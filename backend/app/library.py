"""Owner-scoped immutable published course and lesson revisions."""
from datetime import datetime, timezone
from typing import Literal
import sqlite3

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

from .blueprint import CourseBlueprint, LessonOutline
from .learning import CourseContent, CourseDetail, LearningStore
from .lesson_content import LESSON_SCHEMAS, SCHEMA_VERSION, LessonPublication, practice_preview
from .module_access import assert_module_open, mastered_modules, missing_prerequisites, read_outline
from .practice import PracticeProgress, owned_lesson, practice_progress
from .schemas import Model


MAX_REVISION = (1 << 63) - 1


class PublishRequest(Model):
    draft_revision: int = Field(strict=True, ge=1, le=MAX_REVISION)


class LibraryItem(BaseModel):
    id: str
    title: str
    revision: int
    plan_id: str
    created_at: str


class LibraryPage(BaseModel):
    items: list[LibraryItem]
    next_offset: int | None


class LibraryModule(BaseModel):
    id: str
    title: str
    status: Literal['locked', 'open', 'mastered']
    blocked_by: list[str]


class LessonSlot(BaseModel):
    outline_id: str
    module_id: str
    module_title: str
    locked: bool
    title: str
    objective: str
    week: int
    job_id: str | None
    lesson_id: str | None
    practice_completed: bool


class LessonSlots(BaseModel):
    modules: list[LibraryModule]
    items: list[LessonSlot]


class LessonRead(BaseModel):
    id: str
    course_id: str
    course_revision: int
    revision: int
    schema_version: int
    outline_id: str
    title: str
    objective: str
    week: int
    competency_ids: list[str]
    format: str
    explanation: str
    example: str
    summary: str
    exercise: dict
    practice: PracticeProgress


def migrate_library(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 3').fetchone():
        return
    db.execute('ALTER TABLE generation_jobs ADD COLUMN lesson_outline_id TEXT')
    db.execute("""
        CREATE UNIQUE INDEX generation_jobs_lesson ON generation_jobs (course_id, course_revision, lesson_outline_id)
        WHERE lesson_outline_id IS NOT NULL
    """)
    db.execute("""
        CREATE TABLE course_publications (
            course_id TEXT NOT NULL,
            draft_revision INTEGER NOT NULL,
            published_revision INTEGER NOT NULL,
            PRIMARY KEY (course_id, draft_revision),
            FOREIGN KEY (course_id, draft_revision) REFERENCES course_versions(course_id, revision) ON DELETE CASCADE,
            FOREIGN KEY (course_id, published_revision) REFERENCES course_versions(course_id, revision) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE lesson_versions (
            id TEXT PRIMARY KEY REFERENCES generation_jobs(id) ON DELETE CASCADE,
            course_id TEXT NOT NULL,
            course_revision INTEGER NOT NULL,
            outline_id TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            schema_version INTEGER NOT NULL,
            format TEXT NOT NULL,
            outline TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (course_id, course_revision, outline_id, revision),
            FOREIGN KEY (course_id, course_revision) REFERENCES course_versions(course_id, revision) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TRIGGER freeze_published_course BEFORE UPDATE ON course_versions
        WHEN OLD.published = 1 BEGIN SELECT RAISE(ABORT, 'Published course revision is immutable'); END
    """)
    db.execute("""
        CREATE TRIGGER freeze_published_lesson BEFORE UPDATE ON lesson_versions
        BEGIN SELECT RAISE(ABORT, 'Published lesson revision is immutable'); END
    """)
    db.execute('INSERT INTO learning_migrations (version) VALUES (3)')


def course_detail(row: sqlite3.Row) -> CourseDetail:
    try:
        return CourseDetail(id=row['id'], plan_id=row['plan_id'], plan_revision=row['plan_revision'],
                            revision=row['revision'], created_at=row['created_at'], published=bool(row['published']),
                            content=CourseContent.model_validate_json(row['content']))
    except ValidationError:
        raise HTTPException(500, 'Não foi possível abrir este curso salvo.') from None


def outline_of(course: CourseDetail) -> CourseBlueprint:
    return read_outline(course.content)


class CourseLibrary:
    def __init__(self, learning: LearningStore):
        self.learning = learning
        self.connection = learning.connection

    @staticmethod
    def _version(db: sqlite3.Connection, owner: str, course: str, revision: int, *, published: bool) -> CourseDetail:
        row = db.execute("""
            SELECT c.id, c.plan_id, c.plan_revision, v.revision, v.content, v.published, v.created_at
            FROM courses c JOIN course_versions v ON v.course_id = c.id
            JOIN assessment_history h ON h.id = c.plan_id
            WHERE c.id = ? AND v.revision = ? AND v.published = ? AND h.owner_id = ? AND h.result IS NOT NULL
        """, (course, revision, published, owner)).fetchone()
        if row is None:
            raise HTTPException(404, 'Curso não encontrado.')
        return course_detail(row)

    def publish(self, owner: str, course_id: str, draft_revision: int) -> CourseDetail:
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            draft = self._version(db, owner, course_id, draft_revision, published=False)
            validated = db.execute("""
                SELECT 1 FROM generation_jobs WHERE course_id = ? AND course_revision = ?
                    AND status = 'ready' AND lesson_outline_id IS NULL
            """, (course_id, draft_revision)).fetchone()
            if validated is None:
                raise HTTPException(404, 'Rascunho validado não encontrado.')
            existing = db.execute("""
                SELECT published_revision FROM course_publications WHERE course_id = ? AND draft_revision = ?
            """, (course_id, draft_revision)).fetchone()
            if existing:
                return self._version(db, owner, course_id, existing['published_revision'], published=True)
            outline_of(draft)
            published = self.learning.write_course_version(
                db, owner, draft.plan_id, draft.plan_revision, draft.content, published=True,
            )
            db.execute('INSERT INTO course_publications VALUES (?, ?, ?)',
                       (course_id, draft_revision, published.revision))
            return published

    def owned_outline(self, db: sqlite3.Connection, owner: str, course_id: str, revision: int,
                      outline_id: str) -> tuple[CourseDetail, LessonOutline]:
        course = self._version(db, owner, course_id, revision, published=True)
        for module in outline_of(course).modules:
            for lesson in module.lessons:
                if lesson.id == outline_id:
                    assert_module_open(db, owner, course_id, revision, module)
                    return course, lesson
        raise HTTPException(404, 'Lição não encontrada.')

    def get_source(self, owner: str, course_id: str, revision: int, outline_id: str):
        with self.connection() as db:
            return self.owned_outline(db, owner, course_id, revision, outline_id)

    def get_slots(self, owner: str, course_id: str, revision: int) -> LessonSlots:
        with self.connection() as db:
            db.execute('BEGIN')
            course = self._version(db, owner, course_id, revision, published=True)
            items = db.execute("""
                SELECT j.lesson_outline_id, j.id, v.id AS lesson_id,
                    EXISTS(SELECT 1 FROM practice_attempts p
                           WHERE p.lesson_id = v.id AND p.owner_id = ? AND p.correct = 1) AS practice_completed
                FROM generation_jobs j LEFT JOIN lesson_versions v ON v.id = j.id
                WHERE j.course_id = ? AND j.course_revision = ? AND j.lesson_outline_id IS NOT NULL
            """, (owner, course_id, revision)).fetchall()
            states = {row['lesson_outline_id']: row for row in items}
            mastered = mastered_modules(db, owner, course_id, revision)
        outline = outline_of(course)
        titles = {module.id: module.title for module in outline.modules}
        modules = []
        slots = []
        for module in outline.modules:
            waiting = missing_prerequisites(module, mastered)
            status = 'locked' if waiting else 'mastered' if module.id in mastered else 'open'
            modules.append(LibraryModule(id=module.id, title=module.title, status=status,
                                         blocked_by=[titles[key] for key in waiting]))
            for lesson in module.lessons:
                state = states.get(lesson.id) if not waiting else None
                slots.append(LessonSlot(
                    outline_id=lesson.id, module_id=module.id, module_title=module.title, title=lesson.title,
                    objective=lesson.objective, week=lesson.week, locked=bool(waiting),
                    job_id=state['id'] if state else None, lesson_id=state['lesson_id'] if state else None,
                    practice_completed=bool(state and state['practice_completed']),
                ))
        return LessonSlots(items=slots, modules=modules)

    def list_courses(self, owner: str, offset: int, limit: int) -> LibraryPage:
        with self.connection() as db:
            rows = db.execute("""
                SELECT c.id, c.plan_id, c.plan_revision, v.revision, v.created_at, v.content, v.published
                FROM courses c JOIN course_versions v ON v.course_id = c.id
                JOIN assessment_history h ON h.id = c.plan_id
                WHERE h.owner_id = ? AND h.result IS NOT NULL AND v.published = 1
                    AND v.revision = (SELECT MAX(revision) FROM course_versions WHERE course_id = c.id AND published = 1)
                ORDER BY v.created_at DESC, c.id LIMIT ? OFFSET ?
            """, (owner, limit + 1, offset)).fetchall()
        return LibraryPage(items=[
            LibraryItem(id=course.id, title=course.content.title, revision=course.revision,
                        plan_id=course.plan_id, created_at=course.created_at)
            for course in map(course_detail, rows[:limit])
        ], next_offset=offset + limit if len(rows) > limit else None)

    @staticmethod
    def save_lesson(db: sqlite3.Connection, job: dict, publication: LessonPublication) -> None:
        db.execute("""
            INSERT INTO lesson_versions (
                id, course_id, course_revision, outline_id, revision, schema_version, format, outline, content, created_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """, (job['id'], job['course_id'], job['course_revision'], publication.outline.id, SCHEMA_VERSION,
              publication.outline.format, publication.outline.model_dump_json(), publication.content.model_dump_json(),
              datetime.now(timezone.utc).isoformat()))

    @staticmethod
    def view_lesson(db: sqlite3.Connection, owner: str, lesson_id: str) -> LessonRead:
        row = owned_lesson(db, owner, lesson_id)
        try:
            if row['schema_version'] != SCHEMA_VERSION:
                raise ValueError('Schema de lição desconhecido.')
            outline = LessonOutline.model_validate_json(row['outline'])
            content = LESSON_SCHEMAS[row['format']].model_validate_json(row['content'])
            return LessonRead(
                id=row['id'], course_id=row['course_id'], course_revision=row['course_revision'],
                revision=row['revision'], schema_version=row['schema_version'], outline_id=outline.id,
                title=outline.title, objective=outline.objective, week=outline.week,
                competency_ids=outline.competency_ids, format=outline.format, explanation=content.explanation,
                example=content.example, summary=content.summary, exercise=practice_preview(content),
                practice=practice_progress(db, owner, lesson_id),
            )
        except (KeyError, ValueError):
            raise HTTPException(500, 'Não foi possível abrir esta lição salva.') from None

    def install_routes(self, app: FastAPI, require_account) -> None:
        @app.get('/api/courses', response_model=LibraryPage)
        def courses(owner: str = Depends(require_account), offset: int = Query(0, ge=0, le=MAX_REVISION), limit: int = Query(25, ge=1, le=50)):
            return self.list_courses(owner, offset, limit)

        @app.post('/api/courses/{course_id}/publish', response_model=CourseDetail)
        def publish(course_id: str, request: PublishRequest, owner: str = Depends(require_account)):
            return self.publish(owner, course_id, request.draft_revision)

        @app.get('/api/courses/{course_id}/lessons', response_model=LessonSlots)
        def slots(course_id: str, course_revision: int = Query(ge=1, le=MAX_REVISION), owner: str = Depends(require_account)):
            return self.get_slots(owner, course_id, course_revision)

        @app.get('/api/lessons/{lesson_id}', response_model=LessonRead)
        def lesson(lesson_id: str, owner: str = Depends(require_account)):
            with self.connection() as db:
                return self.view_lesson(db, owner, lesson_id)
