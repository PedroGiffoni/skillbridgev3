import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from test_api import settings
from test_course_generation import OutlineGemini, create_plan, outline, wait_job
from test_history import sign_in


class LessonProvider(OutlineGemini):
    def __init__(self, invalid=False):
        super().__init__()
        self.lesson_calls = []
        self.invalid = invalid

    async def generate(self, instruction, data, schema):
        if schema.__name__ != 'ChoiceLesson':
            return await super().generate(instruction, data, schema)
        self.lesson_calls.append(data)
        return schema.model_validate({
            'explanation': 'Use um exemplo pequeno para testar a sua hipótese.',
            'example': 'Registre o que mudou entre dois testes.',
            'summary': 'Compare os registros para decidir seu próximo passo.',
            'exercise': {
                'prompt': 'O que permite comparar duas tentativas?',
                'options': [
                    {'id': 'a', 'label': 'Registrar o resultado', 'feedback': 'O registro torna a comparação possível.'},
                    {'id': 'b', 'label': 'Omitir a hipótese', 'feedback': 'A hipótese ajuda a interpretar o resultado.'},
                    {'id': 'c', 'label': 'Descartar a observação', 'feedback': 'A observação é parte da análise.'},
                ],
                'correct_option_id': 'missing' if self.invalid else 'a',
            },
        })


class MixedProvider(LessonProvider):
    async def generate(self, instruction, data, schema):
        if schema.__name__ == 'CourseBlueprint':
            source = outline(data)
            source['modules'][0]['lessons'][1]['format'] = 'order_steps'
            source['modules'][0]['lessons'][2]['format'] = 'fill_blank'
            return schema.model_validate(source)
        fields = {'explanation': 'Observe o que aconteceu.', 'example': 'Anote um resultado.',
                  'summary': 'Use anotações para revisar.'}
        if schema.__name__ == 'OrderLesson':
            return schema.model_validate({**fields, 'exercise': {
                'prompt': 'Ordene a investigação.',
                'steps': [
                    {'id': 'b', 'label': 'Experimentar', 'feedback': 'Teste em pequena escala.'},
                    {'id': 'a', 'label': 'Definir hipótese', 'feedback': 'Estabeleça primeiro o que quer testar.'},
                    {'id': 'c', 'label': 'Rever', 'feedback': 'Compare os resultados ao final.'},
                ],
                'correct_order': ['a', 'b', 'c'],
            }})
        if schema.__name__ == 'BlankLesson':
            return schema.model_validate({**fields, 'exercise': {
                'prompt': 'Ao comparar, olhe o seu [lacuna].', 'answer': 'registro',
                'correct_feedback': 'O registro sustenta a comparação.',
                'incorrect_feedback': 'Lembre-se do que anotou durante a experiência.',
            }})
        return await super().generate(instruction, data, schema)

def published_course(client):
    plan_id = create_plan(client)
    job = client.post('/api/courses/generate', json={'plan_id': plan_id, 'consent': True}).json()
    draft = wait_job(client, job['id'])['draft']
    response = client.post('/api/courses/' + draft['id'] + '/publish', json={'draft_revision': draft['revision']})
    assert response.status_code == 200
    return response.json(), draft


def test_publication_and_reopening_are_private_and_reuse_saved_content(tmp_path):
    config = settings(auth_db_path=tmp_path / 'library.sqlite3')
    provider = LessonProvider()
    outbox = {}
    app = create_app(config, provider, email_sender=outbox.__setitem__)
    with TestClient(app) as owner, TestClient(app) as other:
        sign_in(owner, outbox, 'reader@example.test')
        sign_in(other, outbox, 'other@example.test')
        course, draft = published_course(owner)
        assert course['published'] is True and course['revision'] != draft['revision']
        assert owner.post('/api/courses/' + course['id'] + '/publish',
                          json={'draft_revision': draft['revision']}).json() == course
        assert owner.get('/api/courses').json()['items'][0]['id'] == course['id']
        assert other.get('/api/courses').json()['items'] == []
        base = '/api/courses/' + course['id'] + '/lessons'
        route = base + '/lesson-1/generate'
        body = {'course_revision': course['revision'], 'consent': True}
        assert other.post(route, json=body).status_code == 404
        assert owner.post(route, json={**body, 'consent': False}).status_code == 422
        response = owner.post(route, json=body)
        assert response.status_code == 202
        assert response.json()['prompt_version'] == 1001
        assert owner.post(route, json={**body, 'course_revision': 2 ** 63}).status_code == 422
        assert owner.get(base, params={'course_revision': 2 ** 63}).status_code == 422
        assert owner.post('/api/courses/' + course['id'] + '/publish', json={'draft_revision': 2 ** 63}).status_code == 422
        job = wait_job(owner, response.json()['id'])
        assert job['status'] == 'ready'
        lesson = job['lesson']
        assert lesson['outline_id'] == 'lesson-1'
        assert 'correct_option_id' not in str(lesson) and 'feedback' not in str(lesson)
        assert all(len(option['id']) == 32 for option in lesson['exercise']['options'])
        assert other.get('/api/lessons/' + lesson['id']).status_code == 404
        assert owner.get('/api/lessons/' + lesson['id']).json() == lesson
        assert owner.post(route, json=body).json()['lesson'] == lesson
        assert len(provider.lesson_calls) == 1
        cookies = owner.cookies
    restarted = LessonProvider()
    disabled = config.model_copy(update={'gemini_free_tier_confirmed': False, 'gemini_model': 'another-test-model'})
    with TestClient(create_app(disabled, restarted, email_sender=outbox.__setitem__)) as client:
        client.cookies.update(cookies)
        assert client.get('/api/lessons/' + lesson['id']).json() == lesson
        assert client.get(base, params={'course_revision': course['revision']}).json()['items'][0]['lesson_id'] == lesson['id']
        assert client.post(route, json=body).json()['lesson'] == lesson
        assert restarted.lesson_calls == []


def test_invalid_answer_does_not_publish_a_lesson(tmp_path):
    config = settings(auth_db_path=tmp_path / 'invalid.sqlite3')
    outbox = {}
    with TestClient(create_app(config, LessonProvider(invalid=True), email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'reader@example.test')
        course, _ = published_course(client)
        base = '/api/courses/' + course['id'] + '/lessons'
        job = client.post(base + '/lesson-1/generate', json={'course_revision': course['revision'], 'consent': True}).json()
        detail = wait_job(client, job['id'])
        assert detail['status'] == 'needs_review' and detail['lesson'] is None
        assert client.get(base, params={'course_revision': course['revision']}).json()['items'][0]['lesson_id'] is None


def test_all_lesson_formats_use_the_outline_and_keep_the_answer_on_server(tmp_path):
    config = settings(auth_db_path=tmp_path / 'formats.sqlite3')
    outbox = {}

    provider = MixedProvider()
    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'reader@example.test')
        course, _ = published_course(client)
        base = '/api/courses/' + course['id'] + '/lessons'
        for slot, format_, public_fields in (
            ('lesson-1', 'multiple_choice', {'prompt', 'options'}),
            ('lesson-2', 'order_steps', {'prompt', 'steps'}),
            ('lesson-3', 'fill_blank', {'prompt'}),
        ):
            job = client.post(f'{base}/{slot}/generate', json={'course_revision': course['revision'], 'consent': True}).json()
            lesson = wait_job(client, job['id'])['lesson']
            assert lesson['format'] == format_ and set(lesson['exercise']) == public_fields
            assert all(set(item) == {'id', 'label'} for item in lesson['exercise'].get('options', lesson['exercise'].get('steps', [])))
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM lesson_versions').fetchone() == (3,)
            with pytest.raises(sqlite3.IntegrityError):
                db.execute("UPDATE lesson_versions SET content = '{}'")
            with pytest.raises(sqlite3.IntegrityError):
                db.execute("UPDATE course_versions SET content = '{}' WHERE published = 1")
        assert client.delete('/api/history/' + course['plan_id']).status_code == 204
        assert client.get('/api/courses').json()['items'] == []
        with sqlite3.connect(config.auth_db_path) as db:
            for table in ('lesson_versions', 'course_publications', 'generation_jobs'):
                assert db.execute('SELECT COUNT(*) FROM ' + table).fetchone() == (0,)
