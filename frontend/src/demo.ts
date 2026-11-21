export const competencies = [
  { name: 'Comunicação', question: 'Como você explica uma ideia e escuta pontos de vista diferentes?', expected: 3 },
  { name: 'Resolução de problemas', question: 'Como você investiga um problema e propõe uma solução?', expected: 3 },
  { name: 'Organização', question: 'Como você organiza tarefas e acompanha seus prazos?', expected: 3 },
  { name: 'Colaboração', question: 'Como você contribui para uma entrega em equipe?', expected: 3 },
  { name: 'Aprendizagem contínua', question: 'Como você aprende algo novo e coloca em prática?', expected: 3 },
  { name: 'Uso de ferramentas', question: 'Como escolhe e utiliza uma ferramenta para realizar uma tarefa?', expected: 3 },
  { name: 'Revisão de entregas', question: 'Como confere uma entrega e corrige o que não funcionou?', expected: 3 },
  { name: 'Aplicação de feedback', question: 'Como transforma um comentário recebido em uma melhoria concreta?', expected: 3 },
]
export const gap = (expected: number, self: number) => Math.max(0, expected - self)
export const weeks = [
  ['Explorar e observar', 'Escolha uma competência prioritária. Encontre um material introdutório e anote três aprendizados.', 'Uma página de anotações · 2 horas'],
  ['Praticar em pequena escala', 'Crie um exercício simples que use essa competência em uma situação do seu dia a dia.', 'Um exercício concluído · 2 horas'],
  ['Aplicar em colaboração', 'Compartilhe seu exercício com um colega e peça um comentário concreto sobre como melhorar.', 'Uma versão revisada · 2 horas'],
  ['Refletir e continuar', 'Compare o que conseguiu fazer com seu ponto de partida. Escolha o próximo exercício.', 'Uma reflexão e próximo passo · 1 hora'],
]
