# SkillBridge V3 — Plano mestre de evolução

**Base de auditoria:** `PedroGiffoni/SkillBridge`, commit `3dff00b0c8f83dc97ff122b75940b2a674770802` (HEAD consultado em 20/11/2026). **Branch planejada:** `V3`. **Estado:** implementação técnica de S0 a S8 na V3 local. Piloto, validação ao vivo e publicação aguardam as condições registradas. [Preparação de release](37-v3-dominio-dashboards-release.md).

## 0. Decisões consolidadas

- Produto: plataforma para estudantes e iniciantes em **tecnologia**; catálogo existente de 72 carreiras distribuídas em 12 áreas.
- Jornada: diagnóstico de lacunas → plano individual de **12 semanas** → curso IA sob demanda → microlições gamificadas → avaliação de domínio → atualização do progresso.
- Domínio: **mínimo 80%** em avaliação somativa; revisão e nova prova em caso de falha.
- IA: Gemini em modalidade gratuita, modelo configurável, orçamento zero para provedores pagos sem autorização; nenhuma simulação apresentada como resultado real.
- Conteúdo: validação automática por schema e regras, conteúdo problemático retido e sinalizado; amostragem humana de controle de qualidade.
- UX: responsiva web, identidade SkillBridge consistente, movimento/microinterações acessíveis, dashboards orientados por dados reais.
- Engenharia: branch `V3`, integração incremental, revisões por fase, preservar histórico das V1/V2.

## 1. Diagnóstico técnico já verificado

| Componente | Evidência no repositório | Ação V3 |
|---|---|---|
| Front | `frontend/src/App.tsx`, `frontend/src/api.ts` React/TypeScript/Vite | Modularizar jornadas e layouts; não substituir sem justificativa |
| Back | `backend/app/main.py`, FastAPI/Pydantic | Extrair serviços por domínio gradualmente |
| IA | `backend/app/gemini.py`, contrato Pydantic | Adicionar pipeline de blueprint/lesson e validação |
| Persistência | SQLite em `backend/app/history.py`, contas/histórico | Adicionar tabelas versionadas; planejar banco durável para produção |
| Autenticação | `backend/app/auth.py`, `accounts.py` | Reutilizar proteção; revisar ambiente publicado |
| Carreiras | `frontend/src/careers.json`, 72 opções, 12 áreas; rótulos no backend | Compartilhar catálogo canônico/versão entre front e back |
| Plano 4 semanas | prompt em `backend/app/main.py`, `Week`/`Guidance` em `schemas.py`, cliente `api.ts` e tela `App.tsx` | Migrar cuidadosamente para 12 semanas |
| Testes | `backend/tests/`, arquivos `*.test.tsx` | Estender e executar regressão em cada fase |

**Riscos reais observados:** contrato atual rejeita semanas fora de 1–4; cliente exige array de quatro; material existente afirma que backend e front já têm histórico/logins, mas produção depende de persistência durável e configuração real. Documentação relata 503 temporário do Gemini em 19/11. Não afirmar operacionalidade em produção sem reteste.

## 2. Arquitetura alvo (monólito modular)

Frontend React: `catalog`, `diagnostic`, `study-plan`, `course`, `lesson-player`, `assessment`, `dashboards`, `account`, `design-system`.

API FastAPI: `catalog`, `diagnostics`, `study_plans`, `course_generation`, `content_validation`, `lessons`, `attempts`, `mastery`, `gamification`, `analytics`, `admin`, `auth`, `observability`.

Persistência: tabelas relacionais com migrações, constraints e índices. SQLite aceitável para desenvolvimento; ambiente publicado precisa de armazenamento persistente. **Não migrar para PostgreSQL automaticamente**; avaliar após prova de conceito e inventário de deploy.

IA: serviço assíncrono ou job persistente → Gemini → JSON estruturado → validação de schema + integridade + segurança + verificação de gabarito → publicar versão imutável ou reter em revisão. API key exclusivamente no servidor. Geração em duas etapas: blueprint das 12 semanas e conteúdo de módulo/lição sob demanda com cache e idempotência.

## 3. Módulos de engenharia previstos

| ID | Módulo | Prioridade | Reaproveitamento / entrega |
|---|---|---|---|
| M01 | Contas, consentimento e perfis | P0 | Reusar autenticação/histórico; revisar durabilidade |
| M02 | Catálogo 72 carreiras / 12 áreas | P0 | Fonte canônica, sinônimos, vínculo com competências |
| M03 | Diagnóstico de competências | P0 | Preservar lacunas e evidência autodeclarada |
| M04 | Planejador de 12 semanas | P0 | Novo contrato versionado e replanejamento |
| M05 | Orquestrador Gemini | P0 | Cotas, job, retry, estados e rastreabilidade |
| M06 | Gerador e validador pedagógico | P0 | Blueprint, módulo, lição, questão e gabarito |
| M07 | Biblioteca versionada de cursos | P0 | Conteúdo, relações, imutabilidade e publicação |
| M08 | Player de microlições | P0 | Mobile-first, navegação, acessibilidade |
| M09 | Motor de exercícios | P0 | Múltipla escolha, preencher lacuna, ordenação |
| M10 | Domínio, reforço e bloqueios | P0 | 80%, evidências, pre-requisitos server-side |
| M11 | Gamificação | P1 | XP idempotente, conquistas, ofensivas opcionais |
| M12 | Dashboards de aluno | P0 | Plano, domínio, calendário, evolução, esforço |
| M13 | Dashboards de produto/admin | P1 | Qualidade IA, geração, custos, progresso agregado |
| M14 | Segurança/observabilidade | P0 | Logs sem PII, taxa de erro, testes, privacidade |

Estes são **módulos lógicos**, não 14 microsserviços. Regras de modularização: dependências apontam para serviços de domínio e interfaces; UI não decide aprovação; API não confia em estado local para desbloqueio.

## 4. Plano de 12 semanas — regras de negócio

**Entrada:** carreira escolhida, 8 competências do questionário Gemini, níveis autodeclarados 0–4, lacunas calculadas no backend, contexto opcional (tempo/recursos), preferências e plano anterior.

**Saída:** `plan_version`, `source_assessment_id`, `weeks[12]` com semana 1…12, objetivo mensurável, competência(s), atividades, carga estimada, entregável verificável, revisão e critérios. Separar plano (agendamento) de curso (conteúdo pedagógico) e de evidência (resultado de exercício).

**Distribuição-base ajustável:** semanas 1–3 fundamentos e lacunas prioritárias; 4 consolidação; 5–7 aprofundamento; 8 revisão intermediária; 9–10 aplicação integrada; 11 reforço; 12 avaliação e próximos passos. A IA ajusta a ordem conforme pré-requisitos e horas disponíveis; o sistema alerta se não couber na disponibilidade.

**Histórico:** manter compatibilidade de leitura dos antigos `weeks[4]`; novas avaliações usam schema V3 de 12 semanas. Nunca reinterpretar registros V1/V2 como 12 semanas nem regravar registros antigos. Replanejamento cria nova versão, preservando semanas concluídas. Semana vencida ≠ competência dominada.

**Domínio:** aprovação somativa >=80%; bloquear se competências críticas não forem cobertas, mesmo com média suficiente; tentativas de treino podem ter dicas, prova somativa preferencialmente sem dicas; erro leva a reforço e avaliação nova. Regras para quantidade mínima de itens e retentativas são configuráveis e devem ser validadas no piloto.

## 5. Cursos e conteúdo IA

Para cada plano, criar **blueprint** de 4–6 módulos pedagógicos por curso-piloto (estimativa, não limite rígido), com 3–8 microlições por módulo conforme complexidade e tempo. Uma semana não é necessariamente um módulo. Cada lição: objetivo, explicação concisa, exemplo, interação, feedback por opção, resumo e links entre competências.

Formatos P0: múltipla escolha, ordenar passos, completar lacunas. Formatos posteriores: editor/execução de código isolado, cenário aberto, projeto guiado e tutor contextual. Correção objetiva determinística, não depender de chamada de IA para cada clique. Validação automática: JSON schema; IDs e referências; grafo de pré-requisitos acíclico; gabarito único válido; coerência do feedback; linguagem adequada; limites de tamanho; conteúdo seguro; publicação/versionamento. Se falhar, não publicar.

## 6. Dashboards — especificação

### D1. Meu desenvolvimento (aluno) [P0]
- KPIs: semanas concluídas de 12, competências com domínio comprovado / competências-alvo, lições concluídas, sequência opcional e carga planejada × registrada.
- **Visual 1:** linha de evolução de domínio por semana, com marcador de evidência; não chamar autoavaliação de domínio.
- **Visual 2:** matriz de competências com estados `não iniciado`, `em estudo`, `em revisão`, `dominado`.
- **Visual 3:** cartões de semanas 1–12 com meta, previsto × realizado e estado; CTA `Retomar lição`.
- **Visual 4:** retrospectiva de erros por competência, usando dados de tentativas sem rotular aluno como incapaz.
- Empty state: `Seu histórico aparecerá depois da primeira lição`; jamais preencher gráficos com números fictícios em produção.

### D2. Meu curso (aluno) [P0]
- Mapa de módulos com relações e bloqueios explicados, barra de progresso de lições, conquistas e últimas tentativas.
- Detalhe do requisito para liberar próximo módulo: nota >=80% + pré-requisitos críticos; CTA de reforço ao reprovar.
- Filtros de módulo, competência e semana; layout em coluna no celular; feedback e microanimações de conquista, com `prefers-reduced-motion` respeitado.

### D3. Qualidade e operações (admin) [P1]
- Total de jobs Gemini por status, falhas 429/503/timeout, tempo de geração, taxa de rejeição pelo validador, conteúdo reportado, custo/tokens quando API fornecer e progresso agregado anonimizado.
- Filtros por período, versão do prompt/modelo e carreira; acesso apenas administrativo; evitar identificar aluno em agregados pequenos.
- Exportação CSV opcional após validar LGPD e finalidade. Sem ranking individual para gestores no MVP.

### Contratos analíticos
- Fonte de verdade: eventos persistidos `lesson_completed`, `attempt_submitted`, `mastery_granted`, `week_plan_revised`, `xp_awarded`, `generation_finished` com chaves idempotentes.
- Agregações server-side, sempre filtradas por usuário autorizado. Timestamps UTC armazenados; exibição no fuso do usuário; unidade de tempo clara.
- Distinguir `self_assessment` de `verified_mastery`; testes conferem se soma de cartões corresponde à API.

## 7. Modelo de dados conceitual

`Account`, `Profile`, `Career`, `Competency`, `Diagnostic`, `Gap`, `StudyPlan`, `StudyPlanVersion`, `StudyWeek`, `Course`, `CourseVersion`, `CourseModule`, `Lesson`, `Exercise`, `ExerciseVersion`, `Attempt`, `MasteryRecord`, `Unlock`, `XPEvent`, `Achievement`, `GenerationJob`, `ContentReview`, `LearningEvent`.

Mínimos: `StudyWeek.ordinal` entre 1–12 para V3; unique(plan_version_id, ordinal); `Attempt` vincula versão da questão e aluno; `MasteryRecord` traz regra e evidências; `GenerationJob` tem fingerprint idempotente; `CourseVersion` imutável depois da publicação; foreign keys; índices por aluno/data/status. Contas e histórico legados preservados por migrações aditivas.

## 8. API de intenção (nomes sujeitos à auditoria)

`GET /api/careers`; `POST /api/study-plans`; `GET /api/study-plans/{id}`; `POST /api/study-plans/{id}/replan`; `POST /api/courses/generate`; `GET /api/courses/jobs/{id}`; `GET /api/courses/{id}`; `GET /api/lessons/{id}`; `POST /api/exercises/{id}/attempts`; `POST /api/modules/{id}/assessment`; `GET /api/me/dashboard`; `GET /api/admin/quality`; `POST /api/content-reports`.

Padrões: autorização por objeto, erros estruturados, idempotency key, validação de payload e schema versionado, paginação, limite de payload, nenhuma exposição de prompts completos ou segredos.

## 9. Plano de entregas incrementais (sprints de desenvolvimento, NÃO semanas do aluno)

| Sprint | Entregável | Critério de aceite / gate |
|---|---|---|
| S0 | Auditoria detalhada e branch `V3` | Branch a partir de `main` atualizado; matriz manter/adaptar/criar; baseline de testes |
| S1 | Planejador 12 semanas compatível com histórico | Novo diagnóstico gera 12; antigo de 4 abre intacto; regressão API/frontend |
| S2 | Persistência de plano e curso + catálogo canônico | Migrações aditivas e testes de acesso entre contas |
| S3 | Gerador de blueprint Gemini + validação automática | JSON inválido rejeitado; retry/idempotência; 429/503 tratados |
| S4 | Conteúdo sob demanda, biblioteca e versionamento | Publicação só após validação; não regenera ao reabrir |
| S5 | Player e três formatos de microlições | Navegação teclado/mobile; progresso persistente; correção consistente |
| S6 | Domínio 80%, reforço, desbloqueio | 79% bloqueia; 80% habilita quando requisitos críticos cumpridos; testes server-side |
| S7 | Dashboard D1 + D2 + gamificação básica | Dados reais, estados vazios, XP sem duplicar, redução de movimento |
| S8 | Dashboard admin, qualidade e piloto | Acesso admin, erros/IA visíveis, teste E2E, revisão de amostra |

**Estimativa inicial:** 9 sprints de 1 semana para protótipo com disponibilidade de desenvolvimento consistente; **não é compromisso de prazo**. Pode estender após baseline de testes, limitações da API e revisão de código.

### Entrega adicional após o Sprint 5

V3-026 acrescenta seis materiais por lição publicada. O aluno pode assistir à videoaula de slides narrados, ouvir o audiolivro ou o podcast com duas vozes, explorar o mapa mental e praticar com quiz ou simulado. O fluxo usa a cota gratuita confirmada, geração sob demanda e reabertura de arquivos salvos. A avaliação de domínio e o desbloqueio são entregues pelo Sprint 6. [Guia de materiais](36-v3-materiais-por-tema.md)

## 10. Backlog por épicos

- **EP-01 Plataforma:** V3-001 branch protegida, V3-002 auditoria, V3-003 baseline CI, V3-004 migração de banco, V3-005 persistência durável.
- **EP-02 Plano:** V3-010 schema 12 semanas, V3-011 prompt Gemini, V3-012 UI 12 semanas, V3-013 histórico 4 semanas, V3-014 replanejamento.
- **EP-03 IA/cursos:** V3-020 catálogo, V3-021 blueprint, V3-022 job, V3-023 validação, V3-024 biblioteca/versionamento, V3-025 relatório de conteúdo, V3-026 materiais por tema.
- **EP-04 Ensino:** V3-030 player, V3-031 tipos de exercício, V3-032 tentativas, V3-033 avaliação, V3-034 reforço, V3-035 bloqueio/autorização.
- **EP-05 Engajamento:** V3-040 XP, V3-041 conquistas, V3-042 dashboard do aluno, V3-043 mapa de curso, V3-044 redução de movimento.
- **EP-06 Operação:** V3-050 dashboard admin, V3-051 métricas de IA, V3-052 testes E2E, V3-053 privacidade, V3-054 piloto e documentação.

**Definition of Done de cada ticket:** critérios observáveis, testes unitários/integrados/E2E conforme risco, estados loading/erro/vazio, mobile 320px+, teclado, logs sem PII, registro de arquivos alterados/comandos/resultados, docs e Kanban atualizados. Nunca afirmar teste não executado.

## 11. Estratégia Git `V3`

1. No repositório local de desenvolvimento (não na cópia de auditoria), verificar `git status`, branch atual, tracking e commits pendentes; preservar alterações locais.
2. Confirmar `main` atualizada; criar `V3` **se ainda não existir**, sem sobrescrever branch homônima. Sugestão de comandos após inspeção: `git switch main`, `git pull --ff-only`, `git switch -c V3`, `git push -u origin V3` (push apenas quando o usuário aprovar publicação da branch).
3. Desenvolver em branches `feature/v3-*` a partir de `V3`, fazer PRs curtos, nunca commit direto na `main`; merge condicionado a testes.
4. Cada sprint deixa documentação e evidências. Migrações têm rollback lógico e backup/teste restaurável antes de tocar dados de produção.
5. V1/V2 continuam acessíveis via tags/commits existentes; não criar tags retroativas sem verificar histórico e autorização.

## 12. Matriz de testes essenciais

| Teste | Resultado esperado |
|---|---|
| Plano novo | 12 semanas ordenadas; lacunas vinculadas; esforço coerente |
| Histórico antigo | Registro de 4 semanas permanece legível/inalterado |
| IA 503/429 | Retry limitado, estado seguro e preservação de respostas |
| Conteúdo inválido | Não publicado; relatório de validação |
| Tentativas | Feedback correto, registro persistente, sem duplicação de XP |
| Nota 79% / 80% | Bloqueio / aprovação, sujeito à cobertura crítica |
| Pré-requisito via URL | Backend nega desbloqueio indevido |
| Dashboard | Indicadores iguais aos registros persistidos, sem mock em produção |
| Duas contas | Uma não vê dados da outra |
| Mobile e teclado | 320px sem overflow, foco e navegação corretos |
| Acessibilidade | Contraste, rótulos, reduced motion |
| Persistência | Estado após refresh, logout/login e reinício do serviço conforme ambiente |

## 13. Riscos e mitigação

1. **Gemini gratuito indisponível:** controle de fila, limites e recuperação; não usar provedor pago ou resultado fictício sem autorização.
2. **SQLite efêmero em hosting:** medir condições, planejar serviço persistente antes de contas reais; migração aditiva com rollback.
3. **IA gerando respostas equivocadas:** validação estruturada + revisão por amostra + denúncia + questões verificáveis.
4. **Escopo grande demais:** primeira fatia vertical limitada a uma carreira e um módulo de curso, depois expandir às 72 opções.
5. **Domínio enganoso:** separar autodeclaração, XP e resultado de avaliação; não prometer competência profissional certificada.
6. **Visual pesado:** motion de interface com render otimizado, Three.js só em cenas opcionais e respeitando reduced motion.
7. **Compatibilidade:** schema versionado e testes com fixture real de quatro semanas.

## 14. Decisões residuais para aprovar antes de S2/S3

- Persistência de produção: serviço/banco durável, limite gratuito e estratégia de migração.
- Idade mínima e privacidade para menores; se houver menores, definir políticas específicas antes de onboarding.
- Número mínimo de itens por avaliação somativa (sugestão piloto: 10) e cobertura mínima por competência crítica.
- Horas semanais máximas e suporte a pausas/feriados.
- Meta e amostra do piloto (sugestão inicial: 10–20 voluntários; sem fingir validação ocorrida).
- Quais carreiras usar para piloto (sugestão: Python back-end, análise de dados, front-end), sem abandonar catálogo de 72.
- Identidade V3: preservar marca atual ou renovar com estudo visual separado.

## 15. Prompt inicial para Codex

> Vamos desenvolver SkillBridge V3 na branch `V3` do repositório `PedroGiffoni/SkillBridge`. Leia `AGENTS.md`, toda a documentação aplicável, este `SKILLBRIDGE_V3_PLANO_MESTRE.md` e as skills V3. Comece com inventário read-only de estado Git, arquitetura, testes, deploy e modelo de dados. Valide a situação de `main`/`V3` antes de criar branch. NÃO altere dados nem reestruture o projeto nesta primeira rodada. Entregue `AUDITORIA_V3.md` com matriz manter/adaptar/criar, risco de perda de histórico, baseline de testes e proposta detalhada do Sprint S1 (migrar plano de 4 para 12 semanas com compatibilidade). Aguarde confirmação para implementação. Respeite os gates e publique apenas após autorização.
