import json
import sqlite3
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from fastapi.testclient import TestClient

from app.history import AssessmentHistory, save_initial_plan
from app.learning import CourseContent, LearningStore
from app.main import create_app
from test_api import Fake, assessment_payload, questionnaire, settings
from test_history import sign_in


def test_catalog_has_version_and_is_the_source_of_questionnaire_labels():
    with TestClient(create_app(settings(), Fake())) as client:
        response = client.get('/api/careers')
        assert response.status_code == 200
        catalog = response.json()
        assert catalog['version'] == 1
        assert len(catalog['groups']) == 12
        careers = [career for group in catalog['groups'] for career in group['careers']]
        assert len(careers) == len({career['id'] for career in careers}) == 72
        assert all(career['aliases'] for career in careers)
        assert client.post('/api/questionnaire', json={'profession': careers[0]['label'], 'consent': True}).status_code == 200


def test_plan_persists_privately_and_history_deletion_cascades(tmp_path):
    config = settings(auth_db_path=tmp_path / 'learning.sqlite3')
    outbox = {}
    app = create_app(config, Fake(), email_sender=outbox.__setitem__)
    with TestClient(app) as owner, TestClient(app) as stranger, TestClient(app) as guest:
        sign_in(owner, outbox, 'owner@example.test')
        sign_in(stranger, outbox, 'stranger@example.test')
        result = owner.post('/api/assessment', json=assessment_payload(questionnaire(owner).json())).json()
        plan_id = result['source_assessment_id']
        route = '/api/study-plans/' + plan_id
        assert guest.get(route).status_code == 401
        assert stranger.get(route).status_code == 404
        assert stranger.delete('/api/history/' + plan_id).status_code == 404
        plan = owner.get(route).json()
        assert plan['id'] == plan_id
        assert plan['revision'] == 1
        assert plan['assessment'] == result
        with TestClient(create_app(config, Fake(), email_sender=outbox.__setitem__)) as restarted:
            restarted.cookies.update(owner.cookies)
            assert restarted.get(route).json() == plan
            assert restarted.delete('/api/history/' + plan_id).status_code == 204
            assert restarted.get(route).status_code == 404
    with sqlite3.connect(config.auth_db_path) as database:
        for table in ('study_plans', 'study_plan_versions', 'study_weeks'):
            assert database.execute('SELECT COUNT(*) FROM ' + table).fetchone() == (0,)


def test_migration_materializes_existing_v3_without_changing_history(tmp_path):
    config = settings(auth_db_path=tmp_path / 'migration.sqlite3')
    outbox = {}
    before = create_app(config, Fake(), email_sender=outbox.__setitem__)
    with TestClient(before) as client:
        sign_in(client, outbox, 'owner@example.test')
        payload = assessment_payload(questionnaire(client).json())
        result = client.post('/api/assessment', json=payload).json()
        identifier = result['source_assessment_id']
        cookies = client.cookies
    with sqlite3.connect(config.auth_db_path) as database:
        original = database.execute('SELECT result FROM assessment_history').fetchone()[0]
        existing_tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        database.execute('DROP TRIGGER IF EXISTS award_practice_xp')
        database.execute('DROP TRIGGER IF EXISTS award_mastery_xp')
        for table in ('content_reports', 'study_time', 'xp_ledger', 'module_mastery', 'module_exams',
                      'theme_audio', 'theme_jobs', 'practice_attempts', 'lesson_versions', 'course_publications', 'generation_jobs', 'course_versions', 'courses', 'study_weeks',
                      'study_plan_versions', 'study_plans', 'learning_migrations'):
            if table in existing_tables:
                database.execute('DROP TABLE ' + table)
    with TestClient(create_app(config, Fake(), email_sender=outbox.__setitem__)) as client:
        client.cookies.update(cookies)
        plan = client.get('/api/study-plans/' + identifier).json()
        assert plan['assessment'] == json.loads(original)
    with sqlite3.connect(config.auth_db_path) as database:
        assert database.execute('SELECT result FROM assessment_history').fetchone() == (original,)
        assert database.execute('SELECT COUNT(*) FROM study_weeks').fetchone() == (12,)


def test_course_revisions_are_private_until_published_and_cascade_with_plan(tmp_path):
    config = settings(auth_db_path=tmp_path / 'course.sqlite3')
    outbox = {}
    app = create_app(config, Fake(), email_sender=outbox.__setitem__)
    store = LearningStore(AssessmentHistory(config.auth_db_path).connection)
    initial = CourseContent(title='Primeiro módulo sintético', blueprint={'modules': [{'title': 'Fundamentos'}]})
    next_draft = CourseContent(title='Revisão sintética', blueprint={'modules': [{'title': 'Aplicação'}]})
    with TestClient(app) as owner, TestClient(app) as stranger, TestClient(app) as guest:
        sign_in(owner, outbox, 'owner@example.test')
        sign_in(stranger, outbox, 'stranger@example.test')
        result = owner.post('/api/assessment', json=assessment_payload(questionnaire(owner).json())).json()
        plan_id = result['source_assessment_id']
        with sqlite3.connect(config.auth_db_path) as db:
            identities = dict(db.execute('SELECT email, id FROM accounts'))
        owner_id = identities['owner@example.test']
        stranger_id = identities['stranger@example.test']
        with pytest.raises(HTTPException) as forbidden:
            store.save_course_version(stranger_id, plan_id, 1, initial)
        assert forbidden.value.status_code == 404

        draft = store.save_course_version(owner_id, plan_id, 1, initial)
        assert draft.revision == 1
        assert store.save_course_version(owner_id, plan_id, 1, initial) == draft
        route = '/api/courses/' + draft.id
        assert guest.get(route).status_code == 401
        assert owner.get(route).status_code == 404
        published = store.save_course_version(owner_id, plan_id, 1, initial, published=True)
        assert published.id == draft.id and published.revision == 2
        next_version = store.save_course_version(owner_id, plan_id, 1, next_draft)
        assert next_version.revision == 3
        assert stranger.get(route).status_code == 404

        with TestClient(create_app(config, Fake(), email_sender=outbox.__setitem__)) as restarted:
            restarted.cookies.update(owner.cookies)
            assert restarted.get(route).json() == published.model_dump()
            assert restarted.delete('/api/history/' + plan_id).status_code == 204
            assert restarted.get(route).status_code == 404
    with sqlite3.connect(config.auth_db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM courses').fetchone() == (0,)
        assert db.execute('SELECT COUNT(*) FROM course_versions').fetchone() == (0,)


def test_plan_insert_failure_rolls_back_completed_diagnosis_and_allows_retry(tmp_path):
    config = settings(auth_db_path=tmp_path / 'atomic.sqlite3')
    outbox = {}

    def fail_after_writing_plan(db, assessment, created_at):
        save_initial_plan(db, assessment, created_at)
        raise sqlite3.OperationalError('simulated plan write failure')

    with TestClient(create_app(config, Fake(), email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'owner@example.test')
        payload = assessment_payload(questionnaire(client).json())
        with patch('app.history.save_initial_plan', side_effect=fail_after_writing_plan):
            result = client.post('/api/assessment', json=payload)
            assert result.status_code == 503
        assert client.get('/api/history').json()['items'] == []
        with sqlite3.connect(config.auth_db_path) as db:
            for table in ('assessment_history', 'study_plans', 'study_plan_versions', 'study_weeks'):
                assert db.execute('SELECT COUNT(*) FROM ' + table).fetchone() == (0,)
        retry = client.post('/api/assessment', json=payload)
        assert retry.status_code == 200
        route = '/api/study-plans/' + retry.json()['source_assessment_id']
        assert client.get(route).json()['revision'] == 1

def test_v3_history_saved_by_previous_writer_is_materialized_on_owner_read(tmp_path):
    config = settings(auth_db_path=tmp_path / 'mixed-writers.sqlite3')
    outbox = {}
    app = create_app(config, Fake(), email_sender=outbox.__setitem__)
    with TestClient(app) as owner, TestClient(app) as stranger:
        sign_in(owner, outbox, 'owner@example.test')
        sign_in(stranger, outbox, 'stranger@example.test')
        result = owner.post('/api/assessment', json=assessment_payload(questionnaire(owner).json())).json()
        late_id = '84eabb33dd9643e0b966f584a71e55cc'
        result['source_assessment_id'] = late_id
        serialized = json.dumps(result)
        with sqlite3.connect(config.auth_db_path) as db:
            db.execute("""
                INSERT INTO assessment_history (id, owner_id, fingerprint, profession, started_at, created_at, result)
                SELECT ?, owner_id, 'previous-writer', profession, started_at, created_at, ?
                FROM assessment_history WHERE id = ?
            """, (late_id, serialized, db.execute('SELECT id FROM study_plans').fetchone()[0]))
        route = '/api/study-plans/' + late_id
        assert stranger.get(route).status_code == 404
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM study_plans').fetchone() == (1,)
        response = owner.get(route)
        assert response.status_code == 200
        assert response.json()['assessment'] == result
        assert owner.get(route).json() == response.json()
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT result FROM assessment_history WHERE id = ?', (late_id,)).fetchone() == (serialized,)
