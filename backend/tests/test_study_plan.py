import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from app.demo import competencies
from app.main import create_app
from app.schemas import QuestionnaireContent
from test_api import Fake, assessment_payload, questionnaire, sdk_context, settings, study_guidance
from test_history import sign_in


def sdk_response(data):
    return SimpleNamespace(text=json.dumps(data, ensure_ascii=False))


def test_new_plan_uses_structured_week_schema_and_omits_account_data(tmp_path):
    ids = [item.id for item in competencies()]
    priorities = [ids[4], ids[1], ids[2]]
    guide = study_guidance(priorities)
    mocked = AsyncMock(side_effect=[
        sdk_response({'competencies': [row.model_dump() for row in competencies()]}),
        sdk_response(guide),
    ])
    config = settings(auth_db_path=tmp_path / 'private.sqlite3')
    outbox = {}
    with patch('app.gemini.genai.Client', return_value=sdk_context(mocked)), TestClient(
        create_app(config, email_sender=outbox.__setitem__)
    ) as client:
        sign_in(client, outbox, 'student@example.test')
        q = questionnaire(client).json()
        payload = assessment_payload(q, context={'availability': 'ate-30-min'})
        payload['answers'][4]['self_level'] = 0
        payload['answers'][0]['self_level'] = 4
        response = client.post('/api/assessment', json=payload)
        assert response.status_code == 200
        result = response.json()
        assert result['weeks'] == guide['weeks']
        assert any('30 minutos' in limitation for limitation in result['limitations'])
        sent = mocked.await_args.kwargs
        model_input = json.loads(sent['contents'].splitlines()[-1])
        assert model_input['priority_competency_ids'] == priorities
        assert model_input['weekly_minutes_limit'] == 30
        assert all(value not in sent['contents']
                   for value in ('student@example.test', result['source_assessment_id'], q['token']))
        schema = sent['config'].response_json_schema['properties']
        assert {'plan_version', 'source_assessment_id'}.isdisjoint(schema)


@pytest.mark.parametrize('case', [
    '11-weeks', '13-weeks', 'duplicate', 'order', 'unknown', 'priority', 'future',
    'duration', 'missing-review', 'oversized', 'truncated', 'quota', 'unavailable', 'timeout',
])
def test_invalid_or_unavailable_plan_can_be_retried_without_saving(tmp_path, case):
    ids = [item.id for item in competencies()[:3]]
    invalid = study_guidance(ids)
    week = invalid['weeks'][0]
    if case == '11-weeks':
        invalid['weeks'].pop()
    elif case == '13-weeks':
        invalid['weeks'].append({**week, 'week': 13})
    elif case == 'duplicate':
        week['week'] = 2
    elif case == 'order':
        invalid['weeks'][:2] = reversed(invalid['weeks'][:2])
    elif case == 'unknown':
        week['competency_ids'].append('unrecognized')
    elif case == 'priority':
        invalid = study_guidance(ids[:2])
    elif case == 'future':
        week['prerequisite_weeks'] = [2]
    elif case == 'duration':
        week['estimated_minutes'] = 31
    elif case == 'missing-review':
        del week['review']

    status, reason = 502, 'invalid_response'
    failures = [sdk_response(invalid)]
    provider_message = {'error': {'message': 'private provider data'}}
    if case == 'quota':
        status, reason, failures = 429, 'quota', [errors.ClientError(429, provider_message)]
    elif case == 'unavailable':
        status, reason, failures = 503, 'unavailable', [errors.ServerError(503, provider_message)] * 2
    elif case == 'timeout':
        status, reason, failures = 504, 'timeout', [TimeoutError('private provider data')]
    elif case == 'oversized':
        failures = [SimpleNamespace(text=' ' * 24001)]
    elif case == 'truncated':
        failures = [SimpleNamespace(text=json.dumps(invalid)[:-10])]

    q = QuestionnaireContent(competencies=competencies())
    mocked = AsyncMock(side_effect=[sdk_response(q.model_dump()), *failures, sdk_response(study_guidance(ids))])
    outbox = {}
    with patch('app.gemini.genai.Client', return_value=sdk_context(mocked)), patch(
        'app.gemini.asyncio.sleep', new_callable=AsyncMock
    ), TestClient(create_app(settings(auth_db_path=tmp_path / 'failure.sqlite3'), email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        submission = assessment_payload(questionnaire(client).json(), context={'availability': 'ate-30-min'})
        response = client.post('/api/assessment', json=submission)
        assert response.status_code == status
        assert response.json()['code'] == f'gemini_{reason}'
        assert 'private provider data' not in response.text
        assert client.get('/api/history').json()['items'] == []
        retried = client.post('/api/assessment', json=submission)
        assert retried.status_code == 200
        assert len(retried.json()['weeks']) == 12
        assert len(client.get('/api/history').json()['items']) == 1


def test_legacy_and_v3_records_survive_restart_and_rollback(tmp_path):
    raw_legacy = (Path(__file__).with_name('fixtures') / 'assessment-v2.json').read_bytes()
    config = settings(auth_db_path=tmp_path / 'mixed.sqlite3')
    legacy_config = config.model_copy(update={'study_plan_v3_enabled': False})
    outbox = {}
    with TestClient(create_app(legacy_config, Fake(), email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        original = assessment_payload(questionnaire(client).json())
        legacy = client.post('/api/assessment', json=original).json()
        assert 'plan_version' not in legacy and len(legacy['weeks']) == 4
        legacy_item, = client.get('/api/history').json()['items']
        cookies = client.cookies
    assert legacy == json.loads(raw_legacy)
    with sqlite3.connect(config.auth_db_path) as database:
        database.execute('UPDATE assessment_history SET result = ? WHERE id = ?',
                         (raw_legacy.decode('utf-8'), legacy_item['id']))
        old_row = database.execute('SELECT owner_id, created_at, result FROM assessment_history').fetchone()

    fake = Fake()
    with TestClient(create_app(config, fake, email_sender=outbox.__setitem__)) as client:
        client.cookies.update(cookies)
        assert client.post('/api/assessment', json=original).json() == legacy
        assert fake.inputs == []
        new = client.post('/api/assessment', json={**original, 'context': {'goal': 'atividade-pratica'}})
        assert new.status_code == 200
        result = new.json()
        assert result['plan_version'] == 3

    fake = Fake()
    rolled_back = create_app(legacy_config, fake, email_sender=outbox.__setitem__)
    with TestClient(rolled_back) as client, TestClient(rolled_back) as outsider:
        client.cookies.update(cookies)
        legacy_path = '/api/history/' + legacy_item['id']
        new_path = '/api/history/' + result['source_assessment_id']
        assert client.get(legacy_path).json() == {**legacy_item, 'assessment': legacy}
        assert client.get(new_path).json()['assessment'] == result
        assert client.post('/api/assessment', json=original).json() == legacy
        assert fake.inputs == []
        sign_in(outsider, outbox, 'other@example.test')
        for path in (legacy_path, new_path):
            assert outsider.get(path).status_code == 404
            assert outsider.delete(path).status_code == 404
        assert client.delete(new_path).status_code == 204
        assert client.get(new_path).status_code == 404
    with sqlite3.connect(config.auth_db_path) as database:
        assert database.execute('SELECT owner_id, created_at, result FROM assessment_history').fetchone() == old_row
