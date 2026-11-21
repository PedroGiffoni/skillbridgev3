import asyncio
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from threading import Event

from fastapi.testclient import TestClient

from app.main import create_app
from app.mastery import CompetencyEvidence, passing_score
from test_api import settings
from test_history import sign_in
from test_library import LessonProvider, published_course


class MasteryProvider(LessonProvider):
    def __init__(self):
        super().__init__()
        self.exams = []
        self.repeat = False
        self.started = None
        self.release = None

    async def generate(self, instruction, data, schema):
        if schema.__name__ != 'MasteryExam':
            return await super().generate(instruction, data, schema)

        self.exams.append(data)
        if self.started is not None:
            self.started.set()
            await asyncio.to_thread(self.release.wait, 5)
        competencies = [item['id'] for item in data['competencies']]
        assert len(competencies) > 1
        variant = 1 if self.repeat else len(self.exams)
        questions = [
            {
                'id': f'question-{index}',
                'competency_id': competencies[0] if index < 2 else competencies[1 + index % (len(competencies) - 1)],
                'prompt': f'Cenário {variant}, prática {index + 1}. Qual ação produz evidência para revisão?',
                'options': [
                    {'id': 'a', 'label': 'Registrar o resultado', 'feedback': 'O registro permite a comparação.'},
                    {'id': 'b', 'label': 'Omitir o objetivo', 'feedback': 'O objetivo dá contexto à observação.'},
                    {'id': 'c', 'label': 'Descartar as anotações', 'feedback': 'As anotações sustentam a análise.'},
                ],
                'correct_option_id': 'a',
            }
            for index in range(10)
        ]
        return schema.model_validate({'questions': questions})


def route(course, module):
    return f"/api/courses/{course['id']}/modules/{module}/assessment"


def submission(form, revision, wrong):
    return {
        'course_revision': revision,
        'form_id': form['id'],
        'answers': {
            question['id']: next(option['id'] for option in question['options']
                                 if option['label'] == ('Omitir o objetivo' if index in wrong else 'Registrar o resultado'))
            for index, question in enumerate(form['questions'])
        },
    }


def test_threshold_uses_exact_score_and_all_critical_competencies():
    covered = [CompetencyEvidence(id='first', name='Primeira competência', correct=1, total=3)]
    missing = [CompetencyEvidence(id='first', name='Primeira competência', correct=0, total=3)]
    assert not passing_score(79, 100, covered)
    assert not passing_score(799, 1000, covered)
    assert passing_score(80, 100, covered)
    assert not passing_score(80, 100, missing)


def test_private_module_exams_and_server_side_unlocks(tmp_path):
    config = settings(auth_db_path=tmp_path / 'mastery.sqlite3')
    outbox = {}
    provider = MasteryProvider()
    app = create_app(config, provider, email_sender=outbox.__setitem__)
    with TestClient(app) as owner, TestClient(app) as other:
        sign_in(owner, outbox, 'student@example.test')
        sign_in(other, outbox, 'other@example.test')
        course, _ = published_course(owner)
        revision = {'course_revision': course['revision']}
        prepare = {**revision, 'consent': True}
        first_route = route(course, 'module-1')
        next_route = route(course, 'module-2')
        next_lesson = f"/api/courses/{course['id']}/lessons/lesson-4/generate"

        assert owner.get(next_route, params=revision).status_code == 403
        assert owner.post(next_route, json=prepare).status_code == 403
        assert owner.post(next_lesson, json=prepare).status_code == 403
        assert other.get(first_route, params=revision).status_code == 404
        assert owner.post(first_route, json=revision).status_code == 422
        for consent in (False, 1, 'true'):
            assert owner.post(first_route, json={**prepare, 'consent': consent}).status_code == 422
        empty = owner.get(first_route, params=revision).json()
        assert empty == {'available': True, 'pending': False, 'form': None, 'result': None}

        state = owner.post(first_route, json=prepare).json()
        first = state['form']
        assert len(first['questions']) == 10
        assert state == owner.post(first_route, json=prepare).json()
        assert state == owner.get(first_route, params=revision).json()
        assert len(provider.exams) == 1
        assert not provider.exams[0]['previous_prompts']
        assert set(provider.exams[0]) == {'title', 'objective', 'competencies', 'lessons', 'previous_prompts'}
        assert all(set(question) == {'id', 'prompt', 'options'} for question in first['questions'])
        assert all(len(option['id']) == 32 and set(option) == {'id', 'label'}
                   for question in first['questions'] for option in question['options'])

        first_answers = submission(first, course['revision'], {0, 1})
        assert other.post(first_route + '/submit', json=first_answers).status_code == 404
        invalid = {**first_answers, 'answers': {**first_answers['answers'], first['questions'][0]['id']: 'nonexistent'}}
        assert owner.post(first_route + '/submit', json=invalid).status_code == 422
        result = owner.post(first_route + '/submit', json=first_answers).json()
        assert result['score'] == 80 and not result['passed']
        assert result['competencies'][0]['correct'] == 0 and result['competencies'][0]['total'] == 2
        assert result['reinforcement']
        assert owner.post(first_route + '/submit', json=first_answers).json() == result
        assert owner.post(first_route + '/submit', json=submission(first, course['revision'], set())).status_code == 409
        assert owner.get(next_route, params=revision).status_code == 403
        state = owner.post(first_route, json=prepare).json()
        assert state['form'] is None and state['result'] == result
        assert len(provider.exams) == 1

        provider.repeat = True
        retry = {**prepare, 'previous_form_id': first['id']}
        rejected = owner.post(first_route, json=retry)
        assert rejected.status_code == 502 and rejected.json()['code'] == 'gemini_invalid_response'
        assert owner.get(first_route, params=revision).json() == state
        provider.repeat = False
        second = owner.post(first_route, json=retry).json()['form']
        assert len(provider.exams[2]['previous_prompts']) == 10
        assert first['id'] != second['id']
        assert not {q['prompt'] for q in first['questions']} & {q['prompt'] for q in second['questions']}
        second_answers = submission(second, course['revision'], {8, 9})
        passed = owner.post(first_route + '/submit', json=second_answers).json()
        assert passed['score'] == 80 and passed['passed'] and not passed['reinforcement']
        assert owner.post(first_route + '/submit', json=second_answers).json() == passed
        assert owner.post(first_route, json=retry).json()['form'] is None
        assert owner.get(next_route, params=revision).status_code == 200
        assert owner.post(next_lesson, json=prepare).status_code == 202

        cookies = owner.cookies
    disabled = config.model_copy(update={'gemini_free_tier_confirmed': False})
    with TestClient(create_app(disabled, MasteryProvider(), email_sender=outbox.__setitem__)) as reopened:
        reopened.cookies.update(cookies)
        assert reopened.get(first_route, params=revision).json() == {
            'available': False, 'pending': False, 'form': None, 'result': passed,
        }
        assert reopened.get(next_route, params=revision).status_code == 200
        assert reopened.post(first_route + '/submit', json=second_answers).json() == passed
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT COUNT(*) FROM module_exams').fetchone()[0] == 2
            assert db.execute('SELECT COUNT(*) FROM module_mastery').fetchone()[0] == 1
        assert reopened.delete('/api/history/' + course['plan_id']).status_code == 204
    with sqlite3.connect(config.auth_db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM module_exams').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM module_mastery').fetchone()[0] == 0


def test_concurrent_generation_has_one_claim_and_resumes(tmp_path):
    outbox = {}
    provider = MasteryProvider()
    provider.started, provider.release = Event(), Event()
    config = settings(auth_db_path=tmp_path / 'claims.sqlite3')
    with TestClient(create_app(config, provider, email_sender=outbox.__setitem__)) as owner, ThreadPoolExecutor(1) as pool:
        sign_in(owner, outbox, 'student@example.test')
        course, _ = published_course(owner)
        url = route(course, 'module-1')
        revision = {'course_revision': course['revision']}
        body = {**revision, 'consent': True}
        first = pool.submit(owner.post, url, json=body)
        try:
            assert provider.started.wait(3)
            assert owner.get(url, params=revision).json()['pending']
            concurrent = owner.post(url, json=body).json()
            assert concurrent['pending'] and concurrent['form'] is None
            assert len(provider.exams) == 1
        finally:
            provider.release.set()
        form = first.result(3).json()['form']
        assert form == owner.get(url, params=revision).json()['form']
