"""Private content reports and the administrative quality dashboard."""
from dataclasses import dataclass
from datetime import datetime, timezone
from time import time
import sqlite3
from typing import Literal, get_args

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import Field

from .catalog import CAREER_LABELS
from .practice import owned_lesson
from .schemas import Model


ReportCategory = Literal['accuracy', 'answer_key', 'clarity', 'accessibility', 'inappropriate']
REPORT_CATEGORIES = get_args(ReportCategory)
PRIVACY_MINIMUM = 5
JOB_STATES = ('queued', 'running', 'ready', 'failed', 'needs_review')
FAILURE_REASONS = ('quota', 'provider_503', 'unavailable', 'timeout', 'invalid_response', 'other')

# These are the latest states of persisted jobs. A retry replaces a job's state.
JOBS = """
    WITH jobs AS (
        SELECT j.created_at, j.model, j.prompt_version, j.status, j.reason,
               j.provider_status, j.duration_ms, j.input_tokens, j.output_tokens, h.owner_id, h.profession
        FROM generation_jobs j
        JOIN assessment_history h ON h.id = j.plan_id
        WHERE h.result IS NOT NULL AND j.created_at >= ?
        UNION ALL
        SELECT j.created_at, j.model, j.version, j.status, j.reason,
               j.provider_status, j.duration_ms, NULL, NULL, h.owner_id, h.profession
        FROM theme_jobs j
        JOIN lesson_versions l ON l.id = j.lesson_id
        JOIN courses c ON c.id = l.course_id
        JOIN assessment_history h ON h.id = c.plan_id
        WHERE h.result IS NOT NULL AND j.created_at >= ?
    )
"""
SELECTED_JOBS = JOBS + """
    , selected AS (
        SELECT * FROM jobs
        WHERE (? IS NULL OR model = ?)
          AND (? IS NULL OR prompt_version = ?)
          AND (? IS NULL OR profession = ?)
    )
"""


class ContentReportRequest(Model):
    lesson_id: str = Field(pattern=r'^[0-9a-f]{32}$')
    category: ReportCategory


@dataclass(frozen=True)
class QualityFilters:
    window_days: int
    model: str | None
    prompt_version: int | None
    career: str | None


def migrate_quality(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 8').fetchone():
        return
    db.execute("""
        CREATE TABLE content_reports (
            lesson_id TEXT NOT NULL REFERENCES lesson_versions(id) ON DELETE CASCADE,
            owner_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            category TEXT NOT NULL CHECK (category IN ('accuracy', 'answer_key', 'clarity', 'accessibility', 'inappropriate')),
            created_at TEXT NOT NULL,
            PRIMARY KEY (lesson_id, owner_id, category)
        )
    """)
    db.execute('CREATE INDEX content_reports_period ON content_reports (created_at, category)')
    db.execute('INSERT INTO learning_migrations (version) VALUES (8)')


def migrate_job_telemetry(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 9').fetchone():
        return
    db.execute('ALTER TABLE generation_jobs ADD COLUMN provider_status INTEGER')
    db.execute('ALTER TABLE theme_jobs ADD COLUMN provider_status INTEGER')
    db.execute('ALTER TABLE theme_jobs ADD COLUMN duration_ms INTEGER')
    db.execute('INSERT INTO learning_migrations (version) VALUES (9)')


def _generation(db: sqlite3.Connection, since: float, filters: QualityFilters) -> dict:
    model, version, career = filters.model, filters.prompt_version, filters.career
    params = (since, since, model, model, version, version, career, career)
    states = db.execute(SELECTED_JOBS + """
        SELECT status, COUNT(*) AS amount, COUNT(DISTINCT owner_id) AS people,
               SUM(duration_ms) AS duration_ms, COUNT(duration_ms) AS timings,
               SUM(input_tokens) AS input_tokens, COUNT(input_tokens) AS input_samples,
               SUM(output_tokens) AS output_tokens, COUNT(output_tokens) AS output_samples
        FROM selected GROUP BY status
    """, params).fetchall()
    reasons = db.execute(SELECTED_JOBS + """
        SELECT CASE WHEN provider_status = 503 THEN 'provider_503'
                    WHEN reason IN ('quota', 'unavailable', 'timeout', 'invalid_response') THEN reason
                    ELSE 'other' END AS category,
               COUNT(*) AS amount, COUNT(DISTINCT owner_id) AS people
        FROM selected WHERE status IN ('failed', 'needs_review')
        GROUP BY category
    """, params).fetchall()
    # Suppress the entire career breakdown if any observed cell is too small.
    # Otherwise totals could reveal a hidden category by subtraction.
    restricted = career is not None and any(row['people'] < PRIVACY_MINIMUM for row in (*states, *reasons))
    if restricted:
        return {
            'restricted': True, 'total': None, 'by_status': None, 'failures': None, 'rejection_rate': None,
            'latency_ms': None, 'input_tokens': None, 'output_tokens': None, 'cost_usd': None,
        }
    by_status = dict.fromkeys(JOB_STATES, 0)
    by_status.update((row['status'], row['amount']) for row in states)
    failures = dict.fromkeys(FAILURE_REASONS, 0)
    failures.update((row['category'], row['amount']) for row in reasons)
    terminal = by_status['ready'] + by_status['failed'] + by_status['needs_review']
    measured = sum(row['timings'] for row in states)
    duration = sum(row['duration_ms'] or 0 for row in states)
    input_samples = sum(row['input_samples'] for row in states)
    output_samples = sum(row['output_samples'] for row in states)
    return {
        'restricted': False,
        'total': sum(by_status.values()),
        'by_status': by_status,
        'failures': failures,
        'rejection_rate': round(by_status['needs_review'] / terminal, 4) if terminal else None,
        'latency_ms': {'average': round(duration / measured, 1), 'samples': measured} if measured else None,
        'input_tokens': {'total': sum(row['input_tokens'] or 0 for row in states),
                         'samples': input_samples} if input_samples else None,
        'output_tokens': {'total': sum(row['output_tokens'] or 0 for row in states),
                          'samples': output_samples} if output_samples else None,
        'cost_usd': None,
    }


def _reports(db: sqlite3.Connection, since: str, career: str | None) -> dict:
    rows = db.execute("""
        SELECT r.category, COUNT(*) AS amount, COUNT(DISTINCT r.owner_id) AS people
        FROM content_reports r
        JOIN lesson_versions l ON l.id = r.lesson_id
        JOIN courses c ON c.id = l.course_id
        JOIN assessment_history h ON h.id = c.plan_id
        WHERE r.created_at >= ? AND h.result IS NOT NULL AND (? IS NULL OR h.profession = ?)
        GROUP BY r.category
    """, (since, career, career)).fetchall()
    observed = {row['category']: row for row in rows}
    # Categories without evidence also stay hidden, so the public shape is fixed.
    return {
        category: observed[category]['amount'] if category in observed and observed[category]['people'] >= PRIVACY_MINIMUM
        else None
        for category in REPORT_CATEGORIES
    }


def _progress(db: sqlite3.Connection, since: str, career: str | None) -> dict:
    row = db.execute("""
        WITH lessons AS (
            SELECT p.owner_id
            FROM practice_attempts p
            JOIN lesson_versions l ON l.id = p.lesson_id
            JOIN courses c ON c.id = l.course_id
            JOIN assessment_history h ON h.id = c.plan_id
            WHERE p.correct = 1 AND h.result IS NOT NULL AND (? IS NULL OR h.profession = ?)
            GROUP BY p.lesson_id, p.owner_id
            HAVING MIN(p.created_at) >= ?
        ), mastery AS (
            SELECT m.owner_id
            FROM module_mastery m
            JOIN courses c ON c.id = m.course_id
            JOIN assessment_history h ON h.id = c.plan_id
            WHERE m.granted_at >= ? AND h.result IS NOT NULL AND (? IS NULL OR h.profession = ?)
        )
        SELECT (SELECT COUNT(*) FROM lessons) AS lessons,
               (SELECT COUNT(*) FROM mastery) AS modules,
               (SELECT COUNT(DISTINCT owner_id) FROM lessons) AS lesson_people,
               (SELECT COUNT(DISTINCT owner_id) FROM mastery) AS mastery_people,
               (SELECT COUNT(*) FROM (SELECT owner_id FROM lessons UNION SELECT owner_id FROM mastery)) AS people
    """, (career, career, since, since, career, career)).fetchone()
    return {
        'learners': row['people'] if row['people'] >= PRIVACY_MINIMUM else None,
        'lessons_completed': row['lessons'] if row['lesson_people'] >= PRIVACY_MINIMUM else None,
        'modules_mastered': row['modules'] if row['mastery_people'] >= PRIVACY_MINIMUM else None,
    }


class QualityStore:
    def __init__(self, connection, admin_emails: list[str]):
        self.connection = connection
        self.admin_emails = frozenset(email.strip().lower() for email in admin_emails if email.strip())

    def _allowed(self, db: sqlite3.Connection, owner_id: str) -> bool:
        if not self.admin_emails:
            return False
        # accounts.email is set by successful OTP or verified Google login. Profile edits cannot set it.
        row = db.execute('SELECT email FROM accounts WHERE id = ?', (owner_id,)).fetchone()
        return row is not None and row['email'] in self.admin_emails

    def access(self, owner_id: str) -> dict:
        with self.connection() as db:
            return {'allowed': self._allowed(db, owner_id)}

    def snapshot(self, owner_id: str, filters: QualityFilters) -> dict:
        since = time() - filters.window_days * 86400
        since_iso = datetime.fromtimestamp(since, tz=timezone.utc).isoformat()
        with self.connection() as db:
            db.execute('BEGIN')
            if not self._allowed(db, owner_id):
                raise HTTPException(403, 'O painel de qualidade requer acesso administrativo.')
            if filters.career is not None and filters.career not in CAREER_LABELS:
                raise HTTPException(422, 'Escolha uma carreira do catálogo.')
            options = db.execute(JOBS + 'SELECT DISTINCT model, prompt_version FROM jobs ORDER BY model, prompt_version',
                                 (since, since)).fetchall()
            return {
                'window_days': filters.window_days,
                'generation': _generation(db, since, filters),
                'reports': _reports(db, since_iso, filters.career),
                'progress': _progress(db, since_iso, filters.career),
                'models': sorted({row['model'] for row in options}),
                'prompt_versions': sorted({row['prompt_version'] for row in options}),
                'careers': sorted(CAREER_LABELS, key=str.casefold),
                'privacy_minimum': PRIVACY_MINIMUM,
            }

    def report(self, owner_id: str, data: ContentReportRequest) -> None:
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            owned_lesson(db, owner_id, data.lesson_id)
            db.execute("""
                INSERT INTO content_reports (lesson_id, owner_id, category, created_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(lesson_id, owner_id, category) DO NOTHING
            """, (data.lesson_id, owner_id, data.category, datetime.now(timezone.utc).isoformat()))

    def install_routes(self, app: FastAPI, require_account) -> None:
        @app.get('/api/admin/access')
        def admin_access(owner_id: str = Depends(require_account)):
            return self.access(owner_id)

        @app.get('/api/admin/quality')
        def quality_snapshot(
            window_days: int = Query(30, ge=1, le=90),
            model: str | None = Query(None, min_length=1, max_length=120, pattern=r'^[a-zA-Z0-9._/-]+$'),
            prompt_version: int | None = Query(None, ge=1, le=65_535),
            career: str | None = Query(None, min_length=1, max_length=120),
            owner_id: str = Depends(require_account),
        ):
            return self.snapshot(owner_id, QualityFilters(window_days, model, prompt_version, career))

        @app.post('/api/content-reports', status_code=204)
        def report_content(data: ContentReportRequest, owner_id: str = Depends(require_account)):
            self.report(owner_id, data)
            return Response(status_code=204)
