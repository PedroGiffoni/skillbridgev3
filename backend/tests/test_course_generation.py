import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
from threading import Event
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from google.genai import errors

from fastapi.testclient import TestClient

from app.blueprint import CourseBlueprint, blueprint_response_schema
from app.gemini import Gemini, GenerationFailure
from app.learning import LearningStore
from app.main import create_app
from test_api import Fake, assessment_payload, questionnaire, sdk_context, settings
from test_history import sign_in


def outline(data):
    modules = []
    for index in range(4):
        planned = data['weeks'][index * 3:index * 3 + 3]
        lessons = [
            {'id': f'lesson-{week["week"]}', 'title': f'Prática {week["week"]}',
             'objective': 'Identificar um próximo passo.', 'week': week['week'],
             'competency_ids': week['competency_ids'], 'format': 'multiple_choice'}
            for week in planned
        ]
        modules.append({
            'id': f'module-{index + 1}', 'title': f'Módulo {index + 1}',
            'objective': 'Praticar e revisar.', 'weeks': [week['week'] for week in planned],
            'competency_ids': sorted({cid for lesson in lessons for cid in lesson['competency_ids']}),
            'prerequisite_module_ids': [f'module-{index}'] if index else [],
            'lessons': lessons,
        })
    return {'title': 'Roteiro de prática', 'modules': modules}


class OutlineGemini(Fake):
    def __init__(self):
        super().__init__()
        self.blueprint_inputs = []

    async def generate(self, instruction, data, schema):
        if schema.__name__ != 'CourseBlueprint':
            return await super().generate(instruction, data, schema)
        self.blueprint_inputs.append(data)
        return schema.model_validate(outline(data))


def wait_job(client, job_id, *, states=('ready', 'failed', 'needs_review')):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        response = client.get('/api/courses/jobs/' + job_id)
        assert response.status_code == 200
        job = response.json()
        if job['status'] in states:
            return job
        time.sleep(0.08)
    raise AssertionError('Geração não atingiu o estado esperado.')


def create_plan(client):
    response = client.post('/api/assessment', json=assessment_payload(questionnaire(client).json()))
    assert response.status_code == 200
    return response.json()['source_assessment_id']


@pytest.mark.asyncio
async def test_provider_schema_avoids_nested_limits_but_canonical_validation_still_applies():
    response = SimpleNamespace(text=json.dumps({'title': 'Curso', 'modules': []}))
    generate = AsyncMock(return_value=response)
    gateway = sdk_context(generate)
    projected = blueprint_response_schema()
    with patch('app.gemini.genai.Client', return_value=gateway), pytest.raises(GenerationFailure) as error:
        await Gemini(settings()).generate_with_usage('Teste', {}, CourseBlueprint, provider_schema=projected)
    assert error.value.reason == 'invalid_response'
    transmitted = generate.call_args.kwargs['config'].response_json_schema
    assert transmitted == projected
    assert transmitted['properties']['title']['type'] == 'string'
    assert 'maxItems' not in transmitted['properties']['modules']
    assert 'maxItems' not in transmitted['$defs']['ModuleOutline']['properties']['lessons']
    assert CourseBlueprint.model_json_schema()['$defs']['ModuleOutline']['properties']['lessons']['maxItems'] == 8


def test_blueprint_is_a_private_draft_reused_across_requests_and_restart(tmp_path):
    database = tmp_path / 'blueprint.sqlite3'
    config = settings(auth_db_path=database)
    outbox = {}
    provider = OutlineGemini()
    app = create_app(config, provider, email_sender=outbox.__setitem__)
    with TestClient(app) as client, TestClient(app) as other:
        sign_in(client, outbox, 'student@example.test')
        sign_in(other, outbox, 'other@example.test')
        plan_id = create_plan(client)
        assert other.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True}).status_code == 404
        accepted = client.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True})
        assert accepted.status_code == 202
        job_id = accepted.json()['id']
        assert client.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True}).json()['id'] == job_id
        assert other.get('/api/courses/jobs/' + job_id).status_code == 404
        ready = wait_job(client, job_id)
        assert ready['status'] == 'ready'
        assert ready['draft']['published'] is False
        assert ready['draft']['content']['blueprint']['schema_version'] == 1
        assert client.get('/api/courses/' + ready['draft']['id']).status_code == 404
        assert len(provider.blueprint_inputs) == 1
        model_data, = provider.blueprint_inputs
        assert set(model_data) == {'career', 'competencies', 'weeks'}
        assert len(model_data['weeks']) == 12
        assert plan_id not in str(model_data) and 'student@example.test' not in str(model_data)
        cookies = client.cookies
    after_restart = OutlineGemini()
    with TestClient(create_app(config, after_restart, email_sender=outbox.__setitem__)) as client:
        client.cookies.update(cookies)
        duplicate = client.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True, 'retry_attempt': 1})
        assert duplicate.status_code == 202 and duplicate.json() == ready
        assert not after_restart.blueprint_inputs


class MockSdkGateway(Gemini):
    async def generate(self, instruction, data, schema):
        return await Fake().generate(instruction, data, schema)


@pytest.mark.parametrize('case, reason, expected_state, provider_attempts', [
    ('429', 'quota', 'failed', 1),
    ('503', 'unavailable', 'failed', 2),
    ('timeout', 'timeout', 'failed', 1),
    ('malformed', 'invalid_response', 'needs_review', 1),
    ('duplicate_lesson', 'invalid_response', 'needs_review', 1),
    ('unknown_competency', 'invalid_response', 'needs_review', 1),
    ('future_prerequisite', 'invalid_response', 'needs_review', 1),
    ('missing_week', 'invalid_response', 'needs_review', 1),
    ('missing_competency', 'invalid_response', 'needs_review', 1),
    ('unsafe_text', 'invalid_response', 'needs_review', 1),
])
def test_provider_failures_preserve_plan_and_allow_bounded_explicit_retry(
    tmp_path, case, reason, expected_state, provider_attempts,
):
    config = settings(auth_db_path=tmp_path / 'failed.sqlite3', gemini_timeout_seconds=4)
    outbox = {}
    calls = []

    async def generate(**params):
        data = json.loads(params['contents'].splitlines()[-1])
        calls.append(data)
        result = outline(data)
        if len(calls) <= provider_attempts:
            if case in ('429', '503'):
                category = errors.ClientError if case == '429' else errors.ServerError
                raise category(int(case), {'error': {'message': 'private provider detail'}})
            if case == 'timeout':
                raise TimeoutError('private provider detail')
            if case == 'malformed':
                return SimpleNamespace(text='{"title":')
            if case == 'duplicate_lesson':
                result['modules'][0]['lessons'][1]['id'] = result['modules'][0]['lessons'][0]['id']
            elif case == 'unknown_competency':
                result['modules'][0]['lessons'][0]['competency_ids'] = ['unknown']
            elif case == 'future_prerequisite':
                result['modules'][0]['prerequisite_module_ids'] = ['module-4']
            elif case == 'missing_week':
                result['modules'].pop()
            elif case == 'missing_competency':
                result['modules'][0]['lessons'][0]['competency_ids'].pop()
            elif case == 'unsafe_text':
                result['title'] = '<script>example</script>'
        return SimpleNamespace(text=json.dumps(result), usage_metadata=SimpleNamespace(
            prompt_token_count=400, candidates_token_count=900,
        ))

    sdk = AsyncMock(side_effect=generate)
    app = create_app(config, MockSdkGateway(config), email_sender=outbox.__setitem__)
    with patch('app.gemini.genai.Client', side_effect=lambda **_: sdk_context(sdk)), TestClient(app) as client:
        sign_in(client, outbox, 'student@example.test')
        plan_id = create_plan(client)
        body = {'plan_id': plan_id, 'consent': True}
        job_id = client.post('/api/courses/generate', json=body).json()['id']
        failed = wait_job(client, job_id)
        assert failed['status'] == expected_state
        assert failed['error']['code'] == reason and failed['error']['retryable']
        assert failed['draft'] is None
        assert 'private provider detail' not in str(failed)
        assert sdk.await_count == provider_attempts
        assert client.get('/api/study-plans/' + plan_id).status_code == 200
        assert client.post('/api/courses/generate', json=body).json()['status'] == expected_state
        retry = {**body, 'retry_attempt': 1}
        with sqlite3.connect(config.auth_db_path) as database:
            assert database.execute('SELECT COUNT(*) FROM courses').fetchone() == (0,)
        if case == '429':
            delayed = client.post('/api/courses/generate', json=retry)
            assert int(delayed.headers['Retry-After']) > 0
            assert delayed.json()['status'] == 'failed' and sdk.await_count == 1
            with sqlite3.connect(config.auth_db_path) as database:
                database.execute('UPDATE generation_jobs SET retry_after = 0')
        assert client.post('/api/courses/generate', json=retry).json()['id'] == job_id
        ready = wait_job(client, job_id)
        assert ready['status'] == 'ready' and ready['attempts'] == 2
        assert ready['input_tokens'] == 400 and ready['output_tokens'] == 900
        assert sdk.await_count == provider_attempts + 1


def test_expired_claim_is_recovered_after_restart(tmp_path):
    config = settings(auth_db_path=tmp_path / 'recovery.sqlite3')
    provider = OutlineGemini()
    outbox = {}
    app = create_app(config, provider, email_sender=outbox.__setitem__)
    # Omitting the lifespan models a crash before the next worker cycle.
    client = TestClient(app)
    sign_in(client, outbox, 'student@example.test')
    plan_id = create_plan(client)
    job = client.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True}).json()
    assert job['status'] == 'queued'
    with sqlite3.connect(config.auth_db_path) as database:
        database.execute("""
            UPDATE generation_jobs SET status = 'running', attempts = 1, claim_token = 'old', lease_until = 0
            WHERE id = ?
        """, (job['id'],))
    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as restarted:
        restarted.cookies.update(client.cookies)
        ready = wait_job(restarted, job['id'])
        assert ready['status'] == 'ready' and ready['attempts'] == 2
        assert len(provider.blueprint_inputs) == 1
        assert restarted.delete('/api/history/' + plan_id).status_code == 204
        assert restarted.get('/api/courses/jobs/' + job['id']).status_code == 404
    client.close()


def test_concurrent_submissions_share_a_claim_and_deleted_plan_is_not_restored(tmp_path):
    config = settings(auth_db_path=tmp_path / 'cancelled.sqlite3')
    started, release = Event(), Event()

    class SlowProvider(OutlineGemini):
        async def generate(self, instruction, data, schema):
            if schema.__name__ == 'CourseBlueprint':
                started.set()
                await asyncio.to_thread(release.wait, 7)
            return await super().generate(instruction, data, schema)

    outbox = {}
    provider = SlowProvider()
    app = create_app(config, provider, email_sender=outbox.__setitem__)
    with TestClient(app) as client, TestClient(app) as duplicate, ThreadPoolExecutor(2) as pool:
        sign_in(client, outbox, 'student@example.test')
        duplicate.cookies.update(client.cookies)
        plan_id = create_plan(client)
        body = {'plan_id': plan_id, 'consent': True}
        requests = [pool.submit(c.post, '/api/courses/generate', json=body) for c in (client, duplicate)]
        job_ids = {request.result(5).json()['id'] for request in requests}
        try:
            assert len(job_ids) == 1
            assert started.wait(4)
            job_id, = job_ids
            assert client.get('/api/courses/jobs/' + job_id).json()['status'] == 'running'
            assert client.delete('/api/history/' + plan_id).status_code == 204
            assert client.get('/api/courses/jobs/' + job_id).status_code == 404
        finally:
            release.set()
    with sqlite3.connect(config.auth_db_path) as database:
        for table in ('courses', 'course_versions', 'generation_jobs'):
            assert database.execute('SELECT COUNT(*) FROM ' + table).fetchone() == (0,)
    assert len(provider.blueprint_inputs) == 1


def test_explicit_retry_is_bound_to_failed_attempt_and_limited(tmp_path):
    config = settings(auth_db_path=tmp_path / 'attempts.sqlite3')
    outbox = {}

    class Unavailable(OutlineGemini):
        async def generate(self, instruction, data, schema):
            if schema.__name__ == 'CourseBlueprint':
                self.blueprint_inputs.append(data)
                raise GenerationFailure('unavailable')
            return await super().generate(instruction, data, schema)

    provider = Unavailable()
    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        body = {'plan_id': create_plan(client), 'consent': True}
        job_id = client.post('/api/courses/generate', json=body).json()['id']
        assert wait_job(client, job_id)['attempts'] == 1
        first_retry = {**body, 'retry_attempt': 1}
        assert client.post('/api/courses/generate', json=first_retry).json()['id'] == job_id
        assert wait_job(client, job_id)['attempts'] == 2
        assert client.post('/api/courses/generate', json=first_retry).json()['attempts'] == 2
        second_retry = {**body, 'retry_attempt': 2}
        assert client.post('/api/courses/generate', json=second_retry).json()['id'] == job_id
        exhausted = wait_job(client, job_id)
        assert exhausted['attempts'] == 3 and not exhausted['error']['retryable']
        assert client.post('/api/courses/generate', json={**body, 'retry_attempt': 3}).json() == exhausted
        assert len(provider.blueprint_inputs) == 3


def test_consent_and_local_gemini_configuration_precede_new_queue_entries(tmp_path):
    config = settings(auth_db_path=tmp_path / 'consent.sqlite3')
    outbox = {}
    provider = OutlineGemini()
    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        plan_id = create_plan(client)
        cookies = client.cookies
        for invalid in ({'plan_id': plan_id}, {'plan_id': plan_id, 'consent': False}):
            assert client.post('/api/courses/generate', json=invalid).status_code == 422

    disabled = config.model_copy(update={'gemini_free_tier_confirmed': False})
    with TestClient(create_app(disabled, provider, email_sender=outbox.__setitem__)) as client:
        client.cookies.update(cookies)
        response = client.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True})
        assert response.status_code == 503 and response.json()['code'] == 'gemini_not_configured'
    with sqlite3.connect(config.auth_db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM generation_jobs').fetchone() == (0,)
    assert provider.blueprint_inputs == []


def test_worker_only_claims_jobs_with_matching_model(tmp_path):
    config = settings(auth_db_path=tmp_path / 'models.sqlite3')
    other_config = config.model_copy(update={'gemini_model': 'another-test-model'})
    outbox = {}
    provider = OutlineGemini()
    original = TestClient(create_app(config, provider, email_sender=outbox.__setitem__))
    sign_in(original, outbox, 'student@example.test')
    body = {'plan_id': create_plan(original), 'consent': True}
    old = original.post('/api/courses/generate', json=body).json()
    with TestClient(create_app(other_config, provider, email_sender=outbox.__setitem__)) as current:
        current.cookies.update(original.cookies)
        new = current.post('/api/courses/generate', json=body).json()
        assert new['id'] != old['id']
        assert wait_job(current, new['id'])['status'] == 'ready'
        old_view = current.get('/api/courses/jobs/' + old['id']).json()
        assert old_view['status'] == 'failed' and old_view['error']['code'] == 'configuration'
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT status FROM generation_jobs WHERE id = ?', (old['id'],)).fetchone() == ('queued',)
        assert len(provider.blueprint_inputs) == 1
    original.close()


def test_job_and_draft_rollback_together_after_write_failure(tmp_path):
    config = settings(auth_db_path=tmp_path / 'atomic-course.sqlite3')
    outbox = {}
    provider = OutlineGemini()
    reached_write = Event()
    write_course = LearningStore.write_course_version

    def fail_after_write(*args, **kwargs):
        write_course(*args, **kwargs)
        reached_write.set()
        raise sqlite3.OperationalError('simulated transaction failure')

    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        plan_id = create_plan(client)
        with patch.object(LearningStore, 'write_course_version', staticmethod(fail_after_write)):
            job = client.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True}).json()
            assert reached_write.wait(4)
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM courses').fetchone() == (0,)
            assert db.execute('SELECT status, course_id FROM generation_jobs').fetchone() == ('running', None)
            db.execute('UPDATE generation_jobs SET lease_until = 0')
        ready = wait_job(client, job['id'])
        assert ready['status'] == 'ready' and ready['attempts'] == 2
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM course_versions').fetchone() == (1,)
