"""Fixtures offline para testes; a aplicação não importa nem oferece estes dados."""

from .schemas import Competency, Gap, Guidance, Week
from .demo_options import DEMO_OPTIONS

DEMO_NOTICE = 'DEMONSTRAÇÃO — sem análise Gemini. Competências e roteiro genéricos; não personalizados para a profissão.'
ASSESSMENT_DEMO_NOTICE = 'DEMONSTRAÇÃO — diagnóstico e trilha sem análise Gemini. Lacunas refletem o questionário exibido e suas respostas; roteiro genérico.'
LIMITATION = 'Autoavaliação orientativa, não certificação ou teste de aptidão. Não garante contratação.'


def competencies() -> list[Competency]:
    entries = [
        ('communication', 'Comunicação', 'Como você explica ideias e escuta diferentes pontos de vista?'),
        ('problem_solving', 'Resolução de problemas', 'Como investiga um problema e propõe uma solução?'),
        ('organization', 'Organização', 'Como organiza tarefas e acompanha prazos?'),
        ('collaboration', 'Colaboração', 'Como contribui para uma entrega em equipe?'),
        ('learning', 'Aprendizagem contínua', 'Como aprende algo novo e coloca em prática?'),
        ('tools', 'Uso de ferramentas', 'Como escolhe e utiliza uma ferramenta para realizar uma tarefa?'),
        ('quality', 'Revisão de entregas', 'Como confere uma entrega e corrige o que não funcionou?'),
        ('feedback', 'Aplicação de feedback', 'Como transforma um comentário recebido em uma melhoria concreta?'),
    ]
    return [Competency(id=id_, name=name, description='Competência genérica para reflexão educacional.',
                       question=question, expected_level=3,
                       options=[{'value': value, 'label': label} for value, label in enumerate(DEMO_OPTIONS[i])])
            for i, (id_, name, question) in enumerate(entries)]


def guidance(gaps: list[Gap]) -> Guidance:
    ranked = sorted(gaps, key=lambda item: -item.gap)
    priorities = [f'{g.name}: lacuna didática {g.gap}.' for g in ranked if g.gap > 0]
    focus = ranked[0].name if priorities else 'uma competência de sua escolha'
    entries = [
        ('Explorar e observar', f'Explore {focus}.', 'Estude um material introdutório e anote três aprendizados.', 'Uma página de anotações · até 2 horas'),
        ('Praticar em pequena escala', f'Pratique {focus}.', 'Crie um exercício simples em contexto acadêmico.', 'Um exercício concluído · até 2 horas'),
        ('Aplicar em colaboração', 'Busque feedback concreto.', 'Compartilhe o exercício com um colega e revise sua entrega.', 'Uma versão revisada · até 2 horas'),
        ('Refletir e continuar', 'Escolha seu próximo passo.', 'Compare seu exercício com o ponto de partida e escolha a próxima prática.', 'Reflexão e próximo exercício · até 1 hora'),
    ]
    return Guidance(
        summary='Roteiro de demonstração: use as diferenças como ponto de reflexão e adapte a prática ao seu contexto.',
        strengths=[f'{g.name}: nível autodeclarado {g.self_level}/4, alcança a referência estimativa.' for g in gaps if g.self_level >= g.expected_level],
        priorities=priorities,
        weeks=[Week(week=i + 1, title=t, objective=o, actions=[a], deliverable=d) for i, (t, o, a, d) in enumerate(entries)],
        limitations=[LIMITATION, 'Referências são estimativas educacionais; não são padrões verificados de mercado.'],
    )
