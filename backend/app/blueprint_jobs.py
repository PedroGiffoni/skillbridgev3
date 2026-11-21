"""SQLite job queue for private Gemini course outlines."""
import asyncio
import hashlib
import json
import logging
from math import ceil
from pathlib import Path
import sqlite3
from time import monotonic, time
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool

from .blueprint import (
    PROMPT, PROMPT_VERSION, SCHEMA_VERSION, CourseBlueprint, blueprint_input, blueprint_response_schema,
    validate_blueprint,
)
from .catalog import CAREER_LABELS
from .gemini import FAILURES, Gemini, GenerationFailure, GenerationResult
from .learning import CourseContent, CourseDetail, LearningStore
from .lesson_content import (
    LESSON_SCHEMAS, PROMPT as LESSON_PROMPT, PROMPT_VERSION as LESSON_PROMPT_VERSION,
    SCHEMA_VERSION as LESSON_SCHEMA_VERSION, LessonPublication, validate_lesson,
)
from .library import MAX_REVISION, CourseLibrary, LessonRead
from .schemas import Model

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
POLL_SECONDS = 0.5
FAILURE_DETAILS = {
    **FAILURES,
    'interrupted': 'A geração foi interrompida.',
    'invalid_response': 'O plano do curso retornado não passou pela validação.',
}


class ConsentRequest(Model):
    consent: bool = Field(strict=True)
    retry_attempt: int | None = Field(default=None, strict=True, ge=0, le=MAX_ATTEMPTS)

    @field_validator('consent')
    @classmethod
    def requires_consent(cls, value):
        if not value:
            raise ValueError('Consentimento necessário para gerar o curso.')
        return value


class GenerationRequest(ConsentRequest):
    plan_id: str = Field(pattern=r'^[0-9a-f]{32}$')


class LessonRequest(ConsentRequest):
    course_revision: int = Field(strict=True, ge=1, le=MAX_REVISION)


class JobFailure(BaseModel):
    code: str
    detail: str
    retryable: bool


class JobDetail(BaseModel):
    id: str
    plan_id: str
    plan_revision: int
    status: Literal['queued', 'running', 'ready', 'failed', 'needs_review']
    attempts: int
    prompt_version: int
    schema_version: int
    duration_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    retry_after_seconds: int
    error: JobFailure | None
    draft: CourseDetail | None
    lesson: LessonRead | None


def migrate_jobs(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 2').fetchone():
        return
    db.execute("""
        CREATE TABLE generation_jobs (
            id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE,
            plan_id TEXT NOT NULL,
            plan_revision INTEGER NOT NULL,
            model TEXT NOT NULL,
            prompt_version INTEGER NOT NULL,
            schema_version INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'ready', 'failed', 'needs_review')),
            attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            created_at REAL NOT NULL,
            claim_token TEXT,
            lease_until REAL,
            retry_after REAL,
            reason TEXT,
            duration_ms INTEGER,
            input_tokens INTEGER,
            output_tokens INTEGER,
            course_id TEXT,
            course_revision INTEGER,
            FOREIGN KEY (plan_id, plan_revision) REFERENCES study_plan_versions(plan_id, revision) ON DELETE CASCADE,
            FOREIGN KEY (course_id, course_revision) REFERENCES course_versions(course_id, revision) ON DELETE CASCADE
        )
    """)
    db.execute('CREATE INDEX generation_jobs_dispatch ON generation_jobs (status, lease_until, created_at)')
    db.execute('CREATE INDEX generation_jobs_plan ON generation_jobs (plan_id, plan_revision)')
    db.execute('INSERT INTO learning_migrations (version) VALUES (2)')


class BlueprintJobs:
    def __init__(self, learning: LearningStore, database: Path, model: str, timeout: float, configured: bool, gateway, require_gemini):
        self.learning = learning
        self.library = CourseLibrary(learning)
        self.connection = learning.connection
        self.database = database
        self.model = model
        self.timeout = timeout
        self.configured = configured
        self.gateway = gateway
        self.require_gemini = require_gemini

    def enqueue(self, owner_id: str, request: GenerationRequest) -> JobDetail:
        plan = self.learning.get_plan(owner_id, request.plan_id)
        fingerprint = hashlib.sha256(json.dumps([
            plan.id, plan.revision, self.model, PROMPT_VERSION, SCHEMA_VERSION,
        ]).encode()).hexdigest()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            owned = db.execute("""
                SELECT h.profession FROM study_plan_versions v JOIN assessment_history h ON h.id = v.plan_id
                WHERE v.plan_id = ? AND v.revision = ? AND h.owner_id = ? AND h.result IS NOT NULL
            """, (plan.id, plan.revision, owner_id)).fetchone()
            if owned is None:
                raise HTTPException(404, 'Plano de estudos não encontrado.')
            if owned['profession'] not in CAREER_LABELS:
                raise HTTPException(422, 'Gere um plano para uma carreira do catálogo atual.')
            now = time()
            existing = db.execute('SELECT id FROM generation_jobs WHERE fingerprint = ?', (fingerprint,)).fetchone()
            job_id = existing['id'] if existing else uuid4().hex
            if existing is None:
                if not self.configured:
                    raise GenerationFailure('not_configured')
                db.execute("""
                    INSERT INTO generation_jobs (
                        id, fingerprint, plan_id, plan_revision, model, prompt_version, schema_version, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                """, (job_id, fingerprint, plan.id, plan.revision, self.model, PROMPT_VERSION, SCHEMA_VERSION, now))
            elif request.retry_attempt is not None and self.configured:
                db.execute("""
                    UPDATE generation_jobs SET status = 'queued', reason = NULL, retry_after = NULL,
                        duration_ms = NULL, input_tokens = NULL, output_tokens = NULL
                    WHERE id = ? AND status IN ('failed', 'needs_review') AND attempts = ? AND attempts < ?
                        AND (retry_after IS NULL OR retry_after <= ?)
                """, (job_id, request.retry_attempt, MAX_ATTEMPTS, now))
        return self.get(owner_id, job_id)

    def latest_blueprint(self, owner: str, plan_id: str) -> JobDetail | None:
        plan = self.learning.get_plan(owner, plan_id)
        with self.connection() as db:
            row = db.execute("""
                SELECT id FROM generation_jobs WHERE plan_id = ? AND plan_revision = ? AND lesson_outline_id IS NULL
                ORDER BY (model = ? AND prompt_version = ? AND schema_version = ?) DESC, created_at DESC, id LIMIT 1
            """, (plan.id, plan.revision, self.model, PROMPT_VERSION, SCHEMA_VERSION)).fetchone()
        return self.get(owner, row['id']) if row else None

    def enqueue_lesson(self, owner: str, course_id: str, outline_id: str, request: LessonRequest) -> JobDetail:
        revision = request.course_revision
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            course, outline = self.library.owned_outline(db, owner, course_id, revision, outline_id)
            existing = db.execute("""
                SELECT * FROM generation_jobs WHERE course_id = ? AND course_revision = ? AND lesson_outline_id = ?
            """, (course_id, revision, outline.id)).fetchone()
            now = time()
            job_id = existing['id'] if existing else uuid4().hex
            desired = (self.model, LESSON_PROMPT_VERSION, LESSON_SCHEMA_VERSION)
            if existing is None:
                if not self.configured:
                    raise GenerationFailure('not_configured')
                fingerprint = hashlib.sha256(json.dumps(['lesson', course_id, revision, outline.id]).encode()).hexdigest()
                db.execute("""
                    INSERT INTO generation_jobs (
                        id, fingerprint, plan_id, plan_revision, model, prompt_version, schema_version,
                        status, created_at, course_id, course_revision, lesson_outline_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?)
                """, (job_id, fingerprint, course.plan_id, course.plan_revision, *desired, now, course_id, revision, outline.id))
            elif self.configured and existing['attempts'] < MAX_ATTEMPTS:
                old_config = (existing['model'], existing['prompt_version'], existing['schema_version']) != desired
                inactive = existing['status'] == 'queued' or (
                    existing['status'] == 'running' and (existing['lease_until'] or 0) <= now
                )
                retry = (existing['status'] in ('failed', 'needs_review')
                         and existing['attempts'] == request.retry_attempt and (existing['retry_after'] or 0) <= now)
                if (old_config and inactive) or retry:
                    db.execute("""
                        UPDATE generation_jobs SET status = 'queued', model = ?, prompt_version = ?, schema_version = ?,
                            reason = NULL, retry_after = NULL, duration_ms = NULL, input_tokens = NULL, output_tokens = NULL,
                            claim_token = NULL, lease_until = NULL
                        WHERE id = ?
                    """, (*desired, job_id))
        return self.get(owner, job_id)

    def get(self, owner_id: str, job_id: str) -> JobDetail:
        with self.connection() as db:
            job = db.execute("""
                SELECT j.*, v.created_at AS draft_created_at, v.content AS draft_content, v.published AS draft_published
                FROM generation_jobs j JOIN assessment_history h ON h.id = j.plan_id
                LEFT JOIN course_versions v ON v.course_id = j.course_id AND v.revision = j.course_revision
                WHERE j.id = ? AND h.owner_id = ? AND h.result IS NOT NULL
            """, (job_id, owner_id)).fetchone()
            lesson = None
            if job and job['lesson_outline_id'] is not None:
                if job['status'] == 'ready':
                    lesson = self.library.view_lesson(db, owner_id, job_id)
                else:
                    self.library.owned_outline(db, owner_id, job['course_id'], job['course_revision'],
                                               job['lesson_outline_id'])
        if job is None:
            raise HTTPException(404, 'Solicitação de curso não encontrada.')
        draft = None
        if job['status'] == 'ready' and job['lesson_outline_id'] is None:
            try:
                draft = CourseDetail(
                    id=job['course_id'], plan_id=job['plan_id'], plan_revision=job['plan_revision'],
                    revision=job['course_revision'], created_at=job['draft_created_at'],
                    published=bool(job['draft_published']), content=CourseContent.model_validate_json(job['draft_content']),
                )
            except (ValidationError, ValueError, TypeError):
                raise HTTPException(500, 'Não foi possível abrir o rascunho do curso.') from None
        status, reason = job['status'], job['reason']
        expected = ((self.model, PROMPT_VERSION, SCHEMA_VERSION) if job['lesson_outline_id'] is None
                    else (self.model, LESSON_PROMPT_VERSION, LESSON_SCHEMA_VERSION))
        if ((job['model'], job['prompt_version'], job['schema_version']) != expected
                and (status == 'queued' or status == 'running' and (job['lease_until'] or 0) <= time())):
            status, reason = 'failed', 'configuration'
        error = None if reason is None else JobFailure(
            code=reason, detail=FAILURE_DETAILS[reason], retryable=job['attempts'] < MAX_ATTEMPTS,
        )
        return JobDetail(
            id=job['id'], plan_id=job['plan_id'], plan_revision=job['plan_revision'], status=status,
            attempts=job['attempts'], prompt_version=job['prompt_version'], schema_version=job['schema_version'],
            duration_ms=job['duration_ms'], input_tokens=job['input_tokens'], output_tokens=job['output_tokens'],
            retry_after_seconds=max(0, ceil((job['retry_after'] or 0) - time())), error=error, draft=draft, lesson=lesson,
        )

    def _claim(self) -> dict | None:
        if not self.database.is_file():
            return None
        with self.connection() as db:
            now = time()
            row = db.execute("""
                SELECT j.*, h.owner_id, h.profession FROM generation_jobs j
                JOIN assessment_history h ON h.id = j.plan_id
                WHERE j.model = ? AND (
                    (j.lesson_outline_id IS NULL AND j.prompt_version = ? AND j.schema_version = ?)
                    OR (j.lesson_outline_id IS NOT NULL AND j.prompt_version = ? AND j.schema_version = ?)
                ) AND (j.status = 'queued' OR (j.status = 'running' AND j.lease_until <= ?))
                ORDER BY j.created_at, j.id LIMIT 1
            """, (self.model, PROMPT_VERSION, SCHEMA_VERSION, LESSON_PROMPT_VERSION, LESSON_SCHEMA_VERSION, now)).fetchone()
            if row is None:
                return None
            db.execute('BEGIN IMMEDIATE')
            if row['attempts'] >= MAX_ATTEMPTS:
                db.execute("""
                    UPDATE generation_jobs SET status = 'failed', reason = 'interrupted',
                        claim_token = NULL, lease_until = NULL
                    WHERE id = ? AND status = 'running' AND lease_until <= ? AND attempts >= ?
                """, (row['id'], now, MAX_ATTEMPTS))
                return None
            token = uuid4().hex
            updated = db.execute("""
                UPDATE generation_jobs SET status = 'running', attempts = attempts + 1,
                    claim_token = ?, lease_until = ?
                WHERE id = ? AND model = ? AND prompt_version = ? AND schema_version = ? AND attempts < ?
                    AND (status = 'queued' OR (status = 'running' AND lease_until <= ?))
            """, (token, now + self.timeout + 15, row['id'], row['model'], row['prompt_version'],
                  row['schema_version'], MAX_ATTEMPTS, now))
            return {**dict(row), 'claim_token': token} if updated.rowcount == 1 else None

    def _finish(
        self, job: dict, status: str, duration_ms: int, *, reason: str | None = None,
        content: CourseContent | LessonPublication | None = None, usage: GenerationResult | None = None,
        provider_status: int | None = None,
    ) -> None:
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            claim = (job['id'], job['claim_token'])
            active = db.execute("""
                SELECT 1 FROM generation_jobs WHERE id = ? AND claim_token = ? AND status = 'running'
            """, claim).fetchone()
            if active is None:
                return
            draft = None
            if isinstance(content, LessonPublication):
                self.library.save_lesson(db, job, content)
            elif content is not None:
                draft = self.learning.write_course_version(
                    db, job['owner_id'], job['plan_id'], job['plan_revision'], content,
                )
            db.execute("""
                UPDATE generation_jobs SET status = ?, reason = ?, retry_after = ?, duration_ms = ?,
                    input_tokens = ?, output_tokens = ?, course_id = ?, course_revision = ?, provider_status = ?,
                    claim_token = NULL, lease_until = NULL,
                    attempts = CASE WHEN ? = 'not_configured' THEN attempts - 1 ELSE attempts END
                WHERE id = ? AND claim_token = ?
            """, (status, reason, time() + 60 if reason in ('quota', 'configuration', 'access_denied') else None, duration_ms,
                  usage.input_tokens if usage else None, usage.output_tokens if usage else None,
                  draft.id if draft else job['course_id'], draft.revision if draft else job['course_revision'],
                  provider_status, reason, *claim))

    def _release_interrupted(self, job: dict) -> None:
        with self.connection() as db:
            db.execute("""
                UPDATE generation_jobs SET status = CASE WHEN attempts < ? THEN 'queued' ELSE 'failed' END,
                    reason = CASE WHEN attempts < ? THEN NULL ELSE 'interrupted' END,
                    claim_token = NULL, lease_until = NULL
                WHERE id = ? AND claim_token = ? AND status = 'running'
            """, (MAX_ATTEMPTS, MAX_ATTEMPTS, job['id'], job['claim_token']))

    async def _process(self, job: dict) -> None:
        start = monotonic()
        content = usage = reason = provider_status = None
        status = 'failed'
        try:
            outline = None
            plan = await run_in_threadpool(self.learning.get_plan, job['owner_id'], job['plan_id'], job['plan_revision'])
            if job['lesson_outline_id'] is None:
                prompt, schema = PROMPT, CourseBlueprint
                data = blueprint_input(plan, job['profession'])
            else:
                course, outline = await run_in_threadpool(
                    self.library.get_source, job['owner_id'], job['course_id'], job['course_revision'], job['lesson_outline_id'],
                )
                prompt, schema = LESSON_PROMPT, LESSON_SCHEMAS[outline.format]
                data = {
                    'career': job['profession'], 'course': course.content.title,
                    'lesson': outline.model_dump(exclude={'id'}),
                    'competencies': [{'id': gap.competency_id, 'name': gap.name} for gap in plan.assessment.gaps
                                     if gap.competency_id in outline.competency_ids],
                }
            self.require_gemini()
            async with asyncio.timeout(self.timeout):
                if isinstance(self.gateway, Gemini):
                    provider_schema = blueprint_response_schema() if outline is None else None
                    usage = await self.gateway.generate_with_usage(prompt, data, schema, provider_schema=provider_schema)
                else:
                    usage = GenerationResult(await self.gateway.generate(prompt, data, schema))
            content = validate_lesson(outline, usage.content) if outline else validate_blueprint(usage.content, plan)
            status = 'ready'
        except asyncio.CancelledError:
            await run_in_threadpool(self._release_interrupted, job)
            raise
        except GenerationFailure as failure:
            reason, provider_status = failure.reason, failure.provider_status
        except TimeoutError:
            reason = 'timeout'
        except (ValidationError, ValueError, TypeError):
            reason = 'invalid_response'
        except HTTPException:
            reason = 'interrupted'
        if reason == 'invalid_response':
            status = 'needs_review'
        elapsed = round((monotonic() - start) * 1000)
        try:
            await run_in_threadpool(self._finish, job, status, elapsed, reason=reason, content=content, usage=usage,
                                    provider_status=provider_status)
        except sqlite3.OperationalError as error:
            if (getattr(error, 'sqlite_errorcode', 0) & 0xff) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise
            await asyncio.sleep(0.2)
            await run_in_threadpool(self._finish, job, status, elapsed, reason=reason, content=content, usage=usage,
                                    provider_status=provider_status)

    async def run(self) -> None:
        while True:
            try:
                job = await run_in_threadpool(self._claim)
                if job is not None:
                    await self._process(job)
                    continue
            except sqlite3.Error:
                # The transaction rolls back and the previous claim eventually expires.
                logger.warning('blueprint_job_storage_failure')
            except Exception:
                logger.warning('blueprint_job_processing_failure')
            await asyncio.sleep(POLL_SECONDS)

    def install_routes(self, app: FastAPI, require_account) -> None:
        self.library.install_routes(app, require_account)

        @app.get('/api/study-plans/{plan_id}/course-job', response_model=dict[str, JobDetail | None])
        def course_job(plan_id: str, owner_id: str = Depends(require_account)):
            return {'job': self.latest_blueprint(owner_id, plan_id)}

        @app.post('/api/courses/{course_id}/lessons/{outline_id}/generate', response_model=JobDetail, status_code=202)
        def request_lesson(course_id: str, outline_id: str, request: LessonRequest, response: Response,
                           owner_id: str = Depends(require_account)):
            job = self.enqueue_lesson(owner_id, course_id, outline_id, request)
            if job.retry_after_seconds:
                response.headers['Retry-After'] = str(job.retry_after_seconds)
            return job

        @app.post('/api/courses/generate', response_model=JobDetail, status_code=202)
        def request_generation(request: GenerationRequest, response: Response, owner_id: str = Depends(require_account)):
            job = self.enqueue(owner_id, request)
            if job.retry_after_seconds:
                response.headers['Retry-After'] = str(job.retry_after_seconds)
            return job

        @app.get('/api/courses/jobs/{job_id}', response_model=JobDetail)
        def generation_status(job_id: str, owner_id: str = Depends(require_account)):
            return self.get(owner_id, job_id)
