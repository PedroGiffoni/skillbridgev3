"""Private study materials and resumable audio generation for a saved lesson."""
import asyncio
from collections.abc import Callable
import logging
from math import ceil
from pathlib import Path
import re
import sqlite3
from time import monotonic, time
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi import Path as PathParameter
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

from .blueprint_jobs import MAX_ATTEMPTS, POLL_SECONDS, ConsentRequest, JobFailure
from .gemini import FAILURES, GenerationFailure
from .library import CourseLibrary
from .practice import owned_lesson
from .theme_content import GradeRequest, THEME_PROMPT, ThemePack, grade_theme, public_theme, validate_theme

AudioFormat = Literal['video', 'audiobook', 'podcast']
AssessmentFormat = Literal['quiz', 'simulation']
AUDIO_FORMATS = ('video', 'audiobook', 'podcast')
logger = logging.getLogger(__name__)
VERSION = 1
DETAILS = {
    **FAILURES,
    'invalid_response': 'O material gerado não passou pela validação.',
    'interrupted': 'A preparação do material foi interrompida.',
}


class ThemeJobState(BaseModel):
    status: Literal['idle', 'queued', 'running', 'ready', 'failed', 'needs_review'] = 'idle'
    attempts: int = 0
    retry_after_seconds: int = 0
    error: JobFailure | None = None


class ThemeAudioState(ThemeJobState):
    segments: int = 0


class ThemeState(BaseModel):
    study: ThemeJobState
    content: dict | None
    audio: dict[str, ThemeAudioState]
    text_available: bool
    audio_available: bool


def migrate_themes(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 5').fetchone():
        return
    db.execute("""
        CREATE TABLE theme_jobs (
            lesson_id TEXT NOT NULL REFERENCES lesson_versions(id) ON DELETE CASCADE,
            kind TEXT NOT NULL CHECK (kind IN ('study', 'video', 'audiobook', 'podcast')),
            model TEXT NOT NULL,
            version INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'ready', 'failed', 'needs_review')),
            attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            created_at REAL NOT NULL,
            lease_until REAL,
            claim_token TEXT,
            reason TEXT,
            retry_after REAL,
            content TEXT,
            segments INTEGER NOT NULL DEFAULT 0 CHECK (segments >= 0),
            PRIMARY KEY (lesson_id, kind)
        )
    """)
    db.execute('CREATE INDEX theme_job_dispatch ON theme_jobs (status, version, created_at)')
    db.execute("""
        CREATE TABLE theme_audio (
            lesson_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            model TEXT NOT NULL,
            version INTEGER NOT NULL,
            segment INTEGER NOT NULL CHECK (segment >= 0),
            wav BLOB NOT NULL,
            PRIMARY KEY (lesson_id, kind, model, version, segment),
            FOREIGN KEY (lesson_id, kind) REFERENCES theme_jobs (lesson_id, kind) ON DELETE CASCADE
        )
    """)
    db.execute('INSERT INTO learning_migrations (version) VALUES (5)')


def _audio_script(pack: ThemePack, kind: str) -> list[list[tuple[str, str]]]:
    if kind == 'video':
        return [[('narrator', slide.narration)] for slide in pack.slides]
    if kind == 'audiobook':
        return [[('narrator', section.title + '. ' + section.text)] for section in pack.chapter.sections]
    return [[(turn.speaker, turn.text) for turn in pack.podcast.turns]]


def _range(value: str, size: int) -> tuple[int, int]:
    match = re.fullmatch(r'bytes=([0-9]{0,14})-([0-9]{0,14})', value.strip(), re.ASCII)
    if match:
        first, last = match.groups()
        if first:
            start, end = int(first), min(int(last), size - 1) if last else size - 1
        else:
            start, end = max(0, size - int(last or '0')), size - 1
        if start <= end:
            return start, end
    raise HTTPException(416, 'Intervalo de áudio indisponível.',
                        headers={'Accept-Ranges': 'bytes', 'Content-Range': f'bytes */{size}'})


class ThemeMaterials:
    def __init__(self, connection, database: Path, settings, generator, speech, reserve_request: Callable[[], None]):
        self.connection = connection
        self.database = database
        self.timeout = settings.gemini_timeout_seconds
        self.modes = {
            'study': (settings.ready, settings.gemini_model),
            **dict.fromkeys(AUDIO_FORMATS, (settings.gemini_tts_ready, settings.gemini_tts_model)),
        }
        self.generator = generator
        self.speech = speech
        self.reserve_request = reserve_request

    @staticmethod
    def _stored_pack(db: sqlite3.Connection, lesson_id: str) -> ThemePack | None:
        row = db.execute("""
            SELECT content, version FROM theme_jobs WHERE lesson_id = ? AND kind = 'study' AND status = 'ready'
        """, (lesson_id,)).fetchone()
        if row is None:
            return None
        try:
            if row['version'] != VERSION:
                raise ValueError('Versão dos materiais incompatível.')
            return ThemePack.model_validate_json(row['content'])
        except (ValidationError, ValueError, TypeError):
            raise HTTPException(500, 'Não foi possível abrir os materiais salvos deste tema.') from None

    def _state(self, row: sqlite3.Row | None, kind: str) -> ThemeAudioState:
        if row is None:
            return ThemeAudioState()
        available, model = self.modes[kind]
        status, reason = row['status'], row['reason']
        dormant = status == 'queued' or (status == 'running' and (row['lease_until'] or 0) <= time())
        if dormant and (not available or row['model'] != model or row['version'] != VERSION):
            reason = 'configuration' if available else 'not_configured'
            status = 'failed'
        error = None if not reason else JobFailure(
            code=reason, detail=DETAILS[reason], retryable=available and row['attempts'] < MAX_ATTEMPTS,
        )
        return ThemeAudioState(status=status, attempts=row['attempts'], segments=row['segments'],
                               retry_after_seconds=max(0, ceil((row['retry_after'] or 0) - time())), error=error)

    def get(self, owner: str, lesson_id: str) -> ThemeState:
        with self.connection() as db:
            db.execute('BEGIN')
            owned_lesson(db, owner, lesson_id)
            rows = {row['kind']: row for row in db.execute("""
                SELECT kind, model, version, status, attempts, lease_until, reason, retry_after, segments
                FROM theme_jobs WHERE lesson_id = ?
            """, (lesson_id,))}
            pack = self._stored_pack(db, lesson_id)
        return ThemeState(study=self._state(rows.get('study'), 'study'), content=public_theme(pack) if pack else None,
                          audio={kind: self._state(rows.get(kind), kind) for kind in AUDIO_FORMATS},
                          text_available=self.modes['study'][0], audio_available=self.modes['video'][0])

    def enqueue(self, owner: str, lesson_id: str, kind: str, request: ConsentRequest) -> ThemeState:
        available, model = self.modes[kind]
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            owned_lesson(db, owner, lesson_id)
            row = db.execute('SELECT * FROM theme_jobs WHERE lesson_id = ? AND kind = ?', (lesson_id, kind)).fetchone()
            now = time()
            can_prepare = row is None or row['status'] != 'ready'
            if can_prepare and not available:
                raise GenerationFailure('not_configured')
            if kind != 'study' and self._stored_pack(db, lesson_id) is None:
                raise HTTPException(409, 'Prepare os materiais do tema antes de gerar o áudio.')
            if row is None:
                db.execute("""
                    INSERT INTO theme_jobs (lesson_id, kind, model, version, status, created_at)
                    VALUES (?, ?, ?, ?, 'queued', ?)
                """, (lesson_id, kind, model, VERSION, now))
            elif can_prepare and request.retry_attempt == row['attempts'] and row['attempts'] < MAX_ATTEMPTS:
                dormant = row['status'] == 'queued' or (row['status'] == 'running' and (row['lease_until'] or 0) <= now)
                moved = dormant and (row['model'] != model or row['version'] != VERSION)
                retry = row['status'] in ('failed', 'needs_review') and (row['retry_after'] or 0) <= now
                if moved or retry:
                    db.execute("""
                        UPDATE theme_jobs SET status = 'queued', model = ?, version = ?, reason = NULL,
                            retry_after = NULL, claim_token = NULL, lease_until = NULL, created_at = ?
                        WHERE lesson_id = ? AND kind = ?
                    """, (model, VERSION, now, lesson_id, kind))
        return self.get(owner, lesson_id)

    def _claim(self) -> dict | None:
        text_enabled, text_model = self.modes['study']
        audio_enabled, audio_model = self.modes['video']
        if not (text_enabled or audio_enabled) or not self.database.is_file():
            return None
        with self.connection() as db:
            now = time()
            row = db.execute("""
                SELECT j.lesson_id, j.kind, j.model, j.version, j.attempts, h.owner_id
                FROM theme_jobs j JOIN lesson_versions l ON l.id = j.lesson_id
                JOIN courses c ON c.id = l.course_id JOIN assessment_history h ON h.id = c.plan_id
                WHERE j.version = ? AND h.result IS NOT NULL
                    AND ((j.kind = 'study' AND ? AND j.model = ?) OR (j.kind != 'study' AND ? AND j.model = ?))
                    AND (j.status = 'queued' OR (j.status = 'running' AND j.lease_until <= ?))
                ORDER BY j.created_at, j.lesson_id, j.kind LIMIT 1
            """, (VERSION, text_enabled, text_model, audio_enabled, audio_model, now)).fetchone()
            if row is None:
                return None
            db.execute('BEGIN IMMEDIATE')
            token = uuid4().hex
            state = 'failed' if row['attempts'] >= MAX_ATTEMPTS else 'running'
            changed = db.execute("""
                UPDATE theme_jobs SET status = ?, reason = ?, attempts = attempts + ?,
                    claim_token = ?, lease_until = ?
                WHERE lesson_id = ? AND kind = ? AND model = ? AND version = ? AND attempts = ?
                    AND (status = 'queued' OR (status = 'running' AND lease_until <= ?))
            """, (state, 'interrupted' if state == 'failed' else None, int(state == 'running'),
                  token if state == 'running' else None, now + self.timeout + 20 if state == 'running' else None,
                  row['lesson_id'], row['kind'], row['model'], row['version'], row['attempts'], now))
            return {**dict(row), 'claim_token': token} if changed.rowcount == 1 and state == 'running' else None

    @staticmethod
    def _identity(job: dict) -> tuple:
        return (job['lesson_id'], job['kind'], job['model'], job['version'])

    @staticmethod
    def _claim_id(job: dict) -> tuple:
        return (job['lesson_id'], job['kind'], job['claim_token'])

    def _source(self, job: dict) -> dict:
        with self.connection() as db:
            lesson = CourseLibrary.view_lesson(db, job['owner_id'], job['lesson_id'])
        return lesson.model_dump(include={'title', 'objective', 'explanation', 'example', 'summary'})

    def _audio_work(self, job: dict) -> tuple[list[list[tuple[str, str]]], set[int]]:
        with self.connection() as db:
            owned_lesson(db, job['owner_id'], job['lesson_id'])
            pack = self._stored_pack(db, job['lesson_id'])
            if pack is None:
                raise HTTPException(409, 'Materiais indisponíveis.')
            existing = {row['segment'] for row in db.execute("""
                SELECT segment FROM theme_audio WHERE lesson_id = ? AND kind = ? AND model = ? AND version = ?
            """, self._identity(job))}
        return _audio_script(pack, job['kind']), existing

    def _save_segment(self, job: dict, index: int, wav: bytes) -> bool:
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            updated = db.execute("""
                UPDATE theme_jobs SET lease_until = ?
                WHERE lesson_id = ? AND kind = ? AND claim_token = ? AND status = 'running'
            """, (time() + self.timeout + 20, *self._claim_id(job)))
            if updated.rowcount != 1:
                return False
            db.execute("""
                INSERT INTO theme_audio (lesson_id, kind, model, version, segment, wav) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (lesson_id, kind, model, version, segment) DO NOTHING
            """, (*self._identity(job), index, wav))
            return True

    def _finish(self, job: dict, status: str, reason: str | None, content: str | None, segments: int,
                provider_status: int | None, duration_ms: int) -> None:
        with self.connection() as db:
            db.execute("""
                UPDATE theme_jobs SET status = ?, reason = ?, content = ?, segments = ?, claim_token = NULL,
                    lease_until = NULL, retry_after = ?, provider_status = ?, duration_ms = ?
                WHERE lesson_id = ? AND kind = ? AND claim_token = ? AND status = 'running'
            """, (status, reason, content, segments, time() + 60 if reason == 'quota' else None,
                  provider_status, duration_ms, *self._claim_id(job)))

    def _interrupt(self, job: dict) -> None:
        with self.connection() as db:
            db.execute("""
                UPDATE theme_jobs SET status = 'queued', claim_token = NULL, lease_until = NULL
                WHERE lesson_id = ? AND kind = ? AND claim_token = ? AND status = 'running'
            """, self._claim_id(job))

    async def _process(self, job: dict) -> None:
        started = monotonic()
        reason = content = provider_status = None
        segments = 0
        try:
            if job['kind'] == 'study':
                source = await run_in_threadpool(self._source, job)
                self.reserve_request()
                async with asyncio.timeout(self.timeout):
                    pack = await self.generator.generate(THEME_PROMPT, source, ThemePack)
                content = validate_theme(pack).model_dump_json()
            else:
                script, existing = await run_in_threadpool(self._audio_work, job)
                for index, turns in enumerate(script):
                    if index in existing:
                        continue
                    self.reserve_request()
                    async with asyncio.timeout(self.timeout):
                        wav = await self.speech.synthesize(turns)
                    if not await run_in_threadpool(self._save_segment, job, index, wav):
                        return
                segments = len(script)
        except asyncio.CancelledError:
            await run_in_threadpool(self._interrupt, job)
            raise
        except GenerationFailure as failure:
            reason, provider_status = failure.reason, failure.provider_status
        except TimeoutError:
            reason = 'timeout'
        except (ValidationError, ValueError, TypeError):
            reason = 'invalid_response'
        except HTTPException:
            reason = 'interrupted'
        status = 'ready' if reason is None else 'needs_review' if reason == 'invalid_response' else 'failed'
        duration_ms = round((monotonic() - started) * 1000)
        await run_in_threadpool(self._finish, job, status, reason, content, segments, provider_status, duration_ms)

    async def run(self) -> None:
        while True:
            try:
                job = await run_in_threadpool(self._claim)
                if job:
                    await self._process(job)
                    continue
            except sqlite3.Error:
                logger.warning('theme_job_storage_failure')
            except Exception:
                logger.warning('theme_job_processing_failure')
            await asyncio.sleep(POLL_SECONDS)

    def play(self, owner: str, lesson_id: str, kind: AudioFormat, segment: int, requested_range: str | None) -> Response:
        with self.connection() as db:
            db.execute('BEGIN')
            owned_lesson(db, owner, lesson_id)
            audio = db.execute("""
                SELECT a.rowid, length(a.wav) AS bytes FROM theme_audio a JOIN theme_jobs j
                    ON j.lesson_id = a.lesson_id AND j.kind = a.kind AND j.model = a.model AND j.version = a.version
                WHERE a.lesson_id = ? AND a.kind = ? AND a.segment = ? AND j.status = 'ready'
            """, (lesson_id, kind, segment)).fetchone()
            if audio is None:
                raise HTTPException(404, 'Áudio não encontrado.')
            size = audio['bytes']
            start, end = _range(requested_range, size) if requested_range else (0, size - 1)
            headers = {'Accept-Ranges': 'bytes'}
            if requested_range:
                headers['Content-Range'] = f'bytes {start}-{end}/{size}'
            with db.blobopen('theme_audio', 'wav', audio['rowid'], readonly=True) as blob:
                blob.seek(start)
                raw = blob.read(end - start + 1)
        return Response(raw, status_code=206 if requested_range else 200, media_type='audio/wav', headers=headers)

    def grade(self, owner: str, lesson_id: str, kind: AssessmentFormat, request: GradeRequest) -> dict:
        with self.connection() as db:
            db.execute('BEGIN')
            owned_lesson(db, owner, lesson_id)
            pack = self._stored_pack(db, lesson_id)
        if pack is None:
            raise HTTPException(409, 'Os materiais deste tema ainda não estão prontos.')
        return grade_theme(pack, kind, request)

    def install_routes(self, app: FastAPI, require_account) -> None:
        base = '/api/lessons/{lesson_id}/materials'

        @app.get(base, response_model=ThemeState)
        def read(lesson_id: str, owner: str = Depends(require_account)):
            return self.get(owner, lesson_id)

        @app.post(base, response_model=ThemeState, status_code=202)
        def prepare(lesson_id: str, request: ConsentRequest, owner: str = Depends(require_account)):
            return self.enqueue(owner, lesson_id, 'study', request)

        @app.post(base + '/audio/{kind}', response_model=ThemeState, status_code=202)
        def prepare_audio(lesson_id: str, kind: AudioFormat, request: ConsentRequest, owner: str = Depends(require_account)):
            return self.enqueue(owner, lesson_id, kind, request)

        @app.get(base + '/audio/{kind}/{segment}')
        def play(lesson_id: str, kind: AudioFormat, segment: int = PathParameter(ge=0, le=7),
                 range_header: str | None = Header(None, alias='Range'), owner: str = Depends(require_account)):
            return self.play(owner, lesson_id, kind, segment, range_header)

        @app.post(base + '/{kind}/grade')
        def grade(lesson_id: str, kind: AssessmentFormat, request: GradeRequest, owner: str = Depends(require_account)):
            return self.grade(owner, lesson_id, kind, request)
