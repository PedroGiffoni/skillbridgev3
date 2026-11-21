"""Private assessment history and short reservations for concurrent submissions."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from threading import Lock
from time import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, TypeAdapter, ValidationError

from .blueprint_jobs import migrate_jobs
from .learning import migrate_learning, save_initial_plan
from .learning_dashboard import migrate_dashboard
from .library import migrate_library
from .mastery import migrate_mastery
from .practice import migrate_practice
from .quality import migrate_job_telemetry, migrate_quality
from .schemas import AssessmentResult, AssessmentV3
from .theme_materials import migrate_themes


assessment_reader = TypeAdapter(AssessmentResult)


def read_assessment(raw: str, entry_id: str) -> AssessmentResult:
    try:
        result = assessment_reader.validate_json(raw)
    except ValidationError:
        raise HTTPException(500, 'Não foi possível abrir esta avaliação salva.') from None
    if isinstance(result, AssessmentV3) and result.source_assessment_id != entry_id:
        raise HTTPException(500, 'Não foi possível abrir esta avaliação salva.')
    return result


class HistoryItem(BaseModel):
    id: str
    profession: str
    created_at: str


class HistoryPage(BaseModel):
    items: list[HistoryItem]


class HistoryDetail(HistoryItem):
    assessment: AssessmentResult


class AssessmentHistory:
    def __init__(self, path: Path):
        self.path = path
        self._schema_lock = Lock()
        self._initialized = False

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        database = sqlite3.connect(self.path, timeout=5)
        database.row_factory = sqlite3.Row
        try:
            with database:
                database.execute('PRAGMA foreign_keys = ON')
                with self._schema_lock:
                    if not self._initialized:
                        database.execute('BEGIN IMMEDIATE')
                        self._create_schema(database)
                        migrate_learning(database)
                        migrate_jobs(database)
                        migrate_library(database)
                        migrate_practice(database)
                        migrate_themes(database)
                        migrate_mastery(database)
                        migrate_dashboard(database)
                        migrate_quality(database)
                        migrate_job_telemetry(database)
                        database.commit()
                        self._initialized = True
                yield database
        finally:
            database.close()

    @staticmethod
    def _create_schema(database: sqlite3.Connection) -> None:
        database.execute("""
            CREATE TABLE IF NOT EXISTS assessment_history (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                fingerprint TEXT NOT NULL,
                profession TEXT NOT NULL,
                started_at REAL NOT NULL,
                created_at TEXT,
                result TEXT,
                UNIQUE (owner_id, fingerprint)
            )
        """)
        database.execute("""
            CREATE INDEX IF NOT EXISTS assessment_history_owner_date
            ON assessment_history (owner_id, created_at DESC) WHERE result IS NOT NULL
        """)
        database.execute("""
            CREATE INDEX IF NOT EXISTS assessment_history_pending
            ON assessment_history (started_at) WHERE result IS NULL
        """)

    def reserve(self, owner_id: str, fingerprint: str, profession: str) -> tuple[str, AssessmentResult | None]:
        now = time()
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            existing = database.execute(
                'SELECT id, result, started_at FROM assessment_history WHERE owner_id = ? AND fingerprint = ?',
                (owner_id, fingerprint),
            ).fetchone()
            if existing is not None:
                if existing['result'] is not None:
                    return existing['id'], read_assessment(existing['result'], existing['id'])
                if now - existing['started_at'] < 180:
                    raise HTTPException(409, 'Este diagnóstico está sendo preparado. Aguarde um momento e tente novamente.')
            # Stale reservations can survive a process stop during generation.
            database.execute('DELETE FROM assessment_history WHERE result IS NULL AND started_at <= ?', (now - 180,))
            entry_id = uuid4().hex
            database.execute(
                'INSERT INTO assessment_history (id, owner_id, fingerprint, profession, started_at) VALUES (?, ?, ?, ?, ?)',
                (entry_id, owner_id, fingerprint, profession, now),
            )
            return entry_id, None

    def save(self, owner_id: str, entry_id: str, result: AssessmentResult) -> None:
        with self.connection() as database:
            created_at = datetime.now(timezone.utc).isoformat()
            saved = database.execute(
                'UPDATE assessment_history SET created_at = ?, result = ? WHERE id = ? AND owner_id = ? AND result IS NULL',
                (created_at, result.model_dump_json(), entry_id, owner_id),
            )
            if saved.rowcount != 1:
                raise HTTPException(409, 'Não foi possível salvar este diagnóstico. Tente novamente.')
            if isinstance(result, AssessmentV3):
                if result.source_assessment_id != entry_id:
                    raise HTTPException(500, 'Não foi possível salvar o plano deste diagnóstico.')
                save_initial_plan(database, result, created_at)

    def release(self, owner_id: str, entry_id: str) -> None:
        with self.connection() as database:
            database.execute(
                'DELETE FROM assessment_history WHERE id = ? AND owner_id = ? AND result IS NULL',
                (entry_id, owner_id),
            )

    def install_routes(self, app: FastAPI, require_account) -> None:
        @app.get('/api/history', response_model=HistoryPage)
        def history(owner_id: str = Depends(require_account)):
            with self.connection() as database:
                rows = database.execute(
                    """SELECT id, profession, created_at FROM assessment_history
                       WHERE owner_id = ? AND result IS NOT NULL ORDER BY created_at DESC, id DESC""",
                    (owner_id,),
                ).fetchall()
            return HistoryPage(items=[HistoryItem(**dict(row)) for row in rows])

        @app.get('/api/history/{entry_id}', response_model=HistoryDetail)
        def history_detail(entry_id: str, owner_id: str = Depends(require_account)):
            with self.connection() as database:
                row = database.execute(
                    """SELECT id, profession, created_at, result FROM assessment_history
                       WHERE id = ? AND owner_id = ? AND result IS NOT NULL""",
                    (entry_id, owner_id),
                ).fetchone()
            if row is None:
                raise HTTPException(404, 'Avaliação não encontrada.')
            return HistoryDetail(id=row['id'], profession=row['profession'], created_at=row['created_at'],
                                 assessment=read_assessment(row['result'], row['id']))

        @app.delete('/api/history/{entry_id}', status_code=204)
        def delete_history(entry_id: str, owner_id: str = Depends(require_account)):
            with self.connection() as database:
                removed = database.execute(
                    'DELETE FROM assessment_history WHERE id = ? AND owner_id = ? AND result IS NOT NULL',
                    (entry_id, owner_id),
                )
                if removed.rowcount != 1:
                    raise HTTPException(404, 'Avaliação não encontrada.')
            return Response(status_code=204)
