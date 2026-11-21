"""Release-level learning journey using a temporary SQLite database and a synthetic provider."""
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from test_api import settings
from test_history import sign_in
from test_library import published_course
from test_mastery import MasteryProvider, route, submission
from test_practice import make_lesson


def test_dashboard_reconciles_evidence_replan_and_backup(tmp_path):
    config = settings(auth_db_path=tmp_path / 'learning.sqlite3')
    provider = MasteryProvider()
    outbox = {}
    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as owner, \
            TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as other:
        sign_in(owner, outbox, 'learner@example.test')
        sign_in(other, outbox, 'other@example.test')
        dashboard = '/api/me/dashboard'
        blank = owner.get(dashboard).json()
        assert blank['course'] is None and blank['weeks'] == [] and blank['xp'] == 0

        course, _ = published_course(owner)
        assert other.get(dashboard, params={'course_id': course['id']}).status_code == 404
        _, lesson = make_lesson(owner, course=course)
        initial = owner.get(dashboard).json()
        assert len(initial['weeks']) == 12 and initial['xp'] == 0
        assert initial['next_lesson']['outline_id'] == 'lesson-1'
        assert initial['modules'][1]['status'] == 'locked'
        assert all(skill['status'] == 'not_started' for skill in initial['competencies'])

        attempt = '/api/exercises/' + lesson['id'] + '/attempts'
        option = lesson['exercise']['options'][0]['id']
        practice = {'attempt_id': uuid4().hex, 'answer': {'kind': 'multiple_choice', 'option_id': option}}
        assert owner.post(attempt, json=practice).json()['practice']['completed']
        assert owner.post(attempt, json=practice).status_code == 200
        assert owner.post(attempt, json={**practice, 'attempt_id': uuid4().hex}).status_code == 200
        activity = owner.get(dashboard).json()
        assert activity['xp'] == 10
        assert activity['weeks'][0]['complete'] and activity['weeks'][0]['lessons_completed'] == 1
        assert activity['next_lesson']['outline_id'] == 'lesson-2'
        assert any(skill['status'] == 'studying' for skill in activity['competencies'])

        revision = {'course_revision': course['revision']}
        exam = route(course, 'module-1')
        first = owner.post(exam, json={**revision, 'consent': True}).json()['form']
        result = owner.post(exam + '/submit', json=submission(first, course['revision'], {0, 1})).json()
        assert result['score'] == 80 and not result['passed']
        review = owner.get(dashboard).json()
        assert review['xp'] == 10 and review['modules'][1]['status'] == 'locked'
        assert any(skill['status'] == 'review' for skill in review['competencies'])
        assert review['modules'][0]['reinforcement']

        second = owner.post(exam, json={**revision, 'consent': True, 'previous_form_id': first['id']}).json()['form']
        answers = submission(second, course['revision'], set())
        assert owner.post(exam + '/submit', json=answers).json()['passed']
        assert owner.post(exam + '/submit', json=answers).status_code == 200
        after = owner.get(dashboard).json()
        assert after['xp'] == 60 and after['modules'][0]['status'] == 'mastered'
        assert after['modules'][1]['status'] == 'open'
        assert after['weeks'][-1]['mastered_count'] > 0
        assert 'Primeiro módulo dominado' in after['achievements']
        assert any(skill['status'] == 'mastered' for skill in after['competencies'])
        assert sum(skill['total'] for skill in after['competencies']) == 20

        time = {'course_id': course['id'], **revision, 'week': 1, 'minutes': 42}
        assert other.post(dashboard + '/time', json=time).status_code == 404
        assert owner.post(dashboard + '/time', json=time).json()['weeks'][0]['recorded_minutes'] == 42
        assert owner.post(dashboard + '/time', json=time).json()['weeks'][0]['recorded_minutes'] == 42
        assert owner.post(dashboard + '/time', json={**time, 'minutes': -1}).status_code == 422

        plan = '/api/study-plans/' + course['plan_id']
        before = owner.get(plan).json()
        payload = {'expected_revision': before['revision'], 'minutes_per_week': 45}
        assert other.post(plan + '/replan', json=payload).status_code == 404
        response = owner.post(plan + '/replan', json=payload)
        assert response.status_code == 200
        revised = response.json()
        assert revised['assessment']['weeks'][0] == before['assessment']['weeks'][0]
        assert all(week['estimated_minutes'] == 45 for week in revised['assessment']['weeks'][1:])
        assert revised['revision'] == before['revision'] + 1
        assert owner.post(plan + '/replan', json=payload).json() == revised
        assert owner.post(plan + '/replan', json={**payload, 'minutes_per_week': 60}).status_code == 409
        old = owner.get('/api/history/' + course['plan_id']).json()['assessment']
        assert old == before['assessment']
        persisted = owner.get(dashboard).json()
        assert persisted['weeks'][0]['planned_minutes'] == before['assessment']['weeks'][0]['estimated_minutes']
        assert persisted['weeks'][1]['planned_minutes'] == 45
        assert persisted['xp'] == 60 and persisted['plan_revision'] == revised['revision']
        assert other.get(dashboard).json()['xp'] == 0
        cookies = owner.cookies

    backup = tmp_path / 'restored.sqlite3'
    with sqlite3.connect(config.auth_db_path) as original, sqlite3.connect(backup) as restored:
        original.backup(restored)
        assert restored.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert restored.execute('PRAGMA foreign_key_check').fetchall() == []
        assert restored.execute('SELECT SUM(points), COUNT(*) FROM xp_ledger').fetchone() == (60, 2)
    disabled = config.model_copy(update={'auth_db_path': backup, 'gemini_free_tier_confirmed': False})
    with TestClient(create_app(disabled, email_sender=outbox.__setitem__)) as client:
        client.cookies.update(cookies)
        assert client.get(dashboard).json() == persisted
        assert client.get(exam, params=revision).json()['result']['passed']
