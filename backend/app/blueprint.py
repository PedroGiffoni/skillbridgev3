"""Structured course outlines derived from saved study plans."""
import re
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from .learning import CourseContent, StudyPlanDetail
from .schemas import Model

SCHEMA_VERSION = 1
PROMPT_VERSION = 3
Identifier = Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9_-]{1,40}$')]
Caption = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Goal = Annotated[str, StringConstraints(min_length=1, max_length=180)]
Week = Annotated[int, Field(strict=True, ge=1, le=12)]
UNSAFE_TEXT = re.compile(r'https?://|www\.|<\s*/?[a-z][^>]*>|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}|\x60{3}', re.I)

PROMPT = (
    'Planeje um curso introdutório em português usando somente a carreira, competências e semanas recebidas. '
    'Para esta geração, use quatro módulos com semanas [1,2,3], [4,5,6], [7,8,9] e [10,11,12], nessa ordem. '
    'Inclua exatamente uma microlição para cada semana, em ordem, com três lições por módulo. '
    'Copie para cada microlição todos os competency_ids da sua semana fornecidos nos dados. '
    'Em cada módulo, informe a união dos competency_ids de suas três lições, sem repetir IDs. '
    'Indique pré-requisitos apenas entre módulos anteriores, quando necessários. '
    'Cada microlição tem ID único no curso, título, objetivo verificável e um formato do schema. '
    'Antes de finalizar, confira que nenhuma semana ou competência planejada ficou de fora. '
    'Use IDs de até 40 caracteres, apenas letras, números, hífen ou sublinhado. '
    'Limite títulos a 120 caracteres e objetivos a 180 caracteres. Use texto simples e conciso. '
    'Não escreva exercícios, gabaritos, URLs, dados pessoais, certificados nem diagnósticos de aptidão. '
    'Retorne apenas JSON compacto conforme o schema.'
)


class LessonOutline(Model):
    id: Identifier
    title: Caption
    objective: Goal
    week: Week
    competency_ids: list[Identifier] = Field(min_length=1, max_length=8)
    format: Literal['multiple_choice', 'order_steps', 'fill_blank']


class ModuleOutline(Model):
    id: Identifier
    title: Caption
    objective: Goal
    weeks: list[Week] = Field(min_length=1, max_length=12)
    competency_ids: list[Identifier] = Field(min_length=1, max_length=8)
    prerequisite_module_ids: list[Identifier] = Field(max_length=7)
    lessons: list[LessonOutline] = Field(min_length=3, max_length=8)


class CourseBlueprint(Model):
    title: Caption
    modules: list[ModuleOutline] = Field(min_length=3, max_length=8)


def blueprint_response_schema() -> dict:
    # Nested collection and scalar bounds exceed the provider's grammar complexity limit.
    # The canonical Pydantic model and the plan validation still enforce these constraints.
    bounds = {'minItems', 'maxItems', 'minLength', 'maxLength', 'minimum', 'maximum', 'pattern'}

    def without_bounds(value):
        if isinstance(value, dict):
            return {key: without_bounds(item) for key, item in value.items() if key not in bounds}
        if isinstance(value, list):
            return [without_bounds(item) for item in value]
        return value

    return without_bounds(CourseBlueprint.model_json_schema())


def blueprint_input(plan: StudyPlanDetail, career: str) -> dict:
    return {
        'career': career,
        'competencies': [
            {'id': gap.competency_id, 'name': gap.name, 'gap': gap.gap} for gap in plan.assessment.gaps
        ],
        'weeks': [
            {'week': week.week, 'competency_ids': week.competency_ids, 'estimated_minutes': week.estimated_minutes,
             'prerequisite_weeks': week.prerequisite_weeks}
            for week in plan.assessment.weeks
        ],
    }


def validate_blueprint(blueprint: CourseBlueprint, plan: StudyPlanDetail) -> CourseContent:
    planned = {week.week: set(week.competency_ids) for week in plan.assessment.weeks}
    earlier_modules: dict[str, int] = {}
    lesson_ids: set[str] = set()
    covered: dict[int, set[str]] = {week: set() for week in planned}
    texts = [blueprint.title]
    last_start = 1

    for module in blueprint.modules:
        weeks = set(module.weeks)
        competencies = set(module.competency_ids)
        prerequisites = set(module.prerequisite_module_ids)
        if (module.id in earlier_modules or module.weeks != sorted(weeks) or module.weeks[0] < last_start
                or len(competencies) != len(module.competency_ids)
                or len(prerequisites) != len(module.prerequisite_module_ids)
                or any(ref not in earlier_modules or earlier_modules[ref] > module.weeks[0] for ref in prerequisites)):
            raise ValueError('Referências ou pré-requisitos de módulo inválidos.')
        earlier_modules[module.id] = module.weeks[-1]
        last_start = module.weeks[0]
        lesson_weeks: set[int] = set()
        lesson_competencies: set[str] = set()
        texts.extend((module.title, module.objective))
        for lesson in module.lessons:
            ids = set(lesson.competency_ids)
            if (lesson.id in lesson_ids or lesson.week not in weeks or len(ids) != len(lesson.competency_ids)
                    or not ids.issubset(planned[lesson.week])):
                raise ValueError('Microlição fora da semana ou competência planejada.')
            lesson_ids.add(lesson.id)
            lesson_weeks.add(lesson.week)
            lesson_competencies.update(ids)
            covered[lesson.week].update(ids)
            texts.extend((lesson.title, lesson.objective))
        if lesson_weeks != weeks or lesson_competencies != competencies:
            raise ValueError('Cobertura do módulo incompatível com as microlições.')

    if covered != planned or any(UNSAFE_TEXT.search(text) for text in texts):
        raise ValueError('Cobertura do plano ou conteúdo de texto inválido.')
    return CourseContent(title=blueprint.title,
                         blueprint={'schema_version': SCHEMA_VERSION,
                                    'modules': blueprint.model_dump(mode='json')['modules']})
