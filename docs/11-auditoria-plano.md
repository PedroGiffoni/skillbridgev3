# Auditoria, backlog e plano — 10/11/2026

Lidos AGENTS.md, todos os 11 documentos originais, cinco prompts e seis skills locais. Documentação coerente; hipótese do problema e H1–H3 ainda não validadas. Não há integrantes, ata real de brainstorming, respostas de participantes ou evidências de sprints anteriores. Conferência da rubrica com enunciado original F108 cabe à equipe.

## Plano e decisões

Fases 0 e 1 autorizadas juntas nesta rodada. Frontend React/TS/Vite/Tailwind independente, estado em memória, sem chamadas externas. Backend apenas reservado. SQLite depende de necessidade real, conforme pedido e arquitetura; nenhuma persistência por padrão. A referência fixa 3/4 e a trilha são didáticas e genéricas; profissão muda apenas contexto visual. Sem modelo ou cota Gemini presumidos.

Fase 2 após autorização: FastAPI/Pydantic, contratos com limites e IDs únicos, escala 0–4, cálculo autoritativo no servidor, mocks, CORS restrito e Pytest. Decidir retenção/persistência mínima se necessária.
Fase 3: confirmar modelo/cota na conta e fontes oficiais, SDK google-genai, duas chamadas estruturadas, validação, timeout/429/retry limitado e fallback explícito. Segredo só no servidor, logs sem dados pessoais/prompts integrais.
Fase 4: E2E navegador, 360/768/1280, teclado/contraste/movimento reduzido, integração e publicação aprovada.
Fase 5: coleta real consentida com ≥10 universitários, métricas, gráficos e relatório com evidências reais.

## Matriz de rastreabilidade / Kanban

Endpoints são planejados, não implementados. Responsável técnico: Codex; pesquisa e aprovação: equipe (nomes pendentes). Critérios abaixo definem aceite. Evidência técnica: fontes e testes em docs/12-verificacao-fase-1.md.

| ID / requisitos | Tela / entrega | Endpoint futuro | Aceite / verificação | Fase / estado |
|---|---|---|---|---|
| SB01 RF01–02 | Perfil | /api/questionnaire | Profissão 3–100 caracteres, contexto opcional, ciência local; teste de fluxo | 1 / revisão |
| SB02 RF03, RF10 | Perguntas demo | /api/questionnaire | Cinco competências fixas, aviso sem personalização; teste de fluxo | 1 / revisão |
| SB03 RF04–05 | Autoavaliação | /api/assessment | Nível obrigatório, progresso, revisão preservada; teste de fluxo | 1 / revisão |
| SB04 RF06, RF08 | Diagnóstico/trilha | /api/assessment | Fórmula e referência claras, quatro semanas; testes de lacuna/fluxo | 1 / revisão |
| SB05 RF09 | Reinício | nenhum | Limpa contexto, respostas e consentimento; teste de fluxo | 1 / revisão |
| SB06 RNF01–02 | Todas | nenhum | Labels, foco, layout responsivo, reduced-motion; inspeção navegador pendente | 1 / parcial |
| SB07 RNF03–06 | API | /health, /api/questionnaire, /api/assessment | Contratos, segurança, cálculo no servidor e Pytest | 2 / backlog |
| SB08 RF03, RF07, RF10 | Integração | /api/questionnaire, /api/assessment | JSON validado, timeout/429 e fallback testados | 3 / backlog |
| SB09 RNF01–06 | Publicação/qualidade | todos | E2E e acessibilidade, hospedagem aprovada | 4 / backlog |
| SB10 RF11, RNF05 | Pesquisa | /api/feedback opcional | Coleta anônima consentida real; sem formulário ativo agora | 5 / backlog |
| SB11 RNF07 / F108 | Documentação | nenhum | Sprints, matriz, relatório e anexos reais | todas / andamento |

Carregamento, vazio, timeout e erro de serviço ficam para integração; não há simulação de requisição remota no protótipo. Nenhuma captura ou pesquisa foi produzida nesta rodada.

## Evolução posterior à aprovação do protótipo
Em 10/11/2026 o usuário solicitou integração Gemini. SB07 pronto para revisão técnica; SB08 preparado, aguardando elegibilidade/modelo para ativação real. Matriz atual e resultados estão em docs/13-integracao-gemini.md. Demais itens de pesquisa/publicação continuam pendentes.
