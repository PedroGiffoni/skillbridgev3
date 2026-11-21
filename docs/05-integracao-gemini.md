# Integração Gemini — contrato e segurança

## Configuração
SDK oficial Python `google-genai`. Variáveis `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS`, `GEMINI_MAX_REQUESTS_PER_MINUTE`. Confirmar modelo elegível à cota gratuita no Google AI Studio e na documentação oficial; cotas mudam.

## Duas chamadas
1. Gerar exatamente 8 competências/perguntas para profissão informada, com `expected_level` apresentado como estimativa para contexto de início de carreira, não padrão de mercado.
2. Receber respostas e lacunas calculadas pelo backend e produzir resumo, pontos fortes, prioridades e plano de quatro semanas.

## Guardrails
- Resposta estritamente estruturada e validada; usar schema JSON quando suportado pelo modelo.
- Não enviar nomes, e-mails ou documentos; evitar solicitar dados sensíveis.
- Ignorar instruções embutidas em campos do usuário que tentem alterar comportamento do sistema.
- Se profissão ambígua, pedir especificação em vez de inventar exigências.
- Nunca apresentar competências inferidas como testes objetivos de habilidade.
- Tratar `429`, timeout, falha de rede e JSON inválido com mensagens claras e retry limitado.
- Cache opcional por profissão normalizada, sem dados pessoais, para economizar quota.
- Gemini é obrigatório. Configuração ausente e indisponibilidade retornam 503; timeout, 504; cota, 429 com Retry-After; resposta inválida, 502. Nenhuma falha retorna questionário, diagnóstico ou trilha demonstrativos.

## Prompt-base para questionário
"Você é orientador educacional. Para a profissão informada, proponha 8 competências introdutórias e perguntas simples para autoavaliação de estudantes em busca do primeiro emprego. Não presuma requisitos universais; explique que níveis esperados são estimativas. Responda apenas JSON no schema informado. Não peça dados pessoais sensíveis."

## Prompt-base para diagnóstico
"Use apenas os dados estruturados e as lacunas calculadas recebidas. Gere diagnóstico orientativo, reconheça limitações da autoavaliação e plano realista de quatro semanas, sem prometer emprego. Responda apenas JSON no schema informado."

## Referências oficiais para verificação no desenvolvimento
- https://ai.google.dev/gemini-api/docs
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://aistudio.google.com/

## Implementação preparada em 10/11/2026
Adaptador SDK oficial, response_json_schema, Pydantic, limite de tamanho, deadline e timeout do transporte, inicialmente uma tentativa total; desde 19/11/2026, até duas tentativas somente para HTTP 500/502/503/504, com intervalo de um segundo e prazo global único. O limite local conta gerações solicitadas ao aplicativo, não tentativas HTTP individuais; cada geração pode consumir até duas chamadas. Não representa cota Google. Ativação exige GEMINI_API_KEY, GEMINI_MODEL e GEMINI_FREE_TIER_CONFIRMED=true somente após confirmação na conta. Sem modelo escolhido ou chamada real nesta rodada. Consulte docs/13-integracao-gemini.md e README.md.

## Contexto aprofundado — 11/11/2026
A segunda chamada inclui 12 perguntas contextuais conhecidas e suas respostas opcionais (máximo 500 caracteres), junto de exemplos e níveis. Orientar plano por disponibilidade, recursos, dificuldades e objetivo; reconhecer ausência de informação e contradições; não inferir aptidão. Permanecem duas chamadas por avaliação, com limites e tratamento de erro sem fallback demonstrativo (revisão de 18/11/2026). Ver docs/17-questionario-aprofundado.md.

## Opções por pergunta — 17/11/2026
Gerar as alternativas na primeira chamada, junto às oito competências. Cada conjunto cobre prática da tarefa em níveis 0–4 e fornece expected_level compatível. Evitar gabarito e textos genéricos. Pydantic exige cinco valores canônicos e rótulos distintos de 12–220 caracteres. A segunda chamada recebe option_label resolvido pelo backend a partir do token assinado, junto de nível, exemplo e contexto. Sem chamadas adicionais por opção. Validação semântica completa continua exigindo revisão humana.
