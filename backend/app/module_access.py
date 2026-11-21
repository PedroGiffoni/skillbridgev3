"""Progression gates shared by lesson, practice and assessment routes."""
import sqlite3

from fastapi import HTTPException
from pydantic import ValidationError

from .blueprint import CourseBlueprint, ModuleOutline, SCHEMA_VERSION
from .learning import CourseContent


def read_outline(content: CourseContent) -> CourseBlueprint:
    try:
        blueprint = content.blueprint
        if type(blueprint.get('schema_version')) is not int or blueprint['schema_version'] != SCHEMA_VERSION:
            raise ValueError('Versão de estrutura desconhecida.')
        return CourseBlueprint.model_validate({'title': content.title, 'modules': blueprint.get('modules')})
    except (ValueError, ValidationError):
        raise HTTPException(409, 'Este curso não tem um plano de lições compatível.') from None


def mastered_modules(db: sqlite3.Connection, owner: str, course_id: str, revision: int) -> set[str]:
    return {row['module_id'] for row in db.execute("""
        SELECT module_id FROM module_mastery
        WHERE course_id = ? AND course_revision = ? AND owner_id = ?
    """, (course_id, revision, owner))}


def missing_prerequisites(module: ModuleOutline, mastered: set[str]) -> list[str]:
    return [key for key in module.prerequisite_module_ids if key not in mastered]


def assert_module_open(db: sqlite3.Connection, owner: str, course_id: str, revision: int,
                       module: ModuleOutline) -> None:
    if module.prerequisite_module_ids and missing_prerequisites(module, mastered_modules(db, owner, course_id, revision)):
        raise HTTPException(403, 'Conclua a avaliação dos módulos anteriores para liberar este conteúdo.')


def assert_lesson_open(db: sqlite3.Connection, owner: str, lesson: sqlite3.Row) -> None:
    try:
        course = CourseContent.model_validate_json(lesson['course_content'])
    except ValidationError:
        raise HTTPException(500, 'Não foi possível abrir o curso desta lição.') from None
    for module in read_outline(course).modules:
        if any(item.id == lesson['outline_id'] for item in module.lessons):
            assert_module_open(db, owner, lesson['course_id'], lesson['course_revision'], module)
            return
    raise HTTPException(404, 'Lição não encontrada.')
