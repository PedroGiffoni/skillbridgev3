# Planejamento de sprints — janela curta até 27/11/2026

## Sprint 1 — 11 a 14/11
Problema ODS 8, brainstorming real, requisitos, escopo MVP, critérios de aceitação, protótipos de baixa fidelidade. Evidências: atas e prints do quadro.

## Sprint 2 — 15 a 19/11
Front-end, API, Gemini, fluxo completo, estados de erro e testes técnicos. Evidências: commits, capturas, quadro.

## Sprint 3 — 20 a 24/11
Testes com ≥10 usuários, coleta anônima, correções priorizadas, gráficos e interpretação. Evidências: formulários, logs de sessão anônimos, quadro.

## Finalização — 25 a 26/11
Relatório, anexos, revisão e preenchimento Dream Shape. Entrega em 27/11.

## Kanban
Backlog | A fazer | Em andamento | Em revisão | Concluído. Cada cartão: ID, descrição, responsável, sprint, critério de aceite, link da evidência. Fotografar/exportar quadro em cada sprint; não criar retrospectivas fictícias.

## Registro real — 10/11/2026
Preparação antecipada das Fases 0 e 1: auditoria, backlog SB01–SB11 e protótipo técnico. SB01–SB05 em revisão; SB06 parcial; SB07–SB10 no backlog; SB11 em andamento. Responsável técnico: Codex; validação: equipe. Ver docs/11-auditoria-plano.md e docs/12-verificacao-fase-1.md. Não houve reunião, retrospectiva ou teste com usuários registrado. Datas das sprints acima permanecem planejamento.

## Registro real — integração solicitada em 10/11/2026
Usuário aprovou visual do protótipo e pediu Gemini. SB07 (base API) pronto para revisão, SB08 (adaptador e frontend) preparado com mocks; ativação real pendente de modelo/cota confirmados. SB04/SB05 verificados por testes adicionais; SB06 permanece parcial. SB11 atualizado. Evidência técnica: docs/13-integracao-gemini.md. Nenhuma coleta real com usuários, reunião, retrospectiva ou publicação nesta rodada.

## Versionamento — 10/11/2026
A pedido do usuário, repositório privado PedroGiffoni/skillbridge criado e preparado para o primeiro envio em main. SB11: documentação e versionamento técnico em revisão. Evidências do envio: docs/14-repositorio-github.md e histórico real do GitHub. Testes com usuários e publicação da aplicação continuam pendentes.

## Publicação autorizada — 10/11/2026
SB09 em andamento: preparação Render/Vercel, 36 testes backend + 8 frontend aprovados, lint/build aprovados. Acesso Render pendente de login no registro inicial; não afirmar deploy concluído. SB11 atualizado em docs/15-publicacao.md. Sem testes de usabilidade ou métricas acadêmicas nesta rodada.

SB09 — tentativa de publicação: configurações enviadas no commit 70b8fec. Vercel solicitou passkey e Render não confirmou login. Nenhum deploy declarado concluído; pendência de acesso do titular registrada em docs/15-publicacao.md.

## Publicação verificada — 11/11/2026
SB09: frontend Vercel Ready e backend Render Free live; fluxo publicado de demonstração verificado por HTTP e no navegador. CORS, consentimento, lacunas e quatro semanas conferidos com dados sintéticos. SB08 continua pendente de modelo/cota e teste Gemini real. SB06 revisão completa de acessibilidade e SB10 pesquisa real permanecem pendentes. Evidências e IDs reais: docs/15-publicacao.md.

## Ativação técnica Gemini — 11/11/2026
SB08: modelo/cota confirmados e teste real local aprovado (6 competências, 4 semanas, lacunas determinísticas). Ativação hospedada em andamento: variáveis não secretas configuradas; chave Render e teste real online pendentes. SB11: README enriquecido e registro docs/16-ativacao-gemini.md. SB10 continua pendente; nenhuma validação com usuários alegada.

SB08 — atualização final 11/11: Gemini ativado no Render e fluxo publicado verificado com dados sintéticos. SB09: backend live com Gemini. 36 testes backend e 8 frontend aprovados; lint/build/pip check aprovados. SB11: README com capturas reais e documentação atualizada. SB06 auditoria completa e SB10 usuários reais continuam pendentes.

## Aprofundamento solicitado — 11/11/2026
SB03/SB08/RF03–05/RF07: 8 competências + 12 contextuais implementadas; revisão e pulo preservam respostas. 41 testes backend e 8 frontend aprovados, lint/build aprovados. SB11: requisitos, README e registro 17 atualizados. Verificação publicada em andamento. SB10 pesquisa com usuários permanece pendente.

SB03/SB08/SB09 — verificação publicada concluída: commit 128f3b1, Render live/Vercel READY. Fluxo real com 20 perguntas e contexto sintético gerou diagnóstico e quatro semanas ajustadas à disponibilidade de 2h/semana. Duas chamadas Gemini. Capturas novas e limites no registro 17. SB10 continua pendente.

## Revisão editorial da interface — 11/11/2026
SB06/SB11: cabeçalho, rodapé, destaque da landing, conclusão e erros com linguagem voltada ao usuário final. Removidas referências à entrega da faculdade. 41 testes backend e 8 frontend aprovados; lint/build aprovados. Sem alteração no questionário ou na lógica de diagnóstico. Ver docs/18-textos-interface.md.

Revisão editorial publicada: cc43615, Vercel READY e Render live. Início e conclusão conferidos no navegador em demonstração local, sem consumir Gemini. Evidências no registro 18.

## Material de apresentação — 11/11/2026
SB11: apresentação de 12 slides em PowerPoint e HTML animado produzida a pedido do usuário. Capturas reais e dados sintéticos identificados, notas de fala e guia de uso. Ver docs/19-apresentacao.md. SB10: comunicação com beneficiários e validação real continuam pendentes.

SB11 — adaptação móvel: apresentação vertical de 12 seções, navegação por toque e capturas ampliáveis; testada em viewports 360/390px. Rota pública publicada e verificada na Vercel: /apresentacao.html. Registro em docs/19-apresentacao.md.

SB11 — ajuste solicitado: substituir apenas a apresentação vertical pelo formato horizontal 16:9, mantendo o mesmo endereço /apresentacao.html. Sem alteração na aplicação principal.

## Sprint 2 — alternativas contextualizadas (17/11/2026)
SB03/SB08/RF03–07: cinco opções específicas por pergunta, escala 0–4 preservada, rótulo assinado enviado ao diagnóstico, demo com opções próprias. 52 testes backend e 15 frontend aprovados; lint/build aprovados. SB11 atualizado no registro 20. Publicação e inspeção real em andamento. Nenhuma pesquisa com participantes nesta rodada.

SB03/SB08 — publicação verificada em 17/11: f315de3, Vercel READY e Render live; oito conjuntos de cinco opções, revisão preservada, diagnóstico Gemini e quatro semanas conferidos com dados sintéticos. Evidência e limitações no registro 20. SB10 pesquisa real segue pendente.

## Sprint 2 — temas e movimento (17/11/2026)
SB06/SB09: alternância claro/escuro, Motion e Three.js decorativo com fallback e movimento reduzido. SB11: README, decisão e registro 21 atualizados. 17 testes frontend, lint/build aprovados; viewport local 390px sem overflow na landing/primeira pergunta. Publicação em verificação. SB10 validação com beneficiários permanece pendente.

SB06/SB09: publicação 7fe98f5 verificada, Vercel READY; temas e canvas presentes na aplicação, apresentação horizontal preservada. Capturas reais no registro 21.

## Documentação visual - 17/11/2026
SB11: PDF com 25 prints fornecidos, 27 páginas, gerado e renderizado para revisão. Ver registro 22. SB10 validação real continua pendente; nenhuma pesquisa realizada nesta tarefa.

## Sprint 2 - personagens 3D (17/11/2026)
SB06/SB09/SB11: dois GLB, quatro animações por modelo, estúdio de prévia independente e documentação. Validador glTF sem erros/avisos; 17 testes frontend e lint/build aprovados. Acabamento em revisão; publicação em verificação. SB10 pesquisa real permanece pendente.

SB06/SB09: prévia 3D d832a6f publicada, Vercel READY; modelos carregados, animação e restauração da pose conferidas. Aplicação principal preservada. Captura real e pacote de entrega no registro 23.

## Revisão dos movimentos 3D - 17/11/2026
SB06/SB09: curvas suaves, coordenação de articulações e transições graduais. Validação glTF sem erros/avisos; testes de continuidade adicionados. Lint/build e 17 testes aprovados. Publicação em andamento; SB10 pesquisa real pendente.

SB06/SB09: revisão 42a2920 publicada, Vercel READY; aceno, respiração e retorno gradual conferidos no navegador. Rig rígido preservado; avaliação subjetiva dos movimentos pelo responsável pendente. Registro 24 atualizado.

## Sprint 2 — Avaliação exclusivamente com IA (18/11/2026)
SB08/RF03/RF07/RF10: remover botão e fallback sem IA, restringir contratos à origem Gemini, preservar respostas em falhas e permitir nova tentativa. SB09: 56 testes backend e 20 frontend do pacote de publicação aprovados, lint/build aprovados; commit funcional 21743c1 publicado, Vercel READY/Render live, perfil e contrato verificados sem chamadas reais Gemini. SB11: requisitos, README e registro 27 atualizados. SB10: pesquisa com usuários reais permanece pendente. Estudos locais 3D não integram esta publicação.

## Correção de disponibilidade Gemini — 19/11/2026
SB08/SB09/RF07/RF10: investigar erro reportado pelo responsável. Cota gratuita e modelo conferidos; reproduzido HTTP 503 do Google, com outra geração pública bem-sucedida. 70 testes backend aprovados e implementação revisada: uma única nova tentativa seletiva, prazo global preservado, categorias de acesso/configuração e logs sem dados sensíveis. SB11: README e registro 28. SB10: pesquisa com beneficiários permanece pendente.

SB08/SB09 — correção 435182e publicada, Vercel READY/Render live. Fluxo real permaneceu bloqueado por 503 do provedor nas duas tentativas. Alternativas gratuitas testadas sem sucesso; configuração original preservada. Retentativa validada com mocks, normalização externa e teste completo continuam pendentes; registro 28.

## Evolução pós-MVP — Login e histórico (20/11/2026)
- SB-LOGIN: entrada por código de e-mail e Google, questionário público e diagnóstico protegido.
- SB-HISTÓRICO: avaliações por conta, reabertura e exclusão.
- SB-PERFIL: edição opcional de foto, nome de exibição, curso, semestre e objetivo.
- Próxima validação: credenciais e serviços externos no ambiente aprovado. O [registro 30](30-login-historico-perfil.md) reúne configuração e evidências locais.

## Evolução pós-MVP — Questionário de alternativas (20/11/2026)

SB03/RF04–05/RF07: respostas por seleção única, validação de opções por pergunta e revisão de rascunhos anteriores. Evidência técnica em `backend/tests/test_api.py` e `frontend/src/integration.test.tsx`.

## Evolução pós-MVP — Carreiras de tecnologia (20/11/2026)

SB01/SB06/RF01: página inicial com foco em tecnologia e catálogo de 72 carreiras em 12 áreas. Seleção por clique ou busca por nome, sigla e sinônimos. O FastAPI confere a carreira antes de chamar o Gemini. Rascunhos válidos e histórico anteriores continuam acessíveis.

| Verificação local | Resultado |
| --- | --- |
| `npm run test` a partir de `frontend` | 33 testes passaram |
| `npm run lint` e `npm run build` a partir de `frontend` | Sucesso, com aviso do Vite sobre o tamanho do pacote Three.js |
| `backend/.venv/Scripts/python.exe -m pytest backend -q` | 80 testes passaram, com aviso de depreciação do TestClient |
| Chromium, compilação local e viewport de 360 px | Escolha por toque, busca sem acento, confirmação pelo teclado e largura sem overflow |

Validação local na branch `developer-login`. A etapa de publicação e o teste com Gemini real permanecem pendentes.


## SkillBridge V3 — S0 e Sprint 1 (20/11/2026)

| Item | Estado | Evidência |
| --- | --- | --- |
| V3-001 · Base Git local | Concluído | `V3` em checkout isolado a partir de `3dff00b`, commit da `main` após a integração da V2. |
| V3-002 · Auditoria e instruções | Concluído | [Auditoria](AUDITORIA_V3.md), [plano mestre](SKILLBRIDGE_V3_PLANO_MESTRE.md) e seis skills nas pastas do Codex. |
| V3-003 · Baseline local | Concluído | 80 testes de backend, 27 de frontend, lint e build aprovados. |
| V3-010 a V3-013 · Sprint 1 | Implementado na V3 local | Contrato, prompt, interface e histórico de 4 e 12 semanas. [Verificações e recuperação](31-v3-trilha-12-semanas.md). |
| V3-004 e V3-020 · Sprint 2 | Implementado na V3 local | Catálogo único e persistência privada de planos e revisões de curso. [Migração e testes](32-v3-persistencia-catalogo.md). |
| V3-021 a V3-023 · Sprint 3 | Implementado na V3 local | Geração estruturada, fila idempotente e validação antes da persistência. [Contrato e testes](33-v3-blueprint-gemini.md). |
| V3-024 · Sprint 4 | Implementado na V3 local | Biblioteca, conteúdo sob demanda e revisões imutáveis. [Contrato e verificações](34-v3-biblioteca-microlicoes.md). |
| V3-030 a V3-032 · Sprint 5 | Implementado na V3 local | Player, três formatos de prática e tentativas persistidas. [Contrato e verificações](35-v3-player-pratica.md). |
| V3-026 · Materiais por tema | Implementado na V3 local | Videoaula, audiolivro, podcast com duas vozes, mapa mental, quiz e simulado. [Guia e verificações](36-v3-materiais-por-tema.md). |
| V3-033 a V3-035 · Sprint 6 | Implementado na V3 local | Avaliação com 80%, competências críticas, reforço e bloqueio no servidor. [Verificações](37-v3-dominio-dashboards-release.md). |
| V3-014 e V3-040 a V3-044 · Sprint 7 | Implementado na V3 local | Painéis do aluno e do curso, tempo registrado, replanejamento, XP e conquistas. [Verificações](37-v3-dominio-dashboards-release.md). |
| V3-025 e V3-050 a V3-054 · Sprint 8 | Entrega técnica local | Painel de qualidade, relatos, privacidade, testes e recuperação verificados localmente. [Preparação de release](37-v3-dominio-dashboards-release.md). |
| Validação real da V3 · 21/11/2026 | Gemini verificado em ensaio sintético | Trilha, curso, prova, painel e materiais com narração real, na cota gratuita. O piloto com voluntários e a publicação seguem pendentes. [Evidências e condição da hospedagem](38-v3-ensaio-gratuito-piloto.md). |
