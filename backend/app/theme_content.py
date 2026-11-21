"""Structured companion material for a published lesson."""
import re
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import Field, StringConstraints, model_validator

from .blueprint import Identifier, UNSAFE_TEXT
from .lesson_content import ChoiceExercise, Option
from .practice import ChoiceAnswer, grade
from .schemas import Model, normalize


Title = Annotated[str, StringConstraints(min_length=1, max_length=90)]
Point = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Narration = Annotated[str, StringConstraints(min_length=1, max_length=440)]
Paragraph = Annotated[str, StringConstraints(min_length=1, max_length=680)]
Speech = Annotated[str, StringConstraints(min_length=1, max_length=230)]
Speaker = Literal['host', 'expert']
PracticeKind = Literal['quiz', 'simulation']

THEME_PROMPT = (
    'Prepare materiais complementares introdutórios em português do Brasil para uma única lição publicada. '
    'Use como fonte única os dados pedagógicos e o conteúdo da lição fornecidos. Mantenha seu objetivo e nível. '
    'Crie exemplos fictícios curtos, coerentes com o material, sem informar fatos externos não verificados. '
    'Organize a videoaula em 3 a 4 slides com título, pontos e narração em cada slide. '
    'Em pelo menos um slide, use diagram com 2 a 4 rótulos curtos que mostrem um processo passo a passo. '
    'Escreva um capítulo breve com seções em texto corrido, com explicação, exemplo e revisão. '
    'Escreva um diálogo natural de 8 a 12 falas curtas, alternadas, começando pelo apresentador (host). '
    'O apresentador faz perguntas e conecta ideias. A pessoa especialista (expert) explica e aplica o conteúdo. '
    'Crie um mapa mental com o tema central e ramos distintos com detalhes curtos. '
    'No quiz, escreva exatamente três perguntas rápidas de revisão. No simulado, escreva quatro ou cinco '
    'questões de aplicação com situações breves. Use enunciados e IDs distintos nos dois conjuntos. '
    'Cada questão tem 3 a 4 alternativas plausíveis, exatamente uma correta e feedback distinto por alternativa. '
    'Não revele o gabarito no texto da pergunta. Não peça dados pessoais nem use nomes reais, HTML, links, '
    'comandos executáveis, promessas de emprego ou certificação. Retorne apenas JSON compacto conforme o schema.'
)

_PRIVATE_TEXT = re.compile(
    r'\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|(?:\+55\s*)?\(?[1-9]\d\)?\s*9?\d{4}[- ]\d{4})\b'
    r'|\[[^\]\n]+\]\([^\)\n]+\)|\b(?:ftp|file)://',
    re.I,
)


class ThemeSlide(Model):
    title: Title
    points: list[Point] = Field(min_length=1, max_length=3)
    narration: Narration
    diagram: list[Point] | None = Field(default=None, min_length=2, max_length=4)


class ChapterSection(Model):
    title: Title
    text: Paragraph


class ThemeChapter(Model):
    title: Title
    sections: list[ChapterSection] = Field(min_length=2, max_length=4)


class PodcastTurn(Model):
    speaker: Speaker
    text: Speech


class ThemePodcast(Model):
    title: Title
    turns: list[PodcastTurn] = Field(min_length=8, max_length=12)

    @model_validator(mode='after')
    def check_dialogue(self):
        if any(turn.speaker != ('host' if index % 2 == 0 else 'expert')
               for index, turn in enumerate(self.turns)):
            raise ValueError('O podcast deve começar com o apresentador e alternar as duas vozes.')
        return self


class MindBranch(Model):
    label: Title
    details: list[Point] = Field(min_length=1, max_length=3)


class ThemeMap(Model):
    topic: Title
    branches: list[MindBranch] = Field(min_length=2, max_length=5)


class ThemeQuestion(ChoiceExercise):
    id: Identifier
    options: list[Option] = Field(min_length=3, max_length=4)


class ThemePack(Model):
    slides: list[ThemeSlide] = Field(min_length=3, max_length=4)
    chapter: ThemeChapter
    podcast: ThemePodcast
    map: ThemeMap
    quiz: list[ThemeQuestion] = Field(min_length=3, max_length=3)
    simulation: list[ThemeQuestion] = Field(min_length=4, max_length=5)


class GradeRequest(Model):
    answers: dict[Identifier, Identifier] = Field(min_length=1, max_length=5)


def _check_strings(value: str | list | dict | None) -> None:
    if isinstance(value, str):
        text = normalize(value)
        if not text or UNSAFE_TEXT.search(text) or _PRIVATE_TEXT.search(text):
            raise ValueError('Os materiais devem conter texto simples, sem links ou dados identificáveis.')
    elif isinstance(value, list):
        for item in value:
            _check_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            _check_strings(item)


def _distinct(texts: list[str], description: str) -> None:
    canonical = {re.sub(r'[\W_]+', ' ', normalize(text).casefold()).strip() for text in texts}
    if '' in canonical or len(canonical) != len(texts):
        raise ValueError(f'{description} devem ter conteúdo distinto.')


def _assign_question_ids(question: ThemeQuestion) -> ThemeQuestion:
    aliases = {option.id: uuid4().hex for option in question.options}
    return question.model_copy(update={
        'id': uuid4().hex,
        'options': [option.model_copy(update={'id': aliases[option.id]}) for option in question.options],
        'correct_option_id': aliases[question.correct_option_id],
    })


def validate_theme(pack: ThemePack) -> ThemePack:
    """Apply post-generation checks and assign opaque IDs before persistence."""
    pack = ThemePack.model_validate(pack.model_dump())
    _check_strings(pack.model_dump(mode='json'))
    questions = pack.quiz + pack.simulation
    if len({question.id for question in questions}) != len(questions):
        raise ValueError('Os IDs das questões devem ser distintos.')
    _distinct([question.prompt for question in questions], 'Os enunciados do quiz e do simulado')
    _distinct([slide.title for slide in pack.slides], 'Os títulos dos slides')
    diagrams = [slide.diagram for slide in pack.slides if slide.diagram]
    if not diagrams:
        raise ValueError('Pelo menos um slide deve conter um diagrama com etapas.')
    for diagram in diagrams:
        _distinct(diagram, 'As etapas do diagrama')
    _distinct([section.title for section in pack.chapter.sections], 'Os títulos das seções do capítulo')
    _distinct([branch.label for branch in pack.map.branches], 'Os ramos do mapa')
    for branch in pack.map.branches:
        _distinct(branch.details, 'Os detalhes de cada ramo')
    return pack.model_copy(update={
        'quiz': [_assign_question_ids(question) for question in pack.quiz],
        'simulation': [_assign_question_ids(question) for question in pack.simulation],
    })


def public_theme(pack: ThemePack) -> dict:
    question_secrets = {'__all__': {'correct_option_id': True, 'options': {'__all__': {'feedback'}}}}
    return pack.model_dump(mode='json', exclude={'quiz': question_secrets, 'simulation': question_secrets})


def grade_theme(pack: ThemePack, kind: PracticeKind, request: GradeRequest) -> dict:
    questions = pack.quiz if kind == 'quiz' else pack.simulation
    if kind == 'quiz' and len(request.answers) != 1:
        raise HTTPException(422, 'Envie uma questão por vez no quiz.')
    if kind == 'simulation' and request.answers.keys() != {question.id for question in questions}:
        raise HTTPException(422, 'Responda a todas as questões do simulado antes de corrigir.')

    items = []
    for question in questions:
        option_id = request.answers.get(question.id)
        if option_id is None:
            continue
        correct, feedback = grade(question, ChoiceAnswer(kind='multiple_choice', option_id=option_id))
        items.append({'question_id': question.id, 'correct': correct, 'feedback': feedback[0]})
    if not items:
        raise HTTPException(422, 'A questão não pertence a este quiz.')
    return {'items': items, 'correct': sum(item['correct'] for item in items), 'total': len(items)}
