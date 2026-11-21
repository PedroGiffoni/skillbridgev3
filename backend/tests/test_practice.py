from concurrent.futures import ThreadPoolExecutor
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from test_api import settings
from test_course_generation import wait_job
from test_history import sign_in
from test_library import LessonProvider, MixedProvider, published_course


def make_lesson(client, outline_id='lesson-1', course=None):
    if course is None:
        course, _ = published_course(client)
    route = f"/api/courses/{course['id']}/lessons/{outline_id}/generate"
    job = client.post(route, json={'course_revision': course['revision'], 'consent': True}).json()
    return course, wait_job(client, job['id'])['lesson']


def test_practice_progress_replay_hint_and_account_isolation(tmp_path):
    config = settings(auth_db_path=tmp_path / 'practice.sqlite3')
    outbox = {}
    app = create_app(config, LessonProvider(), email_sender=outbox.__setitem__)
    with TestClient(app) as owner, TestClient(app) as other, TestClient(app) as guest:
        sign_in(owner, outbox, 'student@example.test')
        sign_in(other, outbox, 'other@example.test')
        course, lesson = make_lesson(owner)
        route = '/api/exercises/' + lesson['id']
        choice, wrong, *_ = lesson['exercise']['options']
        attempt_id = uuid4().hex
        body = {'attempt_id': attempt_id, 'answer': {'kind': 'multiple_choice', 'option_id': choice['id']}}
        assert guest.post(route + '/attempts', json=body).status_code == 401
        assert other.post(route + '/attempts', json=body).status_code == 404
        assert other.post(route + '/hint', json={'attempt_id': attempt_id}).status_code == 404
        hinted = owner.post(route + '/hint', json={'attempt_id': attempt_id})
        assert hinted.status_code == 200 and hinted.json()['text']
        body['hint_receipt'] = hinted.json()['receipt']
        assert owner.post(route + '/attempts', json={**body, 'attempt_id': uuid4().hex}).status_code == 422
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM practice_attempts').fetchone() == (0,)
        assert owner.get('/api/lessons/' + lesson['id']).json()['practice']['attempts'] == 0
        result = owner.post(route + '/attempts', json=body)
        assert result.status_code == 200
        stored = result.json()
        assert stored['attempt']['correct'] and stored['attempt']['hint_used']
        assert stored['practice']['attempts'] == 1 and stored['practice']['completed']
        assert owner.post(route + '/attempts', json=body).json() == stored
        assert owner.post(route + '/attempts', json={**body, 'answer': {
            'kind': 'multiple_choice', 'option_id': wrong['id'],
        }}).status_code == 409
        assert owner.post(route + '/hint', json={'attempt_id': attempt_id}).status_code == 409
        with TestClient(create_app(config, LessonProvider(), email_sender=outbox.__setitem__)) as restarted:
            restarted.cookies.update(owner.cookies)
            assert restarted.get('/api/lessons/' + lesson['id']).json()['practice'] == stored['practice']
            slots = restarted.get('/api/courses/' + course['id'] + '/lessons', params={'course_revision': course['revision']}).json()
            assert slots['items'][0]['practice_completed']
            assert restarted.delete('/api/history/' + course['plan_id']).status_code == 204
    with sqlite3.connect(config.auth_db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM practice_attempts').fetchone() == (0,)

def test_wrong_choice_and_concurrent_submissions_preserve_first_completion(tmp_path):
    config = settings(auth_db_path=tmp_path / 'concurrent.sqlite3')
    outbox = {}
    provider = LessonProvider()
    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        _, lesson = make_lesson(client)
        route = '/api/exercises/' + lesson['id'] + '/attempts'
        choice, wrong, *_ = lesson['exercise']['options']
        body = {'attempt_id': uuid4().hex, 'answer': {'kind': 'multiple_choice', 'option_id': choice['id']}}
        assert client.post(route, json={**body, 'answer': {**body['answer'], 'option_id': 'missing'}}).status_code == 422

        def send(_):
            response = client.post(route, json=body)
            assert response.status_code == 200
            return response.json()

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(send, range(4)))
        assert all(item == results[0] for item in results)
        assert results[0]['practice']['attempts'] == 1

        response = client.post(route, json={
            'attempt_id': uuid4().hex, 'answer': {'kind': 'multiple_choice', 'option_id': wrong['id']},
        }).json()
        assert not response['attempt']['correct'] and not response['attempt']['hint_used']
        assert response['practice'] == {'attempts': 2, 'completed': True, 'latest_attempt': response['attempt']}
        assert client.post(route, json=body).json() == {
            'attempt': results[0]['attempt'], 'practice': response['practice'],
        }
        assert len(provider.lesson_calls) == 1


def test_order_and_blank_use_stored_rubrics_and_validate_answers(tmp_path):
    config = settings(auth_db_path=tmp_path / 'formats.sqlite3')
    outbox = {}
    with TestClient(create_app(config, MixedProvider(), email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        course, _ = published_course(client)
        _, ordering = make_lesson(client, 'lesson-2', course)
        _, blank = make_lesson(client, 'lesson-3', course)
        order_route = '/api/exercises/' + ordering['id'] + '/attempts'
        blank_route = '/api/exercises/' + blank['id'] + '/attempts'
        first, second, third = [step['id'] for step in ordering['exercise']['steps']]

        def submit(route, answer):
            return client.post(route, json={'attempt_id': uuid4().hex, 'answer': answer})

        invalid = submit(order_route, {'kind': 'order_steps', 'step_ids': [first, first, third]})
        assert invalid.status_code == 422
        out_of_order = submit(order_route, {'kind': 'order_steps', 'step_ids': [first, second, third]}).json()
        assert not out_of_order['attempt']['correct']
        assert out_of_order['attempt']['feedback'] == ['1 de 3 passos estão na posição esperada. Revise a sequência.']
        ordered = submit(order_route, {'kind': 'order_steps', 'step_ids': [second, first, third]}).json()
        assert ordered['attempt']['correct'] and ordered['practice']['attempts'] == 2
        assert len(ordered['attempt']['feedback']) == 3

        assert submit(blank_route, {'kind': 'multiple_choice', 'option_id': 'a'}).status_code == 422
        assert submit(blank_route, {'kind': 'fill_blank', 'text': '\u200b'}).status_code == 422
        typed = 'Palavra particular'
        incomplete = submit(blank_route, {'kind': 'fill_blank', 'text': typed}).json()
        assert not incomplete['attempt']['correct'] and not incomplete['practice']['completed']
        normalized = submit(blank_route, {'kind': 'fill_blank', 'text': '  ＲＥＧＩＳＴＲＯ  '}).json()
        assert normalized['attempt']['correct'] and normalized['practice']['attempts'] == 2
    with sqlite3.connect(config.auth_db_path) as db:
        row = db.execute(
            'SELECT response_digest, feedback FROM practice_attempts WHERE attempt_id = ?', (incomplete['attempt']['id'],),
        ).fetchone()
        assert isinstance(row[0], bytes) and len(row[0]) == 32
        assert typed not in row[1] and typed.encode() not in row[0]
