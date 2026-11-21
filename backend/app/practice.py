"""Server-side formative grading for immutable lesson revisions."""
from datetime import datetime, timezone
import hmac
import json
import sqlite3
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError, field_validator

from .blueprint import Identifier
from .lesson_content import (
    LESSON_SCHEMAS, SCHEMA_VERSION, BlankExercise, ChoiceExercise, OrderExercise,
)
from .module_access import assert_lesson_open
from .schemas import Model, normalize


Exercise = ChoiceExercise | OrderExercise | BlankExercise
HINTS = {
    'multiple_choice': 'Compare cada alternativa com o exemplo e procure a que atende ao objetivo da lição.',
    'order_steps': 'Identifique o que precisa acontecer primeiro. Depois, confira o que cada passo precisa receber.',
    'fill_blank': 'Leia a frase inteira e procure na explicação o conceito que completa o sentido.',
}


class ChoiceAnswer(Model):
    kind: Literal['multiple_choice']
    option_id: Identifier


class OrderAnswer(Model):
    kind: Literal['order_steps']
    step_ids: list[Identifier] = Field(min_length=3, max_length=6)


class BlankAnswer(Model):
    kind: Literal['fill_blank']
    text: str = Field(min_length=1, max_length=80)

    @field_validator('text')
    @classmethod
    def normalize_blank(cls, value: str) -> str:
        result = normalize(value).casefold()
        if not result:
            raise ValueError('Preencha a lacuna com uma resposta curta.')
        return result


Answer = Annotated[ChoiceAnswer | OrderAnswer | BlankAnswer, Field(discriminator='kind')]


class HintRequest(Model):
    attempt_id: str = Field(pattern=r'^[0-9a-f]{32}$')


class AttemptRequest(HintRequest):
    answer: Answer
    hint_receipt: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class HintResult(BaseModel):
    text: str
    receipt: str


class AttemptResult(BaseModel):
    id: str
    created_at: str
    correct: bool
    hint_used: bool
    feedback: list[str]


class PracticeProgress(BaseModel):
    attempts: int = 0
    completed: bool = False
    latest_attempt: AttemptResult | None = None


class PracticeResult(BaseModel):
    attempt: AttemptResult
    practice: PracticeProgress


def migrate_practice(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 4').fetchone():
        return
    db.execute("""
        CREATE TABLE practice_attempts (
            lesson_id TEXT NOT NULL REFERENCES lesson_versions(id) ON DELETE CASCADE,
            owner_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            attempt_id TEXT NOT NULL,
            hint_used INTEGER NOT NULL CHECK (hint_used IN (0, 1)),
            created_at TEXT NOT NULL,
            response_digest BLOB NOT NULL,
            correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
            feedback TEXT NOT NULL,
            PRIMARY KEY (lesson_id, owner_id, attempt_id)
        )
    """)
    db.execute("""
        CREATE INDEX practice_attempts_progress ON practice_attempts (lesson_id, owner_id, created_at DESC)
    """)
    db.execute("""
        CREATE TRIGGER freeze_practice_attempt BEFORE UPDATE ON practice_attempts
        BEGIN SELECT RAISE(ABORT, 'Submitted practice is immutable'); END
    """)
    db.execute('INSERT INTO learning_migrations (version) VALUES (4)')


def owned_lesson(db: sqlite3.Connection, owner: str, lesson_id: str) -> sqlite3.Row:
    row = db.execute("""
        SELECT l.*, v.content AS course_content FROM lesson_versions l
        JOIN course_versions v ON v.course_id = l.course_id AND v.revision = l.course_revision
        JOIN courses c ON c.id = l.course_id
        JOIN assessment_history h ON h.id = c.plan_id
        WHERE l.id = ? AND h.owner_id = ? AND h.result IS NOT NULL AND v.published = 1
    """, (lesson_id, owner)).fetchone()
    if row is None:
        raise HTTPException(404, 'Lição não encontrada.')
    assert_lesson_open(db, owner, row)
    return row


def result_of(row: sqlite3.Row) -> AttemptResult:
    return AttemptResult(id=row['attempt_id'], created_at=row['created_at'], correct=bool(row['correct']),
                         hint_used=bool(row['hint_used']), feedback=json.loads(row['feedback']))


def practice_progress(db: sqlite3.Connection, owner: str, lesson_id: str) -> PracticeProgress:
    newest = db.execute("""
        SELECT *, COUNT(*) OVER () AS attempts, MAX(correct) OVER () AS completed
        FROM practice_attempts WHERE lesson_id = ? AND owner_id = ?
        ORDER BY created_at DESC, attempt_id DESC LIMIT 1
    """, (lesson_id, owner)).fetchone()
    if newest is None:
        return PracticeProgress()
    return PracticeProgress(attempts=newest['attempts'], completed=bool(newest['completed']),
                            latest_attempt=result_of(newest))


def grade(exercise: Exercise, answer: Answer) -> tuple[bool, list[str]]:
    if isinstance(exercise, ChoiceExercise) and isinstance(answer, ChoiceAnswer):
        option = next((item for item in exercise.options if item.id == answer.option_id), None)
        if option is not None:
            return option.id == exercise.correct_option_id, [option.feedback]
    elif isinstance(exercise, OrderExercise) and isinstance(answer, OrderAnswer):
        steps = {step.id: step for step in exercise.steps}
        if len(answer.step_ids) == len(steps) and set(answer.step_ids) == steps.keys():
            if answer.step_ids == exercise.correct_order:
                return True, [steps[step_id].feedback for step_id in answer.step_ids]
            positions = sum(actual == expected for actual, expected in zip(answer.step_ids, exercise.correct_order))
            return False, [f'{positions} de {len(steps)} passos estão na posição esperada. Revise a sequência.']
    elif isinstance(exercise, BlankExercise) and isinstance(answer, BlankAnswer):
        correct = answer.text == normalize(exercise.answer).casefold()
        return correct, [exercise.correct_feedback if correct else exercise.incorrect_feedback]
    raise HTTPException(422, 'A resposta não corresponde ao formato ou aos itens desta prática.')


class PracticeStore:
    def __init__(self, connection, digest_key: bytes | None):
        self.connection = connection
        self.digest_key = digest_key

    def hint_receipt(self, parameters: tuple[str, str, str]) -> str:
        if self.digest_key is None:
            raise HTTPException(503, 'A prática está indisponível no momento.')
        encoded = json.dumps(parameters, ensure_ascii=False).encode('utf-8')
        return hmac.digest(self.digest_key, b'hint:' + encoded, 'sha256').hex()

    def hint(self, owner: str, lesson_id: str, request: HintRequest) -> HintResult:
        parameters = (lesson_id, owner, request.attempt_id)
        with self.connection() as db:
            lesson = owned_lesson(db, owner, lesson_id)
            text = HINTS.get(lesson['format'])
            if text is None:
                raise HTTPException(409, 'Formato de prática indisponível.')
            if db.execute("""
                SELECT 1 FROM practice_attempts WHERE lesson_id = ? AND owner_id = ? AND attempt_id = ?
            """, parameters).fetchone():
                raise HTTPException(409, 'Abra uma nova tentativa antes de pedir uma dica.')
        return HintResult(text=text, receipt=self.hint_receipt(parameters))

    def submit(self, owner: str, lesson_id: str, request: AttemptRequest) -> PracticeResult:
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            lesson = owned_lesson(db, owner, lesson_id)
            if self.digest_key is None:
                raise HTTPException(503, 'A correção está indisponível no momento.')
            parameters = (lesson_id, owner, request.attempt_id)
            encoded = json.dumps([*parameters, request.answer.model_dump(mode='json')],
                                 ensure_ascii=False, sort_keys=True).encode('utf-8')
            digest = hmac.digest(self.digest_key, encoded, 'sha256')
            previous = db.execute("""
                SELECT * FROM practice_attempts WHERE lesson_id = ? AND owner_id = ? AND attempt_id = ?
            """, parameters).fetchone()
            if previous:
                if not hmac.compare_digest(previous['response_digest'], digest):
                    raise HTTPException(409, 'Esta tentativa já foi salva com outra resposta.')
                attempt = result_of(previous)
            else:
                try:
                    if lesson['schema_version'] != SCHEMA_VERSION:
                        raise ValueError('Schema de prática incompatível.')
                    content = LESSON_SCHEMAS[lesson['format']].model_validate_json(lesson['content'])
                except (KeyError, ValidationError, ValueError):
                    raise HTTPException(500, 'Não foi possível carregar esta prática.') from None
                hint_used = request.hint_receipt is not None
                if hint_used and not hmac.compare_digest(request.hint_receipt, self.hint_receipt(parameters)):
                    raise HTTPException(422, 'Peça uma nova dica para esta tentativa.')
                correct, feedback = grade(content.exercise, request.answer)
                created_at = datetime.now(timezone.utc).isoformat()
                db.execute("""
                    INSERT INTO practice_attempts
                        (lesson_id, owner_id, attempt_id, hint_used, created_at, response_digest, correct, feedback)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (*parameters, hint_used, created_at, digest, correct, json.dumps(feedback, ensure_ascii=False)))
                attempt = AttemptResult(id=request.attempt_id, created_at=created_at, correct=correct,
                                        hint_used=hint_used, feedback=feedback)
            return PracticeResult(attempt=attempt, practice=practice_progress(db, owner, lesson_id))

    def install_routes(self, app: FastAPI, require_account) -> None:
        @app.post('/api/exercises/{lesson_id}/hint', response_model=HintResult)
        def practice_hint(lesson_id: str, request: HintRequest, owner: str = Depends(require_account)):
            return self.hint(owner, lesson_id, request)

        @app.post('/api/exercises/{lesson_id}/attempts', response_model=PracticeResult)
        def practice_attempt(lesson_id: str, request: AttemptRequest, owner: str = Depends(require_account)):
            return self.submit(owner, lesson_id, request)
