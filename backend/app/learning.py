"""Private study plans and append-only course revisions."""

from datetime import datetime, timezone
import json
import sqlite3
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from .schemas import AssessmentV3


class StudyPlanDetail(BaseModel):
    id: str
    revision: int
    created_at: str
    assessment: AssessmentV3


class CourseContent(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=120)
    blueprint: dict[str, JsonValue] = Field(min_length=1)


class CourseDetail(BaseModel):
    id: str
    plan_id: str
    plan_revision: int
    revision: int
    created_at: str
    published: bool
    content: CourseContent


def save_initial_plan(db: sqlite3.Connection, assessment: AssessmentV3, created_at: str) -> None:
    plan_id = assessment.source_assessment_id
    db.execute('INSERT INTO study_plans (id) VALUES (?)', (plan_id,))
    db.execute(
        'INSERT INTO study_plan_versions (plan_id, revision, created_at, assessment) VALUES (?, 1, ?, ?)',
        (plan_id, created_at, assessment.model_dump_json(exclude={'weeks'})),
    )
    db.executemany(
        'INSERT INTO study_weeks (plan_id, plan_revision, ordinal, payload) VALUES (?, 1, ?, ?)',
        ((plan_id, week.week, week.model_dump_json()) for week in assessment.weeks),
    )


def migrate_learning(db: sqlite3.Connection) -> None:
    db.execute('CREATE TABLE IF NOT EXISTS learning_migrations (version INTEGER PRIMARY KEY)')
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 1').fetchone():
        return
    db.execute("""
        CREATE TABLE IF NOT EXISTS study_plans (
            id TEXT PRIMARY KEY REFERENCES assessment_history(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS study_plan_versions (
            plan_id TEXT NOT NULL REFERENCES study_plans(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            created_at TEXT NOT NULL,
            assessment TEXT NOT NULL,
            PRIMARY KEY (plan_id, revision)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS study_weeks (
            plan_id TEXT NOT NULL,
            plan_revision INTEGER NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 12),
            payload TEXT NOT NULL,
            PRIMARY KEY (plan_id, plan_revision, ordinal),
            FOREIGN KEY (plan_id, plan_revision) REFERENCES study_plan_versions(plan_id, revision) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            plan_revision INTEGER NOT NULL,
            UNIQUE (plan_id, plan_revision),
            FOREIGN KEY (plan_id, plan_revision) REFERENCES study_plan_versions(plan_id, revision) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS course_versions (
            course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            published INTEGER NOT NULL CHECK (published IN (0, 1)),
            created_at TEXT NOT NULL,
            content TEXT NOT NULL,
            PRIMARY KEY (course_id, revision)
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS course_versions_published
        ON course_versions (course_id, revision DESC) WHERE published = 1
    """)
    rows = db.execute("""
        SELECT id, created_at, result FROM assessment_history
        WHERE CASE WHEN json_valid(result) THEN json_extract(result, '$.plan_version') END = 3
    """)
    for row in rows:
        try:
            assessment = AssessmentV3.model_validate_json(row['result'])
        except ValidationError:
            continue
        if assessment.source_assessment_id == row['id'] and row['created_at'] is not None:
            save_initial_plan(db, assessment, row['created_at'])
    db.execute('INSERT INTO learning_migrations (version) VALUES (1)')


class LearningStore:
    def __init__(self, connection):
        self.connection = connection

    @staticmethod
    def _find_owned_plan(db: sqlite3.Connection, owner_id: str, plan_id: str, revision: int | None) -> sqlite3.Row:
        row = db.execute("""
            SELECT h.result, h.created_at AS source_created_at,
                   v.revision, v.created_at, v.assessment
            FROM assessment_history h
            LEFT JOIN study_plan_versions v ON v.plan_id = h.id AND (? IS NULL OR v.revision = ?)
            WHERE h.id = ? AND h.owner_id = ? AND h.result IS NOT NULL
            ORDER BY v.revision DESC LIMIT 1
        """, (revision, revision, plan_id, owner_id)).fetchone()
        if row is None:
            raise HTTPException(404, 'Plano de estudos não encontrado.')
        return row

    @staticmethod
    def _parse_source(plan_id: str, row: sqlite3.Row) -> AssessmentV3:
        try:
            assessment = AssessmentV3.model_validate_json(row['result'])
            if assessment.source_assessment_id == plan_id and row['source_created_at'] is not None:
                return assessment
        except ValidationError:
            pass
        raise HTTPException(404, 'Plano de estudos não encontrado.')

    def get_plan(self, owner_id: str, plan_id: str, revision: int | None = None) -> StudyPlanDetail:
        with self.connection() as db:
            db.execute('BEGIN')
            version = self._find_owned_plan(db, owner_id, plan_id, revision)
            if version['revision'] is None:
                if revision not in (None, 1):
                    raise HTTPException(404, 'Plano de estudos não encontrado.')
                self._parse_source(plan_id, version)
                # An older writer can commit a V3 result after the initial migration.
                # Recheck ownership and version under the write lock before materializing it.
                db.rollback()
                db.execute('BEGIN IMMEDIATE')
                version = self._find_owned_plan(db, owner_id, plan_id, revision)
                if version['revision'] is None:
                    assessment = self._parse_source(plan_id, version)
                    created_at = version['source_created_at']
                    save_initial_plan(db, assessment, created_at)
                    return StudyPlanDetail(id=plan_id, revision=1, created_at=created_at, assessment=assessment)
            weeks = db.execute("""
                SELECT payload FROM study_weeks WHERE plan_id = ? AND plan_revision = ? ORDER BY ordinal
            """, (plan_id, version['revision'])).fetchall()
        try:
            assessment = AssessmentV3.model_validate({
                **json.loads(version['assessment']),
                'weeks': [json.loads(week['payload']) for week in weeks],
            })
            if assessment.source_assessment_id != plan_id:
                raise ValueError('O plano não pertence a esta avaliação.')
            return StudyPlanDetail(id=plan_id, revision=version['revision'],
                                   created_at=version['created_at'], assessment=assessment)
        except (ValidationError, ValueError, TypeError):
            raise HTTPException(500, 'Não foi possível abrir este plano salvo.') from None

    def save_course_version(
        self, owner_id: str, plan_id: str, plan_revision: int, content: CourseContent, *, published: bool = False,
    ) -> CourseDetail:
        """Persist an already validated draft or an approved snapshot from the backend."""
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            return self.write_course_version(db, owner_id, plan_id, plan_revision, content, published=published)

    @staticmethod
    def write_course_version(
        db: sqlite3.Connection, owner_id: str, plan_id: str, plan_revision: int,
        content: CourseContent, *, published: bool = False,
    ) -> CourseDetail:
        serialized = json.dumps(content.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, allow_nan=False)
        if len(serialized.encode('utf-8')) > 65536:
            raise ValueError('O conteúdo do curso excede o limite de armazenamento.')
        plan = db.execute("""
            SELECT 1 FROM study_plan_versions v JOIN assessment_history h ON h.id = v.plan_id
            WHERE v.plan_id = ? AND v.revision = ? AND h.owner_id = ? AND h.result IS NOT NULL
        """, (plan_id, plan_revision, owner_id)).fetchone()
        if plan is None:
            raise HTTPException(404, 'Plano de estudos não encontrado.')
        course = db.execute('SELECT id FROM courses WHERE plan_id = ? AND plan_revision = ?',
                            (plan_id, plan_revision)).fetchone()
        if course is None:
            course_id = uuid4().hex
            db.execute('INSERT INTO courses (id, plan_id, plan_revision) VALUES (?, ?, ?)',
                       (course_id, plan_id, plan_revision))
        else:
            course_id = course['id']
        latest = db.execute("""
            SELECT revision, published, created_at, content FROM course_versions
            WHERE course_id = ? ORDER BY revision DESC LIMIT 1
        """, (course_id,)).fetchone()
        if latest and latest['content'] == serialized and latest['published'] == published:
            return CourseDetail(id=course_id, plan_id=plan_id, plan_revision=plan_revision,
                                revision=latest['revision'], created_at=latest['created_at'],
                                published=published, content=content)
        revision = latest['revision'] + 1 if latest else 1
        created_at = datetime.now(timezone.utc).isoformat()
        db.execute("""
            INSERT INTO course_versions (course_id, revision, published, created_at, content)
            VALUES (?, ?, ?, ?, ?)
        """, (course_id, revision, published, created_at, serialized))
        return CourseDetail(id=course_id, plan_id=plan_id, plan_revision=plan_revision,
                            revision=revision, created_at=created_at, published=published, content=content)

    def get_course(self, owner_id: str, course_id: str) -> CourseDetail:
        with self.connection() as db:
            version = db.execute("""
                SELECT c.plan_id, c.plan_revision, v.revision, v.created_at, v.content
                FROM courses c JOIN course_versions v ON v.course_id = c.id
                JOIN assessment_history h ON h.id = c.plan_id
                WHERE c.id = ? AND h.owner_id = ? AND h.result IS NOT NULL AND v.published = 1
                ORDER BY v.revision DESC LIMIT 1
            """, (course_id, owner_id)).fetchone()
        if version is None:
            raise HTTPException(404, 'Curso não encontrado.')
        try:
            return CourseDetail(
                id=course_id, plan_id=version['plan_id'], plan_revision=version['plan_revision'],
                revision=version['revision'], created_at=version['created_at'],
                published=True, content=CourseContent.model_validate_json(version['content']),
            )
        except ValidationError:
            raise HTTPException(500, 'Não foi possível abrir este curso salvo.') from None

    def install_routes(self, app: FastAPI, require_account) -> None:
        @app.get('/api/study-plans/{plan_id}', response_model=StudyPlanDetail)
        def get_study_plan(plan_id: str, owner_id: str = Depends(require_account)):
            return self.get_plan(owner_id, plan_id)

        @app.get('/api/courses/{course_id}', response_model=CourseDetail)
        def get_course(course_id: str, owner_id: str = Depends(require_account)):
            return self.get_course(owner_id, course_id)
