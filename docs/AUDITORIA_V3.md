# Auditoria da SkillBridge V3

> S0 · 20/11/2026 · Base `3dff00b0c8f83dc97ff122b75940b2a674770802` · Planejamento do Sprint 1.

## Decisão de base e estado do Git

A branch local `V3` foi criada e selecionada no checkout separado gerenciado pelo Codex. Ela aponta para a `main` que já recebeu a integração da V2. A referência principal local anterior, `0eb97c2`, está sete commits atrás. `developer-login` em `8b7b165` já é ancestral da base escolhida. O checkout original tem seis arquivos rastreados alterados e 1.505 não rastreados, preservados na pasta original.

Antes da criação, o GitHub listava `main`, `developer-login` e `release/v2-main` (`db1923d`). Não havia `V3` local ou remota nem tags locais. A versão acadêmica anterior ao login permanece localizável em `0eb97c2`. Nenhuma revisão foi publicada durante a auditoria. [Base da V3](https://github.com/PedroGiffoni/skillbridge/commit/3dff00b0c8f83dc97ff122b75940b2a674770802) · [Integração da V2](https://github.com/PedroGiffoni/skillbridge/commit/b8e6eb4) · [Branches no GitHub](https://github.com/PedroGiffoni/skillbridge/branches)

## Fontes e versões anteriores

- Lidos integralmente na Biblioteca do ChatGPT o [plano mestre](SKILLBRIDGE_V3_PLANO_MESTRE.md) e seis modelos. As cópias de auditoria, planejador, cursos Gemini, microlições, dashboards e validação estão em [`.agents/skills/`](../.agents/skills/), cada uma em sua pasta com o `SKILL.md` original.
- Revisados [AGENTS.md](../AGENTS.md), [README.md](../README.md), os 32 documentos Markdown existentes em `docs/` (01–30, decisões e o plano de login) e os cinco arquivos Markdown em [`prompts/`](../prompts/). Os arquivos de `docs/assets/` foram inventariados.
- A V1 acadêmica passou por scaffold, API, integração Gemini e publicação em Vercel/Render. Há evidências documentadas do fluxo publicado com dados sintéticos e quatro semanas em 11 e 17/11. Em 19/11 a correção adicionou retentativa limitada para falha temporária, e a última evidência registrada ainda recebeu 503. [Ativação](16-ativacao-gemini.md) · [Questionário com alternativas](20-alternativas-contextualizadas.md) · [Incidente](29-relatorio-incidente-gemini.md)
- A V2 integrada à `main` preserva o questionário público e pede uma conta para concluir o diagnóstico. Usa sessão de aplicação, Google ou código por e-mail, histórico privado e perfil opcional. A configuração do frontend principal encaminha `/api/*` ao Render principal. O ambiente V2 separado está documentado como ambiente de testes. [Login e ambientes](30-login-historico-perfil.md) · [Proxy Vercel](../frontend/vercel.json)
- O disco efêmero documentado para o Render Free exige prova de durabilidade antes de usar histórico hospedado como fonte de registros permanentes. Login Google/e-mail, chamadas reais ao Gemini e durabilidade de produção ficaram sem nova validação nesta rodada. As tentativas de abrir as URLs públicas pelo serviço de consulta não devolveram um status HTTP, e a consulta local em sandbox encontrou falha de DNS. O piloto acadêmico com pelo menos dez participantes e as métricas correspondentes continuam pendentes. [Publicação registrada](15-publicacao.md) · [Relatório F108](09-relatorio-f108.md)

## Arquitetura e módulos

O monólito já oferece React, TypeScript e Vite no frontend, e FastAPI, Pydantic, SQLite e o SDK `google-genai` no backend. O cálculo de lacunas é determinístico no servidor. A geração recebe dados estruturados e fica no backend, com modelo configurável, erros classificados e limites de tempo e tamanho. O catálogo contém 72 carreiras distintas em 12 áreas. A comparação sensível a maiúsculas entre os rótulos do frontend e os 72 aceitos pela API apresentou zero diferenças.

| Módulo | Ação | Evidência e destino |
| --- | --- | --- |
| M01 Contas, consentimento e perfis | Manter e auditar durabilidade | Sessão e perfil em [auth.py](../backend/app/auth.py), [accounts.py](../backend/app/accounts.py) e [AccountPanels.tsx](../frontend/src/AccountPanels.tsx). |
| M02 Catálogo | Adaptar em S2 | [careers.json](../frontend/src/careers.json), [career_labels.json](../backend/app/career_labels.json). A validação de paridade cobre as duas cópias atuais. Uma fonte canônica fica para S2. |
| M03 Diagnóstico | Manter | Questionário assinado, oito competências, 12 respostas contextuais opcionais e cálculo das lacunas em [main.py](../backend/app/main.py), [tokens.py](../backend/app/tokens.py) e [context.py](../backend/app/context.py). |
| M04 Planejador | Adaptar em S1 | A trilha está acoplada ao diagnóstico. Evoluir [schemas.py](../backend/app/schemas.py), [main.py](../backend/app/main.py), [history.py](../backend/app/history.py), [api.ts](../frontend/src/api.ts) e [App.tsx](../frontend/src/App.tsx). |
| M05 Orquestração Gemini | Adaptar progressivamente | Reutilizar adaptador e erros em [gemini.py](../backend/app/gemini.py) e [config.py](../backend/app/config.py). Jobs e cache do curso entram a partir de S3. |
| M06 Gerador e validação pedagógica | Criar em S3–S4 | A validação atual em [schemas.py](../backend/app/schemas.py) cobre diagnóstico. Blueprint e conteúdo de curso requerem regras próprias. |
| M07 Biblioteca versionada | Criar em S2–S4 | [history.py](../backend/app/history.py) guarda avaliações em JSON. O curso e suas versões terão persistência própria. |
| M08 Player de microlições | Criar em S5 | Reutilizar layout, navegação e estilos existentes em [App.tsx](../frontend/src/App.tsx) e [styles.css](../frontend/src/styles.css). |
| M09 Exercícios | Criar em S5 | O questionário atual tem autodeclaração. Microlições terão correção objetiva e tentativas registradas. [schemas.py](../backend/app/schemas.py) |
| M10 Domínio e desbloqueios | Criar em S6 | Introduzir regra de 80%, cobertura crítica e verificação de pré-requisitos no servidor. Os indicadores atuais de [App.tsx](../frontend/src/App.tsx) exibem autoavaliação. |
| M11 Gamificação | Criar em S7 | XP idempotente e conquistas dependem de eventos de aprendizagem persistidos. |
| M12 Dashboards de aluno | Criar em S7 | A V2 tem histórico e mapa de lacunas. Progresso e domínio precisam de evidência persistida. [AccountPanels.tsx](../frontend/src/AccountPanels.tsx) |
| M13 Dashboard administrativo | Criar em S8 | Adicionar papel autorizado, agregação e indicadores de geração e revisão. [auth.py](../backend/app/auth.py) |
| M14 Segurança e observabilidade | Manter e ampliar | Reutilizar limites, erros sanitizados e isolamento por conta. Ampliar com telemetria mínima de geração e regressão por objeto. [main.py](../backend/app/main.py) · [history.py](../backend/app/history.py) |

Os estudos de personagens chamados V3/V4 na documentação anterior são candidatos visuais e têm numeração independente da evolução do produto.

## Sprint 1 — Trilhas de 12 semanas com histórico legível

**Aceite.** Um diagnóstico novo recebe uma trilha com 12 semanas válidas. Um resultado anterior de quatro semanas abre com o conteúdo, a ordem, o titular e as datas originais, inclusive após reinício da API. O reenvio da mesma submissão legada retorna o resultado salvo, mantendo a idempotência.

| Ordem | Trabalho | Critério verificável |
| --- | --- | --- |
| 1 · V3-010 e V3-013 | Definir contrato versionado de gravação e ler as duas versões no backend e frontend. | O SQLite aceita os resultados juntos em `assessment_history.result`. Um objeto antigo sem marcador entra como legado somente se validar como quatro semanas de 1 a 4. Um resultado novo tem versão explícita, referência à avaliação, 12 semanas de 1 a 12 e os campos pedagógicos obrigatórios. |
| 2 · V3-011 | Ajustar prompt e validação do `POST /api/assessment`. | Cada semana tem objetivo, competências referenciadas, atividades, carga estimada, entregável e revisão. O servidor valida ordem, unicidade, cobertura das lacunas priorizadas, referências a competências conhecidas, dependências acíclicas quando utilizadas, limites e disponibilidade. Se a carga informada for insuficiente, a orientação sinaliza a restrição e prioriza o escopo. |
| 3 · V3-012 | Adaptar o fluxo de diagnóstico, trilha e abertura do histórico. | A duração vem do contrato recebido. A V3 mostra três blocos de quatro, com semanas 10–12 sem zero extra. A pergunta contextual sobre objetivo muda em ambos os catálogos mantendo IDs e opções se a semântica continuar igual. Erro e nova tentativa preservam as respostas. Verificar teclado e 320 px. |
| 4 · Integração | Testar convivência e falhas no mesmo SQLite temporário. | Uma fixture legada sem marcador, gerada pelo código da V2 com dados sintéticos, permanece idêntica no banco. Abrir as duas versões após reiniciar, testar replay e concorrência sem gravação duplicada, isolamento entre contas, exclusão existente, 11/13 semanas, duplicação, ordem inválida, lacunas sem vínculo, carga incompatível, payload truncado e 429/503/timeout. |

**Primeiro PR.** Implementar primeiro os leitores compatíveis, contratos e fixture histórica com testes. Habilitar a gravação de 12 semanas somente após validar o cliente que vai ler os resultados. O servidor controla a versão e a referência à avaliação. O modelo recebe apenas o contexto permitido, competências e lacunas. A saída maior deve caber nos limites de 6.000 tokens e 24.000 bytes do adaptador. [Restrições Gemini](../backend/app/gemini.py#L75) · [Validação atual](../backend/app/schemas.py#L142) · [Histórico e replay](../backend/app/history.py#L75) · [Validador TypeScript](../frontend/src/api.ts#L29)

**Preservação e rollback.** O campo `result` já armazena JSON, portanto a proposta de S1 dispensa DDL e backfill. Preservar o fingerprint e a transação de reserva. Abrir históricos consulta o JSON salvo sem chamar o Gemini. Após gravar registros de 12 semanas, o alvo de rollback deve manter a leitura dos dois formatos e permitir desligar a geração V3. Voltar diretamente a um leitor exclusivamente de quatro semanas quebraria a abertura dos novos registros. Antes de qualquer implantação com dados, verificar backup consistente do SQLite, restauração em cópia e configuração do armazenamento. [Tabela e consulta por titular](../backend/app/history.py#L53)

**Fora de S1.** O replanejamento V3-014 depende de versões persistidas e de um modelo de semanas concluídas. O plano para o próximo incremento é criar uma versão sucessora e carregar a relação com as semanas concluídas. S2 cobre a persistência própria e o catálogo canônico. Cursos sob demanda, microlições, prova de 80%, XP e dashboards seguem os gates S3–S8.

## Testes e arquivos alterados

Baseline executado no checkout da `V3` a partir de `3dff00b`, com dependências locais e SQLite temporário. Nenhum teste acionou Gemini, login externo ou dados de produção.

| Comando | Resultado |
| --- | --- |
| `python -B -m pytest -p no:cacheprovider -q` em `backend`, usando o Python do ambiente virtual existente | 80 passaram. Aviso de depreciação do TestClient em Starlette. |
| `npm run test` em `frontend` | 27 passaram em 5 arquivos. |
| `npm run lint` em `frontend` | Passou. |
| `npm run build` em `frontend` | Passou. Vite registrou um chunk de Three.js de 753,31 kB. |

O checkout antigo tinha dois arquivos locais de testes dos personagens, que explicam os 33 testes de frontend da primeira verificação. Os 27 acima são os testes do commit que serve de base à V3.

Além do plano mestre e deste relatório, o S0 adiciona seis `SKILL.md` em `.agents/skills/` e registra o avanço em [decisoes.md](decisoes.md) e no [Kanban](08-sprints-kanban.md). O Sprint 1 aguarda validação. A recuperação do Gemini no ambiente público, a autenticação real e a durabilidade do histórico hospedado continuam sem nova verificação.
