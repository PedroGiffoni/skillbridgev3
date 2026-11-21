import asyncio
from collections import deque
from contextlib import asynccontextmanager, suppress
import hashlib
import hmac
import json
import sqlite3
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Receive, Scope, Send

from .auth import install_auth
from .blueprint_jobs import BlueprintJobs
from .catalog import CAREER_CATALOG, CAREER_LABELS
from .config import Settings
from .context import CONTEXT_CATALOG, CONTEXT_OPTIONS, PRACTICE_LABELS
from .gemini import FAILURES, Gemini, GenerationFailure
from .history import AssessmentHistory
from .learning import LearningStore
from .learning_dashboard import LearningDashboard
from .mastery import MasteryStore
from .practice import PracticeStore
from .quality import QualityStore
from .schemas import (
    Assessment, AssessmentRequest, AssessmentResult, AssessmentV3, Gap, Guidance, GuidanceV3,
    Profile, Questionnaire, QuestionnaireContent,
)
from .theme_materials import ThemeMaterials
from .theme_tts import GeminiThemeSpeech
from .tokens import Tokens

LIMITATION = 'Autoavaliação orientativa, não certificação ou teste de aptidão. Não garante contratação.'


AVAILABILITY_MINUTES = {
    'ate-30-min': 30,
    'uma-hora': 60,
    'duas-horas': 120,
    'tres-horas': 180,
    'quatro-ou-mais': 240,
}


class BodyLimit:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > 65536:
                return await JSONResponse({'detail': 'Solicitação muito grande (máximo 64 KiB).'}, status_code=413)(scope, receive, send)
            if not message.get('more_body', False):
                break
        async def replay():
            return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
        await self.app(scope, replay, send)


def calculate(questionnaire: Questionnaire, request: AssessmentRequest) -> list[Gap]:
    answers = {answer.competency_id: answer for answer in request.answers}
    if set(answers) != {c.id for c in questionnaire.competencies}:
        raise HTTPException(422, 'Responda exatamente uma vez a cada competência do questionário.')
    return [Gap(competency_id=c.id, name=c.name, expected_level=c.expected_level,
                self_level=answers[c.id].self_level,
                gap=max(0, c.expected_level - answers[c.id].self_level)) for c in questionnaire.competencies]


def create_app(settings: Settings | None = None, generator=None, *, email_sender=None, google_verifier=None, speech_generator=None) -> FastAPI:
    settings = settings or Settings()
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        workers = (asyncio.create_task(jobs.run()), asyncio.create_task(materials.run()))
        try:
            yield
        finally:
            for worker in workers:
                worker.cancel()
            for worker in workers:
                with suppress(asyncio.CancelledError):
                    await worker

    app = FastAPI(title='SkillBridge API', version='0.3.0', lifespan=lifespan)
    app.add_middleware(BodyLimit)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['Content-Type'])
    secret = settings.auth_otp_secret.get_secret_value()
    questionnaire_key = hmac.digest(secret.encode(), b'skillbridge-questionnaire-v1', 'sha256') if len(secret) >= 32 else None
    tokens = Tokens(questionnaire_key)
    auth = install_auth(app, settings, email_sender=email_sender, google_verifier=google_verifier)
    history = AssessmentHistory(settings.auth_db_path)
    history.install_routes(app, auth.require_account)
    learning = LearningStore(history.connection)
    learning.install_routes(app, auth.require_account)
    LearningDashboard(learning).install_routes(app, auth.require_account)
    QualityStore(history.connection, settings.auth_admin_emails).install_routes(app, auth.require_account)
    practice_key = hmac.digest(secret.encode(), b'skillbridge-practice-v1', 'sha256') if len(secret) >= 32 else None
    PracticeStore(history.connection, practice_key).install_routes(app, auth.require_account)
    gemini = generator or Gemini(settings)
    calls: deque[float] = deque()

    @app.middleware('http')
    async def no_api_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    def limit():
        # Global bound per process: no IP addresses or assessment data stored.
        now = monotonic()
        while calls and now - calls[0] >= 60:
            calls.popleft()
        if len(calls) >= settings.gemini_max_requests_per_minute:
            raise GenerationFailure('quota')
        calls.append(now)

    def require_gemini():
        if not settings.ready:
            raise GenerationFailure('not_configured')
        limit()

    jobs = BlueprintJobs(learning, settings.auth_db_path, settings.gemini_model,
                         settings.gemini_timeout_seconds, settings.ready, gemini, require_gemini)
    jobs.install_routes(app, auth.require_account)
    MasteryStore(history.connection, settings, gemini, limit).install_routes(app, auth.require_account)
    materials = ThemeMaterials(history.connection, settings.auth_db_path, settings, gemini,
                               speech_generator or GeminiThemeSpeech(settings), limit)
    materials.install_routes(app, auth.require_account)

    @app.exception_handler(GenerationFailure)
    async def generation_failed(_request: Request, exc: GenerationFailure):
        # No provider messages, prompts or user answers are exposed in errors.
        statuses = {'timeout': 504, 'quota': 429, 'invalid_response': 502,
                    'not_configured': 503, 'configuration': 503, 'access_denied': 503,
                    'unavailable': 503}
        reason = exc.reason if exc.reason in statuses else 'unavailable'
        return JSONResponse(
            {'detail': FAILURES[reason], 'code': f'gemini_{reason}', 'retryable': exc.retryable},
            status_code=statuses[reason],
            headers={'Retry-After': '60'} if reason == 'quota' else None,
        )

    @app.exception_handler(sqlite3.OperationalError)
    async def storage_unavailable(_request: Request, _exc: sqlite3.OperationalError):
        return JSONResponse({'detail': 'O armazenamento está indisponível. Tente novamente em instantes.',
                             'code': 'storage_unavailable', 'retryable': True}, status_code=503)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _exc: RequestValidationError):
        # Avoid echoing input (examples/profession) or validation internals.
        return JSONResponse({'detail': 'Dados inválidos. Confira profissão (3–100 caracteres), consentimento, limites e respostas (0–4).'}, status_code=422)

    @app.get('/health')
    async def health():
        return {'status': 'ok'}

    @app.get('/api/config')
    async def config():
        return {'gemini_enabled': settings.ready}

    @app.get('/api/careers')
    async def careers():
        return CAREER_CATALOG

    @app.post('/api/questionnaire', response_model=Questionnaire)
    async def questionnaire(request: Profile):
        if request.profession not in CAREER_LABELS:
            raise HTTPException(422, 'Selecione uma profissão do catálogo.')
        require_gemini()
        content = await gemini.generate(
            'Proponha exatamente 8 competências introdutórias distintas e relevantes para a profissão: '
            '5 técnicas ou práticas da área e 3 transversais em situações dessa profissão. '
            'Cada pergunta deve explorar uma tarefa concreta, autonomia, estratégia ou dificuldade, '
            'sem exigir experiência profissional prévia. Evite perguntas genéricas ou repetidas. '
            'Inclua descrições e perguntas de autoavaliação respondíveis por seleção única. '
            'Formule enunciados que possam ser respondidos por uma alternativa, sem solicitar textos ou justificativas. '
            'Para CADA competência, gere options com exatamente 5 alternativas {value,label}, '
            'ordenadas por value 0,1,2,3,4. Cada label deve responder diretamente à situação '
            'daquela pergunta, em primeira pessoa, com ações observáveis e linguagem simples '
            '(12 a 220 caracteres). Não reutilize uma escala genérica como "faço com autonomia". '
            'Progressão: 0 ainda não praticou aquela ação; 1 tenta seguindo exemplo e precisa '
            'de orientação próxima; 2 executa parte da tarefa e busca ajuda pontual; '
            '3 realiza e verifica tarefas habituais por conta própria; '
            '4 analisa casos menos previsíveis e justifica ou ajusta a estratégia. '
            'Adapte todos os níveis à tarefa específica, sem presumir emprego anterior. '
            'Não torne ensinar outras pessoas requisito do nível 4. Não use uma alternativa '
            'correta e quatro erros, nem julgamentos como "sou excelente". Não peça para '
            'escolher a melhor técnica: a pessoa deve reconhecer o que já fez na prática. '
            'Se o enunciado tiver mais de uma ação, as alternativas devem cobri-las de forma '
            'coerente ou você deve focar o enunciado em uma única situação. '
            'Escolha expected_level como referência introdutória compatível com essas alternativas. '
            'Use IDs únicos e níveis estimativos 0–4. A profissão foi selecionada do catálogo. '
            'Retorne as 8 competências e deixe clarification vazio.',
            request.model_dump(exclude={'consent'}), QuestionnaireContent,
        )
        if content.clarification or len(content.competencies) != 8:
            raise GenerationFailure('invalid_response')
        result = Questionnaire(
            **content.model_dump(), profession=request.profession, source_mode='gemini',
            notice='Questionário gerado pelo Gemini. Níveis esperados são estimativas educacionais, não padrões verificados de mercado.',
        )
        try:
            result.token = tokens.sign(result)
        except ValueError:
            raise GenerationFailure('invalid_response') from None
        return result

    @app.post('/api/assessment', response_model=AssessmentResult)
    async def assessment(request: AssessmentRequest, owner_id: str = Depends(auth.require_account)):
        payload = request.model_dump(mode='json')
        payload['answers'].sort(key=lambda answer: answer['competency_id'])
        payload['context'] = {key: value for key, value in payload['context'].items() if value}
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        try:
            questionnaire = tokens.verify(request.token)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        gaps = calculate(questionnaire, request)
        entry_id, saved = await run_in_threadpool(history.reserve, owner_id, fingerprint, questionnaire.profession)
        if saved is not None:
            return saved
        try:
            result = await generate_assessment(questionnaire, request, gaps, entry_id)
            await run_in_threadpool(history.save, owner_id, entry_id, result)
        except (Exception, asyncio.CancelledError):
            with suppress(sqlite3.Error):
                await run_in_threadpool(history.release, owner_id, entry_id)
            raise
        return result

    async def generate_assessment(
        questionnaire: Questionnaire, request: AssessmentRequest, gaps: list[Gap], entry_id: str,
    ) -> AssessmentResult:
        require_gemini()
        v3 = settings.study_plan_v3_enabled
        priority_ids = [gap.competency_id for gap in sorted(gaps, key=lambda gap: -gap.gap) if gap.gap][:3]
        weekly_limit = AVAILABILITY_MINUTES.get(request.context.get('availability', ''))
        schema = GuidanceV3 if v3 else Guidance
        plan_instruction = (
            'Crie exatamente 12 semanas ordenadas (1 a 12), com objetivo mensurável, atividades concisas, '
            'entregável observável, revisão e carga estimada em minutos. Use apenas IDs de competências recebidos. '
            'Cubra as lacunas prioritárias sem presumir domínio. Use prerequisite_weeks vazio quando não houver '
            'dependências e aponte apenas para semanas anteriores. Faça fundamentos nas semanas 1–4, '
            'aprofundamento e revisão nas 5–8, e aplicação, reforço e próximos passos nas 9–12. '
            'Respeite o teto semanal em minutos. Se a meta exceder a disponibilidade, reduza o escopo '
            'e explique a restrição nas limitações. Mantenha o JSON conciso. '
        ) if v3 else 'Crie uma trilha realista de quatro semanas (1 a 4) com objetivos, ações e entregáveis. '
        plan_context = {'priority_competency_ids': priority_ids, 'weekly_minutes_limit': weekly_limit or 240} if v3 else {}
        content = await gemini.generate(
            'Gere um diagnóstico orientativo baseado apenas na autoavaliação e nas lacunas recebidas. '
            'Não recalcule nem altere lacunas. Escreva pontos fortes autodeclarados e prioridades. '
            + plan_instruction +
            'Relacione níveis, situações de prática e alternativas de contexto selecionadas. '
            'Fundamente a orientação nas escolhas informadas sem inventar experiências ou exemplos pessoais. '
            'reconheça contradições ou informações ausentes sem presumir domínio. '
            'O nível escolhido e o texto de option_label representam relatos do usuário, '
            'nunca evidência objetiva de habilidade. '
            'Respostas vazias '
            'significam não informado, nunca falta de capacidade. Contexto não muda as lacunas. '
            'Adapte carga de estudo à disponibilidade informada, métodos às preferências e ações '
            'aos recursos e dificuldades relatados. Priorize até 3 frentes e defina entregáveis '
            'observáveis e como revisar o progresso a cada semana, ligados ao objetivo de estudo. '
            'Quando faltar tempo informado, proponha carga ajustável e explicite a suposição. '
            'Informe limitações da autoavaliação. Não invente experiência ou recursos externos. '
            'O resultado será salvo: não inclua nomes, e-mails, telefones ou endereços do estudante.',
            {**plan_context, 'profession': questionnaire.profession, 'competencies': [c.model_dump() for c in questionnaire.competencies],
             'answers': [{**a.model_dump(), 'example': PRACTICE_LABELS.get(a.example, ''), 'option_label': next(
                 option.label for c in questionnaire.competencies if c.id == a.competency_id
                 for option in c.options if option.value == a.self_level
             )} for a in request.answers], 'gaps': [g.model_dump() for g in gaps],
             'context': [{'id': item['id'], 'question': item['question'],
                          'answer': CONTEXT_OPTIONS[item['id']].get(request.context.get(item['id'], ''), '')}
                         for item in CONTEXT_CATALOG]}, schema,
        )
        notes = [LIMITATION]
        if v3 and weekly_limit is None:
            notes.append('A carga semanal é uma estimativa ajustável. Sua disponibilidade não tem um limite fixo informado.')
        elif v3 and weekly_limit == 30:
            notes.append('Com até 30 minutos por semana, priorize as atividades essenciais e adie as que exigirem mais tempo.')
        result = {
            **content.model_dump(exclude={'limitations'}),
            'limitations': list(dict.fromkeys([*notes, *content.limitations]))[:5],
            'gaps': gaps,
            'source_mode': 'gemini',
            'notice': 'Orientação gerada pelo Gemini com base na autoavaliação. Lacunas calculadas pelo servidor; níveis esperados são estimativas.',
        }
        if not v3:
            return Assessment.model_validate(result)

        try:
            assessment = AssessmentV3.model_validate({
                **result, 'plan_version': 3, 'source_assessment_id': entry_id,
            })
        except ValidationError:
            raise GenerationFailure('invalid_response') from None
        covered = {competency for week in assessment.weeks for competency in week.competency_ids}
        if (not covered.issuperset(priority_ids)
                or weekly_limit is not None and any(week.estimated_minutes > weekly_limit for week in assessment.weeks)):
            raise GenerationFailure('invalid_response')
        return assessment

    return app


app = create_app()
