"""Bounded lesson generation schemas and the student-facing projection."""
from dataclasses import dataclass
import json
from typing import Annotated
from uuid import uuid4

from pydantic import Field, StringConstraints, model_validator

from .blueprint import Identifier, LessonOutline, UNSAFE_TEXT
from .schemas import Model, normalize

SCHEMA_VERSION = 1
# Keep lesson jobs outside the prompt versions recognized by blueprint-only workers.
PROMPT_VERSION = 1001
Plain = Annotated[str, StringConstraints(min_length=1, max_length=700)]
Label = Annotated[str, StringConstraints(min_length=1, max_length=160)]
Answer = Annotated[str, StringConstraints(min_length=1, max_length=80)]
PROMPT = (
    'Produza uma única microlição introdutória em português, a partir do objetivo e do formato fornecidos. '
    'Inclua explicação concisa, exemplo pequeno, resumo e um exercício conforme o schema. '
    'No exercício de múltipla escolha, indique exatamente um ID correto e feedback pedagógico por opção, '
    'sem usar a mesma justificativa para opções diferentes. Na ordenação, apresente os passos fora da ordem '
    'correta, defina a ordem dos IDs e inclua feedback por passo. Se for lacuna, use exatamente um marcador '
    '[lacuna], uma resposta curta inequívoca e feedback de acerto e erro. '
    'Use texto simples, sem links, HTML, comandos executáveis, dados pessoais, promessas de emprego ou certificação.'
)


class Option(Model):
    id: Identifier
    label: Label
    feedback: Label


def unique_options(options: list[Option]) -> set[str]:
    ids = {option.id for option in options}
    labels = {normalize(option.label).casefold() for option in options}
    feedback = {normalize(option.feedback).casefold() for option in options}
    if any(len(values) != len(options) for values in (ids, labels, feedback)):
        raise ValueError('Itens ou feedback repetidos.')
    return ids


class ChoiceExercise(Model):
    prompt: Label
    options: list[Option] = Field(min_length=3, max_length=5)
    correct_option_id: Identifier

    @model_validator(mode='after')
    def check_answer(self):
        if self.correct_option_id not in unique_options(self.options):
            raise ValueError('Gabarito de múltipla escolha inválido.')
        return self


class OrderExercise(Model):
    prompt: Label
    steps: list[Option] = Field(min_length=3, max_length=6)
    correct_order: list[Identifier] = Field(min_length=3, max_length=6)

    @model_validator(mode='after')
    def check_permutation(self):
        if (set(self.correct_order) != unique_options(self.steps) or len(self.correct_order) != len(self.steps)
                or self.correct_order == [step.id for step in self.steps]):
            raise ValueError('A ordem correta precisa usar cada passo e diferir da ordem apresentada.')
        return self


class BlankExercise(Model):
    prompt: Label
    answer: Answer
    correct_feedback: Label
    incorrect_feedback: Label

    @model_validator(mode='after')
    def check_single_blank(self):
        if (self.prompt.count('[lacuna]') != 1 or '[lacuna]' in self.answer
                or normalize(self.correct_feedback).casefold() == normalize(self.incorrect_feedback).casefold()):
            raise ValueError('Lacuna, resposta ou feedback incompatível.')
        return self


class LessonText(Model):
    explanation: Plain
    example: Plain
    summary: Plain


class ChoiceLesson(LessonText):
    exercise: ChoiceExercise


class OrderLesson(LessonText):
    exercise: OrderExercise


class BlankLesson(LessonText):
    exercise: BlankExercise


LESSON_SCHEMAS = {
    'multiple_choice': ChoiceLesson,
    'order_steps': OrderLesson,
    'fill_blank': BlankLesson,
}


@dataclass(frozen=True)
class LessonPublication:
    outline: LessonOutline
    content: LessonText


def validate_lesson(outline: LessonOutline, content: LessonText) -> LessonPublication:
    content = LESSON_SCHEMAS[outline.format].model_validate(content.model_dump())
    if UNSAFE_TEXT.search(json.dumps(content.model_dump(mode='json'), ensure_ascii=False)):
        raise ValueError('A lição contém conteúdo não permitido.')
    exercise = content.exercise
    if isinstance(exercise, BlankExercise) and not normalize(exercise.answer):
        raise ValueError('A resposta da lacuna precisa conter texto visível.')
    if isinstance(exercise, ChoiceExercise):
        aliases = {option.id: uuid4().hex for option in exercise.options}
        exercise = exercise.model_copy(update={
            'options': [option.model_copy(update={'id': aliases[option.id]}) for option in exercise.options],
            'correct_option_id': aliases[exercise.correct_option_id],
        })
    elif isinstance(exercise, OrderExercise):
        aliases = {step.id: uuid4().hex for step in exercise.steps}
        exercise = exercise.model_copy(update={
            'steps': [step.model_copy(update={'id': aliases[step.id]}) for step in exercise.steps],
            'correct_order': [aliases[step] for step in exercise.correct_order],
        })
    return LessonPublication(outline, content.model_copy(update={'exercise': exercise}))


def practice_preview(content: ChoiceLesson | OrderLesson | BlankLesson) -> dict:
    exercise = content.exercise
    preview = {'prompt': exercise.prompt}
    if isinstance(exercise, ChoiceExercise):
        preview['options'] = [{'id': option.id, 'label': option.label} for option in exercise.options]
    elif isinstance(exercise, OrderExercise):
        preview['steps'] = [{'id': step.id, 'label': step.label} for step in exercise.steps]
    return preview
