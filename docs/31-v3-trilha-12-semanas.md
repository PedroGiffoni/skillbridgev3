# Sprint 1 da SkillBridge V3 — trilha de estudos

A versão da aplicação na branch `V3` gera 12 semanas para novos diagnósticos e abre avaliações anteriores com quatro semanas. O calendário orienta a prática com base na autoavaliação. O domínio de competências será medido em um sprint posterior.

## Contrato de avaliação

Os endpoints `POST /api/assessment` e `GET /api/history/{id}` continuam autenticados. O resultado do POST e o campo `assessment` do detalhe de histórico usam estes formatos.

| Campo | Resultado anterior | Resultado V3 |
| --- | --- | --- |
| `plan_version` | Ausente | Inteiro `3`, atribuído pela API |
| `source_assessment_id` | Ausente | ID da avaliação no histórico, atribuído pela API |
| `weeks` | Quatro semanas consecutivas | Doze semanas consecutivas |
| Cada semana | Número, título, objetivo, ações e entregável | Campos anteriores, `competency_ids`, `estimated_minutes`, `review` e `prerequisite_weeks` |

A API exige IDs de competências presentes no diagnóstico, cobertura de até três lacunas prioritárias e pré-requisitos únicos que apontem para semanas anteriores. O tempo é registrado em minutos e limitado a 240 por semana e ao menor teto informado na autoavaliação, quando houver. A interface agrupa a V3 em três blocos de quatro e apresenta o tempo como estimativa. Restrições e suposições sobre a carga aparecem nas limitações da orientação.

## Histórico e recuperação

O resultado continua armazenado como JSON em `assessment_history.result`. A mesma definição de leitura é usada ao consultar o histórico privado ou repetir uma submissão já concluída. Os bytes dos registros de quatro semanas permanecem no banco. A migração do contrato dispensa alterações de schema SQLite e atualização retroativa dos dados. Resultados inválidos ou interrompidos liberam a reserva para que a avaliação possa ser retomada.

Para preparar a publicação, valide a restauração de um backup consistente do SQLite em uma cópia e confirme que a hospedagem preserva o arquivo entre reinícios. Publique primeiro um cliente que leia ambos os formatos. Se for preciso desativar a geração de 12 semanas, defina `STUDY_PLAN_V3_ENABLED=false` no backend e reinicie o serviço. A configuração retorna a geração de quatro semanas e mantém ambos os leitores. Uma versão antiga da aplicação que só reconheça quatro semanas não é um alvo de rollback depois que a V3 começar a gravar resultados.

## Verificação local

| Comando ou cenário | Resultado |
| --- | --- |
| `python -B -m pytest -p no:cacheprovider -q` em `backend` | 96 testes passaram. O TestClient emitiu um aviso de depreciação do Starlette/httpx. |
| `npm run test` em `frontend` | 35 testes passaram em cinco arquivos. |
| `npm run lint` e `npm run build` em `frontend` | Ambos passaram. O build manteve o aviso do chunk Three.js acima de 500 kB. |
| Edge com viewport de 320 px, frontend compilado e API local | A conta sintética reabriu as duas trilhas pelo teclado. A V3 mostrou 12 semanas em três blocos e a trilha legada manteve as quatro. O foco chegou ao título e ambas ficaram sem rolagem horizontal após o ajuste do cabeçalho. |
| Fixture legada | `backend/tests/fixtures/assessment-v2.json` foi gerada com o código do commit `3dff00b`, Gemini simulado e SQLite temporário. O teste confirmou a preservação dos bytes, data e titular após ler, reenviar, gerar uma trilha V3 e reiniciar com a opção de recuperação. |

As verificações usaram contas e respostas sintéticas. Gemini real, login externo e durabilidade do SQLite hospedado permanecem pendentes. A implementação e os testes ocorreram na branch local `V3`, sem push ou deploy.

## Arquivos alterados

- Backend: `backend/app/config.py`, `context.py`, `history.py`, `main.py` e `schemas.py`. A configuração de recuperação está em `.env.example` e `backend/.env.example`.
- Frontend: `frontend/index.html`, `frontend/src/App.tsx`, `StudyPlan.tsx`, `account.css`, `api.ts`, `context.ts` e `styles.css`.
- Testes: `backend/tests/test_api.py`, `test_history.py`, `test_study_plan.py` e `fixtures/assessment-v2.json`. No frontend, `frontend/src/api.test.ts`, `integration.test.tsx` e `test-fixtures.ts`.
- Documentação: `README.md`, `backend/README.md`, [Kanban](08-sprints-kanban.md), [decisões](decisoes.md) e este registro.

O [plano mestre](SKILLBRIDGE_V3_PLANO_MESTRE.md) reserva o replanejamento e a persistência de versões de plano e curso para os próximos sprints.
