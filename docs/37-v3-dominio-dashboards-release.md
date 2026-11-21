# SkillBridge V3 — Domínio, progresso e preparação da entrega

## Sprint 6 — Avaliação e reforço

Em **Meus cursos**, abra um curso e expanda **Avaliações de módulo**. O servidor libera os módulos cujos pré-requisitos já têm aprovação registrada. Os títulos de módulos bloqueados aparecem com os requisitos pendentes. Tentativas de abrir diretamente a geração, uma lição salva, sua prática, seus materiais ou sua prova verificam titularidade e pré-requisitos no servidor.

A prova contém dez questões objetivas, todas sem dica e com gabarito privado. A aprovação exige nota de pelo menos **80%** e pelo menos um acerto em cada competência do módulo. Na V3, todas as competências declaradas na estrutura do módulo são críticas. A decisão compara contagens inteiras antes de exibir a porcentagem. A aprovação vale para a revisão publicada do curso e fica vinculada à prova entregue.

A preparação envia ao Gemini apenas objetivos, tópicos, conteúdo pedagógico disponível, competências e enunciados recentes para variar a prova. A correção independe do provedor. A reprovação exibe competências a revisar e links para as lições de reforço. Uma nova prova tem itens distintos. Reservas concorrentes reaproveitam a prova em preparação, e repetir o envio da mesma prova com as mesmas respostas devolve o resultado salvo.

## Sprint 7 — Painéis, XP e replanejamento

A área **Meu desenvolvimento** permite escolher um curso, ver o progresso, retomar a próxima lição e consultar o mapa dos módulos. Há filtros por estado, semana e competência. A matriz distingue competências em estudo, em revisão e aprovadas por evidência. Ela mostra acertos de provas registradas.

Uma semana é concluída quando todas as suas práticas foram concluídas. A carga planejada vem da revisão atual da trilha. O aluno registra manualmente o total de minutos que estudou naquela semana. O gráfico de domínio usa datas reais de aprovação, acumula competências distintas desde o início da trilha e inclui aprovações posteriores na semana 12. Os valores também estão disponíveis em texto.

O registro privado de XP concede 10 pontos no primeiro acerto de cada lição e 50 na primeira aprovação de cada módulo em uma revisão. Uma transação grava a evidência e o evento de XP. Repetir uma prática ou reenviar a mesma prova não duplica a pontuação. Três conquistas indicam a primeira prática, semana e módulo concluídos.

**Replanejar semanas em aberto** cria uma revisão com o novo tempo estimado. Os objetivos e as atividades são preservados. Semanas concluídas mantêm seu planejamento e as evidências continuam no curso em que foram obtidas. O diagnóstico que originou a trilha permanece legível com o JSON original.

## Sprint 8 — Qualidade, privacidade e operação

A opção **Relatar problema nesta lição** registra uma categoria de problema, com deduplicação por conta, lição e categoria. Não há campo de texto livre. A área **Qualidade e operações** está disponível para contas autenticadas com e-mail verificado incluído em `AUTH_ADMIN_EMAILS`. O padrão é uma lista vazia. A API valida a permissão em cada consulta de métricas.

O painel agrega o estado atual dos jobs guardados de cursos, lições e materiais. Exibe latência e tokens quando medidos, rejeições, cota atingida, falhas temporárias e o HTTP 503 quando identificado pelo provedor nos registros novos. Registros anteriores podem reunir indisponibilidade sem código específico. Indicadores de progresso e relatos ocultam grupos com menos de cinco contas distintas. Métricas ausentes aparecem como indisponíveis e o painel não estima cobrança.

| API privada | Uso |
| --- | --- |
| `GET/POST /api/courses/{id}/modules/{module_id}/assessment` | Consulta ou prepara a avaliação de uma revisão publicada. |
| `POST /api/courses/{id}/modules/{module_id}/assessment/submit` | Corrige e persiste o resultado. |
| `GET /api/me/dashboard` | Lê progresso, competências, XP, mapa e retomada. Aceita `course_id`. |
| `POST /api/me/dashboard/time` | Salva o total de minutos informado para uma semana. |
| `POST /api/study-plans/{id}/replan` | Acrescenta uma revisão para as semanas em aberto. |
| `POST /api/content-reports` | Registra um relato categorizado de uma lição acessível ao titular. |
| `GET /api/admin/access` e `GET /api/admin/quality` | Descoberta de acesso e consulta administrativa agregada. |

## Verificação local

- A suíte de backend usa `python -B -m pytest -p no:cacheprovider -q` em `backend`. 143 testes passaram. A suíte cobre o limiar 79%/80%, cobertura crítica, provas distintas, concorrência, isolamento, geração rejeitada, migração, relatórios, XP idempotente e reabertura.
- O teste integrado percorre questionário, diagnóstico de 12 semanas, curso, aprovação, painel, registro de minutos e replanejamento. Ele restaura uma cópia feita com a API de backup do SQLite e verifica o painel, a aprovação, `PRAGMA integrity_check` e `PRAGMA foreign_key_check`.
- A suíte de frontend usa `npm run test`, `npm run lint` e `npm run build` em `frontend`. 48 testes passaram, assim como lint e build.
- No Edge com uma conta sintética, percorri pelo teclado uma prova de 80% com cobertura crítica insuficiente e uma nova prova de 80% que liberou o módulo seguinte. Conferi 50 XP pela aprovação, replanejamento, registro de minutos, retomada com foco na lição, relato e tela administrativa. O painel ficou sem rolagem horizontal em 320, 768 e 1280 px.
- As chamadas ao Gemini e o e-mail foram simulados, com SQLite temporário. O ensaio é evidência técnica local. A inspeção com `git diff --check` passou. Permaneceram os avisos de depreciação do TestClient e de tamanho do chunk Three.js.

## Migração, recuperação e piloto

As migrações 6 a 9 são aditivas. Elas criam provas, aprovações, registro de tempo, registro de XP e relatos, e acrescentam colunas de telemetria. A migração 7 aproveita as primeiras práticas corretas já persistidas, sem modificar as tentativas. O backup deve incluir a base SQLite inteira e a configuração de autenticação deve ser mantida no servidor. Antes de liberar contas reais, valide o volume persistente da hospedagem, restaure um backup em ambiente separado e confira os totais e o histórico. Em caso de rollback de código, preserve o banco e use uma versão capaz de ler trilhas de quatro e doze semanas.

O piloto usa voluntários consentidos com códigos anônimos e a amostra prevista no protocolo F108. Acrescente ao roteiro a navegação no curso, o reforço, a retomada pelo painel e os materiais multimodais. Revise uma amostra de provas e materiais reais quanto a gabarito, clareza, pronúncia e distinção de vozes. Registre somente medidas observadas. [Protocolo de métricas e validação](07-metricas-validacao.md)

O ensaio posterior confirmou a geração e a voz na cota gratuita com dados sintéticos. O Render Free existente não aceita disco persistente. Login e persistência na hospedagem, piloto com usuários e publicação continuam pendentes. [Ensaio real e roteiro do piloto](38-v3-ensaio-gratuito-piloto.md)

## Arquivos alterados

- Backend. `backend/app/mastery.py`, `module_access.py`, `learning_dashboard.py`, `quality.py`, `library.py`, `practice.py`, `blueprint_jobs.py`, `theme_materials.py`, `history.py`, `main.py` e `config.py`.
- Frontend. `frontend/src/App.tsx`, `CourseLibrary.tsx`, `course-api.ts`, `ModuleAssessment.tsx`, `LearningDashboard.tsx`, `useLearningRequest.ts`, `QualityDashboard.tsx`, `quality-api.ts`, `learning-progress.css`, `quality.css` e `account.css`.
- Testes. `backend/tests/test_mastery.py`, `test_learning_dashboard.py`, `test_learning.py`, `test_quality.py` e `frontend/src/LearningViews.test.tsx`.
- Configuração e documentação. `.env.example`, `backend/.env.example`, os READMEs, o Kanban, o plano mestre e o registro de decisões.
