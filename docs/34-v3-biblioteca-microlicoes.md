# Sprint 4 da SkillBridge V3 — biblioteca e lições sob demanda

## Fluxo da conta

Abra um diagnóstico V3 no histórico, siga para a trilha e escolha **Abrir curso da trilha**. O aplicativo consulta o job existente. Para preparar um blueprint novo, a pessoa autoriza o envio dos dados pedagógicos ao Gemini. Quando o rascunho passar pela validação, **Salvar na biblioteca** cria uma revisão publicada para a própria conta.

Em **Meus cursos**, selecione um curso e uma lição. Uma lição que ainda não tem conteúdo pede consentimento antes de entrar na fila. Uma lição salva abre diretamente pela leitura da revisão persistida. A tela apresenta o conteúdo e a proposta de prática. A interação, a correção e o registro de progresso ficam para o Sprint 5.

## API e armazenamento

| Rota privada | Contrato |
| --- | --- |
| `GET /api/study-plans/{id}/course-job` | Consulta o blueprint existente para a trilha. Retorna `job` nulo quando nenhuma geração foi solicitada. |
| `GET /api/courses` | Lista a última revisão publicada de cada curso do titular, com `offset` e `limit`. |
| `POST /api/courses/{id}/publish` | Recebe `draft_revision`. Publica uma revisão separada se o rascunho pertencer a um job de blueprint validado. Reenviar retorna a mesma revisão publicada. |
| `GET /api/courses/{id}/lessons?course_revision=2` | Lista os esboços e os IDs de job e lição salvos para a revisão solicitada. |
| `POST /api/courses/{id}/lessons/{outline_id}/generate` | Recebe `course_revision`, `consent: true` e `retry_attempt` opcional. Reutiliza o mesmo job para a mesma lição e revisão. |
| `GET /api/courses/jobs/{id}` | Consulta o andamento. Para uma lição pronta, o campo `lesson` contém a projeção de leitura. |
| `GET /api/lessons/{id}` | Lê a revisão salva da lição, com texto, exemplo, resumo e proposta de prática. |

A migração SQLite aditiva `learning_migrations.version=3` cria o vínculo entre a revisão de rascunho e a versão publicada, registra as lições por revisão de curso e acrescenta a identidade da lição à fila. Triggers impedem atualizações de revisões publicadas. A exclusão do diagnóstico pelo titular remove os registros ligados por cascata. As rotas devolvem o mesmo `404` para acesso indevido e IDs ausentes.

O worker escolhe o schema de acordo com o formato do esboço salvo. A múltipla escolha exige um ID correto válido e opções distintas. A ordenação exige uma permutação dos passos, diferente da ordem apresentada. A lacuna exige um marcador, uma resposta e feedback de acerto e erro. Os textos passam pelo limite de tamanho e pelo filtro de links, HTML e endereços de e-mail. A saída inválida fica em `needs_review` e não cria uma lição publicada. Os IDs das opções e dos passos são substituídos por identificadores do servidor. O gabarito e o feedback permanecem na revisão privada para a correção posterior.

A conclusão grava a lição e o estado `ready` na mesma transação. A identidade da lição publicada independe da configuração atual do modelo. Os jobs de lição usam a série de prompt `1001`, fora do intervalo usado pelo worker de blueprint do Sprint 3. Um rollback pode conservar as tabelas aditivas. A exibição e o processamento das lições exigem um worker do Sprint 4 ou posterior. Antes de operar com dados reais, verificar backup, restauração e durabilidade do SQLite hospedado.

## Verificações locais

| Comando ou cenário | Resultado |
| --- | --- |
| `python -B -m pytest -p no:cacheprovider -q` em `backend` | 122 testes passaram. |
| `npm run test` em `frontend` | 37 testes passaram. |
| `npm run lint`, `npm run build` e `git diff --check` | Passaram. |
| Edge a 320 px, com o frontend compilado e a API local | Pelo teclado, gerei o blueprint, salvei o curso, preparei uma lição e reabri pela biblioteca depois de recarregar. O foco voltou ao título da lição e não houve rolagem horizontal. |
| Cache, gabarito e integridade | Os testes conferiram acesso entre contas, reabertura com Gemini desativado e outro modelo configurado, rejeição de gabarito inválido, três formatos, imutabilidade e exclusão em cascata. |

As verificações usaram conta sintética, SQLite temporário e Gemini simulado. A validação com o modelo real permanece pendente. Persistem os avisos preexistentes do TestClient e do tamanho do chunk Three.js.

## Arquivos alterados

- Backend: `backend/app/library.py`, `lesson_content.py`, `blueprint_jobs.py` e `history.py`.
- Frontend: `frontend/src/App.tsx`, `CourseLibrary.tsx`, `course-api.ts`, `account-api.ts` e `account.css`.
- Testes: `backend/tests/test_library.py`, `test_learning.py`, `test_course_generation.py` e `frontend/src/CourseLibrary.test.tsx`.
- Documentação: `README.md`, `backend/README.md`, `docs/08-sprints-kanban.md`, `docs/decisoes.md` e este registro.
