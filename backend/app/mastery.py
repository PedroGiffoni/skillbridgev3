"""Private versioned module exams, deterministic grading, and mastery evidence."""

import asyncio
from collections import Counter
from contextlib import suppress
from datetime import datetime, timezone
import hmac
import json
import re
import sqlite3
from time import time
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool

from .blueprint import Identifier, ModuleOutline, UNSAFE_TEXT
from .config import Settings
from .gemini import GenerationFailure
from .lesson_content import ChoiceExercise, LESSON_SCHEMAS
from .library import MAX_REVISION, CourseLibrary, outline_of
from .module_access import assert_module_open
from .practice import ChoiceAnswer, grade
from .schemas import Model, normalize


QUESTION_COUNT = 10
PASS_PERCENT = 80
Revision = Annotated[int, Field(strict=True, ge=1, le=MAX_REVISION)]
FormId = Annotated[str, Field(pattern='^[0-9a-f]{32}$')]
EXAM_PROMPT = (
    'Crie uma avaliação objetiva inteiramente em português do Brasil com exatamente dez questões de aplicação '
    'sobre o módulo recebido. Use exclusivamente o conteúdo pedagógico recebido. Cada pergunta avalia uma '
    'das competências indicadas e cada competência precisa ser avaliada pelo menos uma vez. '
    'Varie os cenários e não repita nem apenas parafraseie enunciados anteriores. '
    'Inclua três ou quatro alternativas curtas e uma única resposta defensável; cada alternativa tem feedback '
    'pedagógico curto e distinto. Use texto simples, sem dicas, URLs, HTML, dados pessoais ou termos de certificação. '
    'Retorne JSON no schema com ID local distinto por questão.'
)
_PRIVATE_TEXT = re.compile(
    r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|(?:\+55\s*)?\(?[1-9]\d\)?\s*9?\d{4}[- ]\d{4})\b'
    r'|\[[^\]\n]+\]\([^\)\n]+\)|\b(?:ftp|file)://',
    re.I,
)
_SCOPE = 'course_id = ? AND course_revision = ? AND module_id = ? AND owner_id = ?'


class MasteryQuestion(ChoiceExercise):
    id: Identifier
    competency_id: Identifier


class MasteryExam(Model):
    questions: list[MasteryQuestion] = Field(min_length=QUESTION_COUNT, max_length=QUESTION_COUNT)


class PrepareExam(Model):
    course_revision: Revision
    consent: bool = Field(strict=True)
    previous_form_id: FormId | None = None

    @field_validator('consent')
    @classmethod
    def requires_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError('O consentimento é necessário para preparar uma avaliação.')
        return value


class SubmitExam(Model):
    course_revision: Revision
    form_id: FormId
    answers: dict[Identifier, Identifier] = Field(min_length=QUESTION_COUNT, max_length=QUESTION_COUNT)


class ExamOption(BaseModel):
    id: str
    label: str


class ExamQuestion(BaseModel):
    id: str
    prompt: str
    options: list[ExamOption]


class ExamForm(BaseModel):
    id: str
    questions: list[ExamQuestion]


class CompetencyEvidence(BaseModel):
    id: str
    name: str
    correct: int
    total: int


class Reinforcement(BaseModel):
    outline_id: str
    title: str


class ExamResult(BaseModel):
    form_id: str
    submitted_at: str
    score: int
    correct: int
    total: int
    passed: bool
    competencies: list[CompetencyEvidence]
    reinforcement: list[Reinforcement]


class ExamState(BaseModel):
    available: bool
    pending: bool = False
    form: ExamForm | None = None
    result: ExamResult | None = None


def migrate_mastery(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 6').fetchone():
        return
    db.execute("""
        CREATE TABLE module_exams (
            id TEXT PRIMARY KEY,
            course_id TEXT NOT NULL,
            course_revision INTEGER NOT NULL,
            module_id TEXT NOT NULL,
            owner_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
            created_at TEXT NOT NULL,
            content TEXT,
            lease_until REAL,
            claim_token TEXT,
            submitted_at TEXT,
            answer_digest BLOB,
            result TEXT,
            UNIQUE (course_id, course_revision, module_id, owner_id, ordinal),
            UNIQUE (course_id, course_revision, module_id, owner_id, id),
            FOREIGN KEY (course_id, course_revision) REFERENCES course_versions(course_id, revision) ON DELETE CASCADE,
            CHECK ((content IS NULL AND lease_until IS NOT NULL AND claim_token IS NOT NULL)
                OR (content IS NOT NULL AND lease_until IS NULL AND claim_token IS NULL)),
            CHECK ((submitted_at IS NULL AND answer_digest IS NULL AND result IS NULL)
                OR (submitted_at IS NOT NULL AND answer_digest IS NOT NULL AND result IS NOT NULL AND content IS NOT NULL))
        )
    """)
    db.execute("""
        CREATE TABLE module_mastery (
            course_id TEXT NOT NULL,
            course_revision INTEGER NOT NULL,
            module_id TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            exam_id TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            PRIMARY KEY (course_id, course_revision, module_id, owner_id),
            FOREIGN KEY (course_id, course_revision, module_id, owner_id, exam_id)
                REFERENCES module_exams(course_id, course_revision, module_id, owner_id, id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TRIGGER freeze_module_exam BEFORE UPDATE ON module_exams
        WHEN OLD.submitted_at IS NOT NULL
        BEGIN SELECT RAISE(ABORT, 'A submitted exam is immutable'); END
    """)
    db.execute('INSERT INTO learning_migrations (version) VALUES (6)')


def passing_score(correct: int, total: int, competencies: list[CompetencyEvidence]) -> bool:
    return total > 0 and correct * 100 >= PASS_PERCENT * total and all(item.correct > 0 for item in competencies)


def _question_key(value: str) -> str:
    return re.sub(r'[\W_]+', ' ', normalize(value).casefold()).strip()


def _checked_exam(raw: MasteryExam, competencies: list[str], previous: list[str]) -> MasteryExam:
    exam = MasteryExam.model_validate(raw.model_dump() if isinstance(raw, MasteryExam) else raw)
    questions = exam.questions
    keys = [_question_key(question.prompt) for question in questions]
    previous_keys = {_question_key(prompt) for prompt in previous}
    if (set(competencies) != {item.competency_id for item in questions}
            or len({item.id for item in questions}) != len(questions)
            or '' in keys or len(set(keys)) != len(keys) or previous_keys.intersection(keys)):
        raise ValueError('Cobertura, identificadores ou variação dos enunciados inválidos.')

    output = []
    for question in questions:
        texts = [question.prompt, *(value for option in question.options for value in (option.label, option.feedback))]
        normalized = [normalize(value) for value in texts]
        if any(not value or UNSAFE_TEXT.search(value) or _PRIVATE_TEXT.search(value) for value in normalized):
            raise ValueError('O texto da avaliação contém dados ou formato inválidos.')
        aliases = {option.id: uuid4().hex for option in question.options}
        randomized = sorted((option.model_copy(update={'id': aliases[option.id]}) for option in question.options),
                            key=lambda option: option.id)
        output.append(question.model_copy(update={
            'id': uuid4().hex, 'options': randomized, 'correct_option_id': aliases[question.correct_option_id],
        }))
    return MasteryExam(questions=output)


def _read_exam(raw: str) -> MasteryExam:
    try:
        return MasteryExam.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(500, 'Não foi possível ler a avaliação salva.') from None


def _read_result(raw: str) -> ExamResult:
    try:
        return ExamResult.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(500, 'Não foi possível ler o resultado salvo.') from None


class MasteryStore:
    def __init__(self, connection, settings: Settings, gateway, reserve_request):
        self.connection = connection
        self.settings = settings
        self.gateway = gateway
        self.reserve_request = reserve_request
        secret = settings.auth_otp_secret.get_secret_value()
        self.digest_key = hmac.digest(secret.encode(), b'skillbridge-mastery-v1', 'sha256') if len(secret) >= 32 else None

    @property
    def available(self) -> bool:
        return self.settings.ready and self.digest_key is not None

    @staticmethod
    def _module(db: sqlite3.Connection, scope: tuple[str, int, str, str]):
        course_id, revision, module_id, owner = scope
        course = CourseLibrary._version(db, owner, course_id, revision, published=True)
        module = next((item for item in outline_of(course).modules if item.id == module_id), None)
        if module is None:
            raise HTTPException(404, 'Módulo não encontrado.')
        assert_module_open(db, owner, course_id, revision, module)
        return course, module

    @staticmethod
    def _competency_names(db: sqlite3.Connection, course) -> dict[str, str]:
        rows = db.execute("""
            SELECT json_extract(gap.value, '$.competency_id') AS id, json_extract(gap.value, '$.name') AS name
            FROM study_plan_versions plan, json_each(plan.assessment, '$.gaps') gap
            WHERE plan.plan_id = ? AND plan.revision = ?
        """, (course.plan_id, course.plan_revision))
        return {row['id']: row['name'] for row in rows if isinstance(row['name'], str)}

    @staticmethod
    def _latest(db: sqlite3.Connection, scope: tuple[str, int, str, str]):
        return db.execute(f'SELECT * FROM module_exams WHERE {_SCOPE} ORDER BY ordinal DESC LIMIT 1', scope).fetchone()

    @staticmethod
    def _last_submitted(db: sqlite3.Connection, scope: tuple[str, int, str, str]):
        return db.execute(f"""
            SELECT id, result FROM module_exams WHERE {_SCOPE} AND submitted_at IS NOT NULL
            ORDER BY ordinal DESC LIMIT 1
        """, scope).fetchone()

    def _state(self, db: sqlite3.Connection, scope: tuple[str, int, str, str], latest) -> ExamState:
        previous = self._last_submitted(db, scope)
        result = _read_result(previous['result']) if previous else None
        if latest is None or latest['submitted_at'] is not None:
            return ExamState(available=self.available, result=result)
        if latest['content'] is None:
            return ExamState(available=self.available, pending=latest['lease_until'] > time(), result=result)
        exam = _read_exam(latest['content'])
        form = ExamForm(id=latest['id'], questions=[
            ExamQuestion(id=question.id, prompt=question.prompt,
                         options=[ExamOption(id=option.id, label=option.label) for option in question.options])
            for question in exam.questions
        ])
        return ExamState(available=self.available, form=form, result=result)

    def get(self, owner: str, course_id: str, module_id: str, revision: int) -> ExamState:
        scope = (course_id, revision, module_id, owner)
        with self.connection() as db:
            db.execute('BEGIN')
            self._module(db, scope)
            return self._state(db, scope, self._latest(db, scope))

    @staticmethod
    def _source(db: sqlite3.Connection, scope: tuple[str, int, str, str], module: ModuleOutline) -> list[dict]:
        saved = {row['outline_id']: row for row in db.execute("""
            SELECT outline_id, content, format FROM lesson_versions WHERE course_id = ? AND course_revision = ?
            ORDER BY revision
        """, scope[:2])}
        lessons = []
        for lesson in module.lessons:
            data = lesson.model_dump(include={'title', 'objective', 'competency_ids'})
            if row := saved.get(lesson.id):
                try:
                    content = LESSON_SCHEMAS[row['format']].model_validate_json(row['content'])
                    data.update(content.model_dump(include={'explanation', 'example', 'summary'}))
                except (KeyError, ValidationError):
                    pass
            lessons.append(data)
        return lessons

    def _reserve(self, scope: tuple[str, int, str, str], request: PrepareExam):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            course, module = self._module(db, scope)
            latest = self._latest(db, scope)
            previous = self._last_submitted(db, scope)
            now = time()
            if latest and latest['submitted_at'] is None:
                if latest['content'] is not None or latest['lease_until'] > now:
                    return self._state(db, scope, latest)
            if previous:
                if previous['id'] != request.previous_form_id or _read_result(previous['result']).passed:
                    return self._state(db, scope, latest)
            elif request.previous_form_id is not None:
                raise HTTPException(409, 'A prova indicada não está disponível para nova tentativa.')
            if not self.available:
                raise GenerationFailure('not_configured')

            old_prompts = [row['prompt'] for row in db.execute(f"""
                SELECT json_extract(question.value, '$.prompt') AS prompt
                FROM module_exams, json_each(module_exams.content, '$.questions') question
                WHERE {_SCOPE}
                ORDER BY ordinal DESC
            """, scope)]
            names = self._competency_names(db, course)
            data = {
                'title': module.title,
                'objective': module.objective,
                'competencies': [{'id': item, 'name': names.get(item, item)} for item in module.competency_ids],
                'lessons': self._source(db, scope, module),
                'previous_prompts': old_prompts[:QUESTION_COUNT * 2],
            }
            token = uuid4().hex
            lease = now + self.settings.gemini_timeout_seconds + 5
            if latest and latest['content'] is None:
                form_id = latest['id']
                db.execute('UPDATE module_exams SET lease_until = ?, claim_token = ? WHERE id = ?',
                           (lease, token, form_id))
            else:
                form_id = uuid4().hex
                ordinal = latest['ordinal'] + 1 if latest else 1
                db.execute("""
                    INSERT INTO module_exams (
                        id, course_id, course_revision, module_id, owner_id, ordinal, created_at, lease_until, claim_token
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (form_id, *scope, ordinal, datetime.now(timezone.utc).isoformat(), lease, token))
            return form_id, token, data, module.competency_ids, old_prompts

    def _save(self, form_id: str, token: str, exam: MasteryExam) -> None:
        with self.connection() as db:
            changed = db.execute("""
                UPDATE module_exams SET content = ?, lease_until = NULL, claim_token = NULL
                WHERE id = ? AND content IS NULL AND claim_token = ?
            """, (exam.model_dump_json(), form_id, token))
            if changed.rowcount != 1:
                raise HTTPException(409, 'A preparação desta prova expirou. Abra a avaliação novamente.')

    def _release(self, form_id: str, token: str) -> None:
        with self.connection() as db:
            db.execute('UPDATE module_exams SET lease_until = 0 WHERE id = ? AND claim_token = ?', (form_id, token))

    async def prepare(self, owner: str, course_id: str, module_id: str, request: PrepareExam) -> ExamState:
        scope = (course_id, request.course_revision, module_id, owner)
        reservation = await run_in_threadpool(self._reserve, scope, request)
        if isinstance(reservation, ExamState):
            return reservation
        form_id, token, data, competency_ids, old_prompts = reservation
        try:
            self.reserve_request()
            async with asyncio.timeout(self.settings.gemini_timeout_seconds):
                raw = await self.gateway.generate(EXAM_PROMPT, data, MasteryExam)
            exam = _checked_exam(raw, competency_ids, old_prompts)
            await run_in_threadpool(self._save, form_id, token, exam)
        except TimeoutError:
            raise GenerationFailure('timeout') from None
        except (ValidationError, ValueError):
            raise GenerationFailure('invalid_response') from None
        finally:
            with suppress(sqlite3.Error):
                await run_in_threadpool(self._release, form_id, token)
        return await run_in_threadpool(self.get, owner, course_id, module_id, request.course_revision)

    def _digest(self, scope: tuple[str, int, str, str], request: SubmitExam) -> bytes:
        if self.digest_key is None:
            raise HTTPException(503, 'A correção está indisponível no momento.')
        encoded = json.dumps([scope, request.form_id, request.answers], sort_keys=True).encode('utf-8')
        return hmac.digest(self.digest_key, encoded, 'sha256')

    def submit(self, owner: str, course_id: str, module_id: str, request: SubmitExam) -> ExamResult:
        scope = (course_id, request.course_revision, module_id, owner)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            course, module = self._module(db, scope)
            row = db.execute(f'SELECT * FROM module_exams WHERE {_SCOPE} AND id = ?', (*scope, request.form_id)).fetchone()
            if row is None or row['content'] is None:
                raise HTTPException(404, 'Avaliação não encontrada.')
            digest = self._digest(scope, request)
            if row['submitted_at'] is not None:
                if not hmac.compare_digest(row['answer_digest'], digest):
                    raise HTTPException(409, 'Esta avaliação já foi corrigida com outro conjunto de respostas.')
                return _read_result(row['result'])

            questions = _read_exam(row['content']).questions
            if request.answers.keys() != {question.id for question in questions}:
                raise HTTPException(422, 'Responda a todas as questões desta avaliação.')
            correct: Counter[str] = Counter()
            totals: Counter[str] = Counter()
            for question in questions:
                passed, _ = grade(question, ChoiceAnswer(kind='multiple_choice', option_id=request.answers[question.id]))
                correct[question.competency_id] += int(passed)
                totals[question.competency_id] += 1

            names = self._competency_names(db, course)
            evidence = [CompetencyEvidence(id=item, name=names.get(item, item), correct=correct[item], total=totals[item])
                        for item in module.competency_ids]
            correct_count = correct.total()
            passed = passing_score(correct_count, len(questions), evidence)
            review = {item.id for item in evidence if item.correct < item.total}
            result = ExamResult(
                form_id=request.form_id, submitted_at=datetime.now(timezone.utc).isoformat(), correct=correct_count,
                total=len(questions), score=correct_count * 100 // len(questions), passed=passed, competencies=evidence,
                reinforcement=[Reinforcement(outline_id=lesson.id, title=lesson.title) for lesson in module.lessons
                               if not passed and review.intersection(lesson.competency_ids)],
            )
            db.execute("""
                UPDATE module_exams SET submitted_at = ?, answer_digest = ?, result = ? WHERE id = ?
            """, (result.submitted_at, digest, result.model_dump_json(), request.form_id))
            if passed:
                db.execute("""
                    INSERT INTO module_mastery (course_id, course_revision, module_id, owner_id, exam_id, granted_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(course_id, course_revision, module_id, owner_id) DO NOTHING
                """, (*scope, request.form_id, result.submitted_at))
            return result

    def install_routes(self, app: FastAPI, require_account) -> None:
        route = '/api/courses/{course_id}/modules/{module_id}/assessment'

        @app.get(route, response_model=ExamState)
        def get_exam(course_id: str, module_id: str, course_revision: int = Query(ge=1, le=MAX_REVISION),
                     owner: str = Depends(require_account)):
            return self.get(owner, course_id, module_id, course_revision)

        @app.post(route, response_model=ExamState)
        async def prepare_exam(course_id: str, module_id: str, request: PrepareExam,
                               owner: str = Depends(require_account)):
            return await self.prepare(owner, course_id, module_id, request)

        @app.post(route + '/submit', response_model=ExamResult)
        def submit_exam(course_id: str, module_id: str, request: SubmitExam, owner: str = Depends(require_account)):
            return self.submit(owner, course_id, module_id, request)
