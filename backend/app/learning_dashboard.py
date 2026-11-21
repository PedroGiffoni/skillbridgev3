"""Learning evidence, study time and the append-only XP ledger."""
from datetime import datetime, timezone
import json
import sqlite3

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import Field, ValidationError

from .learning import CourseContent, CourseDetail, LearningStore, StudyPlanDetail
from .library import CourseLibrary, LibraryItem, course_detail, outline_of
from .module_access import missing_prerequisites, read_outline
from .schemas import AssessmentV3, Model


class StudyTimeRequest(Model):
    course_id: str = Field(pattern=r'^[0-9a-f]{32}$')
    course_revision: int = Field(strict=True, ge=1, le=(1 << 63) - 1)
    week: int = Field(strict=True, ge=1, le=12)
    minutes: int = Field(strict=True, ge=0, le=1440)


class ReplanRequest(Model):
    expected_revision: int = Field(strict=True, ge=1, le=(1 << 63) - 1)
    minutes_per_week: int = Field(strict=True, ge=1, le=240)


def migrate_dashboard(db: sqlite3.Connection) -> None:
    if db.execute('SELECT 1 FROM learning_migrations WHERE version = 7').fetchone():
        return
    db.execute("""
        CREATE TABLE study_time (
            course_id TEXT NOT NULL,
            course_revision INTEGER NOT NULL,
            owner_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            week INTEGER NOT NULL CHECK (week BETWEEN 1 AND 12),
            minutes INTEGER NOT NULL CHECK (minutes BETWEEN 0 AND 1440),
            PRIMARY KEY (course_id, course_revision, owner_id, week),
            FOREIGN KEY (course_id, course_revision)
                REFERENCES course_versions(course_id, revision) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE xp_ledger (
            owner_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            kind TEXT NOT NULL CHECK (kind IN ('practice', 'mastery')),
            subject TEXT NOT NULL,
            course_id TEXT NOT NULL,
            course_revision INTEGER NOT NULL,
            points INTEGER NOT NULL CHECK (points > 0),
            granted_at TEXT NOT NULL,
            PRIMARY KEY (owner_id, kind, subject),
            FOREIGN KEY (course_id, course_revision)
                REFERENCES course_versions(course_id, revision) ON DELETE CASCADE
        )
    """)
    db.execute('CREATE INDEX xp_ledger_course ON xp_ledger (course_id, course_revision, owner_id)')
    db.execute("""
        CREATE TRIGGER award_practice_xp AFTER INSERT ON practice_attempts
        WHEN NEW.correct = 1
        BEGIN
            INSERT OR IGNORE INTO xp_ledger
                SELECT NEW.owner_id, 'practice', l.id, l.course_id, l.course_revision, 10, NEW.created_at
                FROM lesson_versions l WHERE l.id = NEW.lesson_id;
        END
    """)
    db.execute("""
        CREATE TRIGGER award_mastery_xp AFTER INSERT ON module_mastery
        BEGIN
            INSERT OR IGNORE INTO xp_ledger VALUES (
                NEW.owner_id, 'mastery', NEW.exam_id, NEW.course_id, NEW.course_revision, 50, NEW.granted_at
            );
        END
    """)
    db.execute("""
        INSERT OR IGNORE INTO xp_ledger
            SELECT p.owner_id, 'practice', l.id, l.course_id, l.course_revision, 10, MIN(p.created_at)
            FROM practice_attempts p JOIN lesson_versions l ON l.id = p.lesson_id
            WHERE p.correct = 1 GROUP BY p.owner_id, l.id
    """)
    db.execute("""
        INSERT OR IGNORE INTO xp_ledger
            SELECT owner_id, 'mastery', exam_id, course_id, course_revision, 50, granted_at FROM module_mastery
    """)
    db.execute("""
        CREATE TRIGGER freeze_xp_event BEFORE UPDATE ON xp_ledger
        BEGIN SELECT RAISE(ABORT, 'XP events are immutable'); END
    """)
    db.execute('INSERT INTO learning_migrations (version) VALUES (7)')


def _activity(db: sqlite3.Connection, owner: str, course_id: str, revision: int) -> dict[str, bool]:
    return {row['outline_id']: bool(row['correct']) for row in db.execute("""
        SELECT l.outline_id, MAX(p.correct) AS correct FROM lesson_versions l
        JOIN practice_attempts p ON l.id = p.lesson_id AND p.owner_id = ?
        WHERE l.course_id = ? AND l.course_revision = ?
        GROUP BY l.outline_id
    """, (owner, course_id, revision))}


def _completed_weeks(outline, activity: dict[str, bool]) -> set[int]:
    done: dict[int, list[bool]] = {}
    for module in outline.modules:
        for lesson in module.lessons:
            done.setdefault(lesson.week, []).append(activity.get(lesson.id, False))
    return {week for week, lessons in done.items() if all(lessons)}


def _latest_plan(db: sqlite3.Connection, owner: str, plan_id: str) -> StudyPlanDetail:
    plan = LearningStore._find_owned_plan(db, owner, plan_id, None)
    if plan['revision'] is None:
        raise HTTPException(404, 'Plano de estudos não encontrado.')
    try:
        weeks = db.execute("""
            SELECT payload FROM study_weeks WHERE plan_id = ? AND plan_revision = ? ORDER BY ordinal
        """, (plan_id, plan['revision'])).fetchall()
        assessment = AssessmentV3.model_validate({
            **json.loads(plan['assessment']),
            'weeks': [json.loads(row['payload']) for row in weeks],
        })
        if assessment.source_assessment_id != plan_id:
            raise ValueError('Revisão da trilha incompatível.')
        return StudyPlanDetail(id=plan_id, revision=plan['revision'], created_at=plan['created_at'], assessment=assessment)
    except (ValidationError, TypeError, ValueError):
        raise HTTPException(500, 'Não foi possível abrir esta revisão do plano.') from None


def _completion_for_plan(db: sqlite3.Connection, owner: str, plan_id: str) -> set[int]:
    weeks: set[int] = set()
    for row in db.execute("""
        SELECT v.course_id, v.revision, v.content FROM courses c
        JOIN course_versions v ON v.course_id = c.id WHERE c.plan_id = ? AND v.published = 1
    """, (plan_id,)):
        try:
            outline = read_outline(CourseContent.model_validate_json(row['content']))
        except (ValidationError, HTTPException):
            # Older published payloads may have no generated outline and no completion evidence.
            continue
        weeks.update(_completed_weeks(outline, _activity(db, owner, row['course_id'], row['revision'])))
    return weeks


def _card(course: CourseDetail) -> LibraryItem:
    return LibraryItem(id=course.id, plan_id=course.plan_id, revision=course.revision,
                       created_at=course.created_at, title=course.content.title)


def _earned_week(start: datetime, granted_at: str) -> int:
    elapsed = datetime.fromisoformat(granted_at) - start
    return max(1, min(12, elapsed.days // 7 + 1))


class LearningDashboard:
    def __init__(self, learning: LearningStore):
        self.learning = learning
        self.connection = learning.connection

    @staticmethod
    def _latest_courses(db: sqlite3.Connection, owner: str) -> list[CourseDetail]:
        rows = db.execute("""
            SELECT c.id, c.plan_id, c.plan_revision, v.revision, v.content, v.published, v.created_at
            FROM courses c JOIN course_versions v ON v.course_id = c.id
            JOIN assessment_history h ON h.id = c.plan_id
            WHERE h.owner_id = ? AND h.result IS NOT NULL AND v.published = 1
                AND v.revision = (SELECT MAX(revision) FROM course_versions WHERE course_id = c.id AND published = 1)
            ORDER BY v.created_at DESC, c.id
        """, (owner,))
        return [course_detail(row) for row in rows]

    def dashboard(self, owner: str, course_id: str | None = None) -> dict:
        with self.connection() as db:
            db.execute('BEGIN')
            courses = self._latest_courses(db, owner)
            course = next((item for item in courses if item.id == course_id), None) if course_id else next(iter(courses), None)
            if course_id and course is None:
                raise HTTPException(404, 'Curso não encontrado.')
            view = {'courses': [_card(item) for item in courses], 'course': _card(course) if course else None,
                    'plan_revision': None, 'xp': 0, 'achievements': [], 'weeks': [], 'competencies': [],
                    'modules': [], 'next_lesson': None}
            if course is not None:
                view.update(self._course_data(db, owner, course))
            return view

    @staticmethod
    def _course_data(db: sqlite3.Connection, owner: str, course: CourseDetail) -> dict:
        plan = _latest_plan(db, owner, course.plan_id)
        outline = outline_of(course)
        activity = _activity(db, owner, course.id, course.revision)
        keys = (course.id, course.revision, owner)
        exams = db.execute("""
            SELECT module_id, result FROM module_exams
            WHERE course_id = ? AND course_revision = ? AND owner_id = ? AND submitted_at IS NOT NULL
            ORDER BY ordinal, id
        """, keys)
        totals = {gap.competency_id: [0, 0] for gap in plan.assessment.gaps}
        latest = {}
        for row in exams:
            result = json.loads(row['result'])
            latest[row['module_id']] = result
            for skill in result['competencies']:
                if skill['id'] in totals:
                    totals[skill['id']][0] += skill['correct']
                    totals[skill['id']][1] += skill['total']
        granted = {row['module_id']: row['granted_at'] for row in db.execute("""
            SELECT module_id, granted_at FROM module_mastery
            WHERE course_id = ? AND course_revision = ? AND owner_id = ?
        """, keys)}
        times = dict(db.execute("""
            SELECT week, minutes FROM study_time WHERE course_id = ? AND course_revision = ? AND owner_id = ?
        """, keys))
        xp = db.execute("""
            SELECT COALESCE(SUM(points), 0) FROM xp_ledger WHERE course_id = ? AND course_revision = ? AND owner_id = ?
        """, keys).fetchone()[0]

        first = db.execute("""
            SELECT created_at FROM study_plan_versions WHERE plan_id = ? AND revision = 1
        """, (plan.id,)).fetchone()
        start = datetime.fromisoformat(first['created_at'])
        titles = {module.id: module.title for module in outline.modules}
        mastered: dict[str, int] = {}
        studying: set[str] = set()
        review: set[str] = set()
        lesson_counts = {week.week: [0, 0] for week in plan.assessment.weeks}
        modules = []
        next_lesson = None
        for module in outline.modules:
            waiting = missing_prerequisites(module, set(granted))
            recent = latest.get(module.id)
            if recent and not recent['passed']:
                review.update(skill['id'] for skill in recent['competencies'] if skill['correct'] < skill['total'])
            if module.id in granted:
                week = _earned_week(start, granted[module.id])
                for key in module.competency_ids:
                    mastered[key] = min(mastered.get(key, week), week)

            completed = 0
            for lesson in module.lessons:
                entered = lesson.id in activity
                done = activity.get(lesson.id, False)
                if entered:
                    studying.update(lesson.competency_ids)
                completed += done
                lesson_counts[lesson.week][0] += done
                lesson_counts[lesson.week][1] += 1
                if next_lesson is None and not done and not waiting:
                    next_lesson = {'outline_id': lesson.id, 'title': lesson.title}
            modules.append({
                'id': module.id, 'title': module.title, 'objective': module.objective, 'weeks': module.weeks,
                'competency_ids': module.competency_ids,
                'prerequisites': [{'id': key, 'title': titles[key], 'satisfied': key in granted}
                                  for key in module.prerequisite_module_ids],
                'status': 'locked' if waiting else 'mastered' if module.id in granted else 'open',
                'lessons_completed': completed, 'lessons_total': len(module.lessons),
                'latest_score': recent['score'] if recent else None,
                'reinforcement': recent['reinforcement'] if recent and not recent['passed'] else [],
            })

        weeks = []
        for week in plan.assessment.weeks:
            complete, total = lesson_counts[week.week]
            weeks.append({
                'week': week.week, 'title': week.title, 'planned_minutes': week.estimated_minutes,
                'recorded_minutes': times.get(week.week, 0), 'lessons_completed': complete, 'lessons_total': total,
                'complete': bool(total and complete == total), 'mastered_count': sum(i <= week.week for i in mastered.values()),
            })
        competencies = []
        for gap in plan.assessment.gaps:
            key = gap.competency_id
            if key in mastered:
                status = 'mastered'
            elif key in review:
                status = 'review'
            elif key in studying or totals[key][1]:
                status = 'studying'
            else:
                status = 'not_started'
            competencies.append({'id': key, 'name': gap.name, 'status': status,
                                 'correct': totals[key][0], 'total': totals[key][1]})
        achievements = []
        if any(activity.values()):
            achievements.append('Primeira prática concluída')
        if any(week['complete'] for week in weeks):
            achievements.append('Primeira semana concluída')
        if granted:
            achievements.append('Primeiro módulo dominado')
        return {'plan_revision': plan.revision, 'weeks': weeks, 'competencies': competencies, 'modules': modules,
                'xp': xp, 'achievements': achievements, 'next_lesson': next_lesson}

    def save_time(self, owner: str, request: StudyTimeRequest) -> dict:
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            CourseLibrary._version(db, owner, request.course_id, request.course_revision, published=True)
            latest = db.execute("""
                SELECT MAX(revision) FROM course_versions WHERE course_id = ? AND published = 1
            """, (request.course_id,)).fetchone()[0]
            if latest != request.course_revision:
                raise HTTPException(409, 'Reabra o painel para registrar a revisão atual.')
            db.execute("""
                INSERT INTO study_time (course_id, course_revision, owner_id, week, minutes) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (course_id, course_revision, owner_id, week) DO UPDATE SET minutes = excluded.minutes
            """, (request.course_id, request.course_revision, owner, request.week, request.minutes))
        return self.dashboard(owner, request.course_id)

    def replan(self, owner: str, plan_id: str, request: ReplanRequest) -> StudyPlanDetail:
        # Ensure historic V3 diagnostics that predate the materialization have a base revision.
        self.learning.get_plan(owner, plan_id)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            plan = _latest_plan(db, owner, plan_id)
            done = _completion_for_plan(db, owner, plan_id)
            weeks = [week if week.week in done else week.model_copy(update={'estimated_minutes': request.minutes_per_week})
                     for week in plan.assessment.weeks]
            if weeks == plan.assessment.weeks:
                return plan
            if plan.revision != request.expected_revision:
                raise HTTPException(409, 'A trilha foi atualizada. Reabra a revisão atual antes de replanejar.')
            started = datetime.now(timezone.utc).isoformat()
            revision = plan.revision + 1
            assessment = plan.assessment.model_copy(update={'weeks': weeks})
            db.execute("""
                INSERT INTO study_plan_versions (plan_id, revision, created_at, assessment) VALUES (?, ?, ?, ?)
            """, (plan_id, revision, started, assessment.model_dump_json(exclude={'weeks'})))
            db.executemany("""
                INSERT INTO study_weeks (plan_id, plan_revision, ordinal, payload) VALUES (?, ?, ?, ?)
            """, ((plan_id, revision, week.week, week.model_dump_json()) for week in weeks))
            return StudyPlanDetail(id=plan_id, revision=revision, created_at=started, assessment=assessment)

    def install_routes(self, app: FastAPI, require_account) -> None:
        @app.get('/api/me/dashboard')
        def dashboard(course_id: str | None = Query(None, max_length=40), owner: str = Depends(require_account)):
            return self.dashboard(owner, course_id)

        @app.post('/api/me/dashboard/time')
        def study_time(request: StudyTimeRequest, owner: str = Depends(require_account)):
            return self.save_time(owner, request)

        @app.post('/api/study-plans/{plan_id}/replan', response_model=StudyPlanDetail)
        def replan(plan_id: str, request: ReplanRequest, owner: str = Depends(require_account)):
            return self.replan(owner, plan_id, request)
