from concurrent.futures import ThreadPoolExecutor
import io
import sqlite3
from time import monotonic, sleep
import wave

from fastapi.testclient import TestClient

from app.gemini import GenerationFailure
from app.main import create_app
from test_api import settings
from test_history import sign_in
from test_library import LessonProvider
from test_practice import make_lesson


def theme_pack():
    def questions(prefix, prompts):
        return [{
            'id': f'{prefix}-{index}', 'prompt': prompt, 'correct_option_id': 'a',
            'options': [
                {'id': 'a', 'label': 'Registrar os resultados', 'feedback': 'Os registros dão base à comparação.'},
                {'id': 'b', 'label': 'Ignorar as hipóteses', 'feedback': 'A hipótese define o que será observado.'},
                {'id': 'c', 'label': 'Trocar todos os fatores', 'feedback': 'Mudar vários fatores confunde a análise.'},
            ],
        } for index, prompt in enumerate(prompts)]

    return {
        'slides': [
            {'title': title, 'points': [point], 'narration': 'Leia o exemplo antes de seguir. ' + point,
             'diagram': ['Hipótese', 'Teste', 'Observação']}
            for title, point in [
                ('Defina a hipótese', 'Escolha o que quer testar.'),
                ('Registre a observação', 'Anote o resultado de cada tentativa.'),
                ('Compare os resultados', 'Confira as diferenças entre as tentativas.'),
            ]
        ],
        'chapter': {'title': 'Como comparar tentativas', 'sections': [
            {'title': 'Prepare o teste', 'text': 'Escolha uma hipótese e defina uma medida comum.'},
            {'title': 'Faça a revisão', 'text': 'Compare as anotações e decida seu próximo passo.'},
        ]},
        'podcast': {'title': 'O que mudou neste teste?', 'turns': [
            {'speaker': 'host' if index % 2 == 0 else 'expert', 'text': line}
            for index, line in enumerate([
                'Como sabemos o que mudou?',
                'Compare a mesma medida nas duas tentativas.',
                'E quando faltam registros?',
                'Vale repetir o teste e anotar o resultado.',
                'Devo trocar tudo de uma vez?',
                'Comece com um único fator.',
                'O que acontece depois?',
                'Use a comparação para decidir o próximo passo.',
            ])
        ]},
        'map': {'topic': 'Comparar tentativas', 'branches': [
            {'label': 'Hipótese', 'details': ['Escolha a pergunta que deseja responder.']},
            {'label': 'Observação', 'details': ['Anote o resultado de cada teste.']},
        ]},
        'quiz': questions('q', ['O que ajuda a comparar?', 'O que traz evidência?', 'O que guardar no teste?']),
        'simulation': questions('s', [
            'Dois grupos testaram um fluxo. O que você pediria?',
            'Uma colega repetiu o ensaio. O que ela deveria preservar?',
            'Um lote mudou de desempenho. Qual é o próximo registro?',
            'A equipe quer revisar as tentativas anteriores. O que ajuda?',
        ]),
    }


def make_wav(seconds=0.1, frequency=440):
    from math import sin, tau
    from struct import pack

    target = io.BytesIO()
    with wave.open(target, 'wb') as audio:
        audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(b''.join(
            pack('<h', int(500 * sin(tau * frequency * index / 24000)))
            for index in range(int(seconds * 24000))
        ))
    return target.getvalue()


class ThemeProvider(LessonProvider):
    def __init__(self, invalid=False):
        super().__init__()
        self.themes = []
        self.invalid_theme = invalid

    async def generate(self, instruction, data, schema):
        if schema.__name__ != 'ThemePack':
            return await super().generate(instruction, data, schema)
        self.themes.append(data)
        content = theme_pack()
        if self.invalid_theme:
            content['slides'][0]['narration'] = 'Acesse https://example.test para o restante.'
        return schema.model_validate(content)


class SpeechProvider:
    def __init__(self, fail_on_call=None, seconds=0.1):
        self.calls = []
        self.fail_on_call = fail_on_call
        self.seconds = seconds

    async def synthesize(self, turns):
        self.calls.append(turns)
        if len(self.calls) == self.fail_on_call:
            raise GenerationFailure('unavailable')
        return make_wav(self.seconds, frequency=440 + len(self.calls) * 25)


def wait_for_material(client, route, kind='study', expected='ready'):
    deadline = monotonic() + 8
    while monotonic() < deadline:
        response = client.get(route)
        assert response.status_code == 200
        data = response.json()
        job = data['study'] if kind == 'study' else data['audio'][kind]
        if job['status'] not in {'queued', 'running'}:
            assert job['status'] == expected, job
            return data
        sleep(0.04)
    raise AssertionError(f'O job {kind} não terminou no prazo do teste.')


def test_theme_is_private_reused_and_graded_without_gemini(tmp_path):
    config = settings(auth_db_path=tmp_path / 'theme.sqlite3')
    outbox = {}
    provider = ThemeProvider()
    app = create_app(config, provider, email_sender=outbox.__setitem__)
    with TestClient(app) as owner, TestClient(app) as other, TestClient(app) as guest:
        sign_in(owner, outbox, 'student@example.test')
        sign_in(other, outbox, 'other@example.test')
        _, lesson = make_lesson(owner)
        route = f"/api/lessons/{lesson['id']}/materials"
        assert guest.get(route).status_code == 401
        assert other.get(route).status_code == 404
        assert other.post(route, json={'consent': True}).status_code == 404
        assert other.get(route + '/audio/podcast/0').status_code == 404
        assert owner.post(route, json={'consent': False}).status_code == 422
        assert owner.get(route).json()['study']['status'] == 'idle'

        def prepare(_):
            return owner.post(route, json={'consent': True}).status_code

        with ThreadPoolExecutor(max_workers=3) as threads:
            assert list(threads.map(prepare, range(3))) == [202, 202, 202]
        result = wait_for_material(owner, route)
        assert len(provider.themes) == 1
        assert set(provider.themes[0]) == {'title', 'objective', 'explanation', 'example', 'summary'}
        content = result['content']
        assert set(content) == {'slides', 'chapter', 'podcast', 'map', 'quiz', 'simulation'}
        assert not result['audio_available']
        assert owner.post(route + '/audio/video', json={'consent': True}).status_code == 503
        quiz = content['quiz'][0]
        assert len(quiz['id']) == 32 and set(quiz) == {'id', 'prompt', 'options'}
        assert all(set(option) == {'id', 'label'} for option in quiz['options'])
        assert owner.post(route + '/quiz/grade', json={'answers': {'invalida': quiz['options'][0]['id']}}).status_code == 422

        disabled = config.model_copy(update={'gemini_free_tier_confirmed': False})
        with TestClient(create_app(disabled, ThemeProvider(), email_sender=outbox.__setitem__)) as restarted:
            restarted.cookies.update(owner.cookies)
            assert restarted.get(route).json()['content'] == content
            grade = restarted.post(route + '/quiz/grade', json={'answers': {quiz['id']: quiz['options'][0]['id']}}).json()
            assert grade == {'correct': 1, 'total': 1, 'items': [{
                'question_id': quiz['id'], 'correct': True, 'feedback': 'Os registros dão base à comparação.',
            }]}
            answers = {question['id']: question['options'][1]['id'] for question in content['simulation']}
            partial = dict(list(answers.items())[:1])
            assert restarted.post(route + '/simulation/grade', json={'answers': partial}).status_code == 422
            result = restarted.post(route + '/simulation/grade', json={'answers': answers}).json()
            assert result['correct'] == 0 and result['total'] == len(answers)


def test_audio_resumes_from_saved_segments_and_respects_ranges(tmp_path):
    config = settings(auth_db_path=tmp_path / 'audio.sqlite3', gemini_tts_model='speech-configured-by-test',
                      gemini_tts_free_tier_confirmed=True)
    outbox = {}
    speech = SpeechProvider(fail_on_call=2)
    app = create_app(config, ThemeProvider(), email_sender=outbox.__setitem__, speech_generator=speech)
    with TestClient(app) as client:
        sign_in(client, outbox, 'student@example.test')
        course, lesson = make_lesson(client)
        route = f"/api/lessons/{lesson['id']}/materials"
        video = route + '/audio/video'
        assert client.post(video, json={'consent': True}).status_code == 409
        assert client.post(route, json={'consent': True}).status_code == 202
        wait_for_material(client, route)
        assert client.post(video, json={'consent': False}).status_code == 422
        assert client.post(video, json={'consent': True}).status_code == 202
        failed = wait_for_material(client, route, 'video', 'failed')
        assert failed['audio']['video']['error']['retryable']
        assert client.get(video + '/0').status_code == 404
        with sqlite3.connect(config.auth_db_path) as db:
            assert db.execute('SELECT segment FROM theme_audio').fetchall() == [(0,)]
        assert client.post(video, json={'consent': True, 'retry_attempt': 1}).status_code == 202
        assert wait_for_material(client, route, 'video')['audio']['video']['segments'] == 3
        assert len(speech.calls) == 4
        assert speech.calls[0] != speech.calls[1] == speech.calls[2] != speech.calls[3]

        podcast = route + '/audio/podcast'
        assert client.post(podcast, json={'consent': True}).status_code == 202
        assert wait_for_material(client, route, 'podcast')['audio']['podcast']['segments'] == 1
        assert [speaker for speaker, _ in speech.calls[-1]] == ['host', 'expert'] * 4
        chapter = route + '/audio/audiobook'
        assert client.post(chapter, json={'consent': True}).status_code == 202
        assert wait_for_material(client, route, 'audiobook')['audio']['audiobook']['segments'] == 2
        assert speech.calls[-1][0][1].startswith('Faça a revisão. ')
        assert len(speech.calls) == 7

        audio = client.get(podcast + '/0')
        assert audio.status_code == 200 and audio.headers['content-type'] == 'audio/wav'
        assert audio.headers['cache-control'] == 'no-store'
        assert audio.content[:4] == b'RIFF'
        header = client.get(podcast + '/0', headers={'Range': 'bytes=0-19'})
        assert header.status_code == 206 and header.content == audio.content[:20]
        assert header.headers['content-range'] == f'bytes 0-19/{len(audio.content)}'
        suffix = client.get(podcast + '/0', headers={'Range': 'bytes=-20'})
        assert suffix.status_code == 206 and suffix.content == audio.content[-20:]
        assert client.get(podcast + '/0', headers={'Range': 'bytes=999999999-'}).status_code == 416
        assert client.get(podcast + '/1').status_code == 404

        disabled = config.model_copy(update={'gemini_tts_free_tier_confirmed': False})
        with TestClient(create_app(disabled, ThemeProvider(), email_sender=outbox.__setitem__)) as restarted:
            restarted.cookies.update(client.cookies)
            assert not restarted.get(route).json()['audio_available']
            assert restarted.get(podcast + '/0').content == audio.content
            assert restarted.delete('/api/history/' + course['plan_id']).status_code == 204
            assert restarted.get(podcast + '/0').status_code == 404
    with sqlite3.connect(config.auth_db_path) as db:
        for table in ('theme_jobs', 'theme_audio'):
            assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone() == (0,)


def test_invalid_theme_remains_in_review(tmp_path):
    config = settings(auth_db_path=tmp_path / 'invalid-theme.sqlite3')
    outbox = {}
    with TestClient(create_app(config, ThemeProvider(invalid=True), email_sender=outbox.__setitem__)) as client:
        sign_in(client, outbox, 'student@example.test')
        _, lesson = make_lesson(client)
        route = f"/api/lessons/{lesson['id']}/materials"
        assert client.post(route, json={'consent': True}).status_code == 202
        result = wait_for_material(client, route, expected='needs_review')
        assert result['content'] is None
        assert result['study']['error']['retryable']
