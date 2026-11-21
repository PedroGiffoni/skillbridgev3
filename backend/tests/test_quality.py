import sqlite3

from fastapi.testclient import TestClient

from app.gemini import GenerationFailure
from app.main import create_app
from test_api import TEST_CAREER, settings
from test_course_generation import wait_job
from test_history import sign_in
from test_library import LessonProvider, published_course


def test_administrative_access_and_private_idempotent_content_report(tmp_path):
    config = settings(auth_db_path=tmp_path / 'quality.sqlite3', auth_admin_emails=[' ADMIN@example.com '])
    outbox = {}
    class QualityProvider(LessonProvider):
        unavailable = False

        async def generate(self, instruction, data, schema):
            if self.unavailable and schema.__name__ == 'ChoiceLesson':
                raise GenerationFailure('unavailable', provider_status=503)
            return await super().generate(instruction, data, schema)

    provider = QualityProvider()
    app = create_app(config, provider, email_sender=outbox.__setitem__)
    with TestClient(app) as admin, TestClient(app) as owner, TestClient(app) as guest:
        assert guest.get('/api/admin/access').status_code == 401
        assert guest.get('/api/admin/quality').status_code == 401
        sign_in(admin, outbox, 'admin@example.com')
        sign_in(owner, outbox, 'reader@example.com')
        assert admin.get('/api/admin/access').json() == {'allowed': True}
        assert owner.get('/api/admin/access').json() == {'allowed': False}
        assert owner.get('/api/admin/quality').status_code == 403

        empty = admin.get('/api/admin/quality').json()
        assert empty['generation']['total'] == 0
        assert empty['generation']['latency_ms'] is None
        assert empty['generation']['cost_usd'] is None

        course, _draft = published_course(owner)
        route = '/api/courses/' + course['id'] + '/lessons'
        body = {'course_revision': course['revision'], 'consent': True}
        ready = owner.post(route + '/lesson-1/generate', json=body).json()
        lesson_id = wait_job(owner, ready['id'])['lesson']['id']
        data = {'lesson_id': lesson_id, 'category': 'answer_key'}

        assert guest.post('/api/content-reports', json=data).status_code == 401
        assert admin.post('/api/content-reports', json=data).status_code == 404
        assert owner.post('/api/content-reports', json={**data, 'category': 'unknown'}).status_code == 422
        assert owner.post('/api/content-reports', json={**data, 'notes': 'Extra text'}).status_code == 422
        assert owner.post('/api/content-reports', json=data).status_code == 204
        assert owner.post('/api/content-reports', json=data).status_code == 204
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM content_reports').fetchone() == (1,)

        provider.invalid = True
        invalid = owner.post(route + '/lesson-2/generate', json=body).json()
        assert wait_job(owner, invalid['id'])['status'] == 'needs_review'
        summary = admin.get('/api/admin/quality', params={'model': config.gemini_model}).json()
        assert summary['generation']['by_status'] == {'queued': 0, 'running': 0, 'ready': 2, 'failed': 0, 'needs_review': 1}
        assert summary['generation']['failures']['invalid_response'] == 1
        assert summary['generation']['rejection_rate'] == 0.3333
        assert summary['reports']['answer_key'] is None
        assert summary['progress']['learners'] is None
        assert 'reader@example.com' not in str(summary) and lesson_id not in str(summary)
        hidden = admin.get('/api/admin/quality', params={'career': TEST_CAREER}).json()
        assert hidden['generation']['restricted'] and hidden['generation']['total'] is None
        filtered = admin.get('/api/admin/quality', params={'prompt_version': 1001}).json()
        assert filtered['generation']['total'] == 2
        assert admin.get('/api/admin/quality', params={'window_days': 91}).status_code == 422

        provider.unavailable = True
        interrupted = owner.post(route + '/lesson-3/generate', json=body).json()
        assert wait_job(owner, interrupted['id'])['status'] == 'failed'
        measured = admin.get('/api/admin/quality').json()['generation']
        assert measured['failures']['provider_503'] == 1
        assert measured['failures']['unavailable'] == 0
        assert measured['latency_ms']['samples'] == 4

        assert owner.delete('/api/history/' + course['plan_id']).status_code == 204
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM content_reports').fetchone() == (0,)


def test_learning_indicators_count_first_completion_and_minimum_five_people():
    from app.quality import _progress, _reports

    cutoff = '2026-11-10T00:00:00+00:00'
    in_window = '2026-11-20T00:00:00+00:00'
    outside = '2026-11-01T00:00:00+00:00'
    with sqlite3.connect(':memory:') as db:
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE assessment_history (id TEXT, profession TEXT, result TEXT);
            CREATE TABLE courses (id TEXT, plan_id TEXT);
            CREATE TABLE lesson_versions (id TEXT, course_id TEXT);
            CREATE TABLE practice_attempts (owner_id TEXT, lesson_id TEXT, correct INTEGER, created_at TEXT);
            CREATE TABLE module_mastery (owner_id TEXT, course_id TEXT, granted_at TEXT);
            CREATE TABLE content_reports (owner_id TEXT, lesson_id TEXT, category TEXT, created_at TEXT);
            INSERT INTO assessment_history VALUES ('plan', 'Carreira', '{}');
            INSERT INTO courses VALUES ('course', 'plan');
            INSERT INTO lesson_versions VALUES ('lesson', 'course'), ('older', 'course');
        """)
        db.executemany('INSERT INTO practice_attempts VALUES (?, ?, ?, ?)', [
            ('person-0', 'older', 1, outside), ('person-0', 'older', 1, in_window),
            ('person-0', 'lesson', 1, in_window), ('person-0', 'lesson', 1, in_window),
        ])
        for index in range(1, 5):
            db.execute('INSERT INTO practice_attempts VALUES (?, ?, 1, ?)', (f'person-{index}', 'lesson', in_window))
        for index in range(5):
            db.execute('INSERT INTO content_reports VALUES (?, ?, ?, ?)',
                       (f'person-{index}', 'lesson', 'accuracy', in_window))
        db.execute('INSERT INTO content_reports VALUES (?, ?, ?, ?)', ('person-0', 'older', 'accuracy', in_window))
        db.execute('INSERT INTO module_mastery VALUES (?, ?, ?)', ('person-0', 'course', in_window))

        assert _progress(db, cutoff, None) == {'learners': 5, 'lessons_completed': 5, 'modules_mastered': None}
        assert _reports(db, cutoff, None)['accuracy'] == 6
        assert _reports(db, cutoff, None)['clarity'] is None
        assert _reports(db, cutoff, 'Outra carreira')['accuracy'] is None
