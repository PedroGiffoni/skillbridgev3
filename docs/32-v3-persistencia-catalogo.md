# Sprint 2 da SkillBridge V3 — persistência e catálogo

O Sprint 2 entrega um catálogo canônico público e a persistência privada de avaliações V3, planos, semanas e revisões de curso no SQLite da aplicação.

1. Verificar que o catálogo completo tem uma fonte versionada e que seus rótulos são os mesmos aceitos pelo questionário. Preservar a busca local, os IDs e os rascunhos.
2. Criar tabelas aditivas. Persistir o plano inicial na mesma transação que finaliza o diagnóstico. Materializar planos V3 anteriores durante a migração e conservar os resultados originais no histórico.
3. Verificar o acesso ao plano e a cursos publicados com duas contas. Persistir revisões de curso usando a identidade da revisão do plano. Registrar e testar a exclusão em cascata pelo histórico.
4. Executar as suítes e registrar os resultados. A geração de curso pelo Gemini e o replanejamento com progresso ficam nos próximos sprints.

## Catálogo canônico

O React e o FastAPI leem `frontend/src/careers.json`. A versão `1` preserva as 12 áreas, 72 carreiras e 350 entradas de sinônimos. O React inclui os dados no bundle para a busca local. O FastAPI expõe o mesmo documento em `GET /api/careers` e deriva dele os rótulos aceitos em `POST /api/questionnaire`. IDs, rótulos, descrições e sinônimos são iguais aos do catálogo anterior. O deploy do backend V3 deve incluir o checkout integral do repositório para que o arquivo esteja disponível.

## Persistência privada

A primeira conexão do serviço de histórico aplica a migração interna `learning_migrations.version=1` no SQLite de `AUTH_DB_PATH`. A criação das tabelas e a cópia dos diagnósticos V3 válidos ocorrem em uma transação. Os resultados originais continuam em `assessment_history`. Uma avaliação V3 gravada por uma versão anterior da API após a migração pode ser materializada no primeiro acesso do titular.

- `study_plans` usa o ID do diagnóstico. `study_plan_versions` guarda revisões, começando em `1`. O campo `plan_version: 3` ainda identifica o formato do resultado da avaliação.
- `study_weeks` guarda as semanas em ordem com ordinal único de 1 a 12 por revisão. Finalizar um diagnóstico novo grava o histórico, a revisão e as 12 semanas em uma única transação.
- `courses` vincula o curso à revisão efetiva do plano. `course_versions` guarda o conteúdo por revisão. A escrita é interna ao backend. Um novo rascunho não substitui a última revisão publicada na leitura.
- `GET /api/study-plans/{id}` abre a revisão atual do plano do titular. `GET /api/courses/{id}` lê a última revisão publicada do curso do titular. Ambas exigem sessão e devolvem o mesmo `404` para um ID inexistente ou pertencente a outra conta.
- Excluir um diagnóstico pela rota existente remove os planos e cursos vinculados por chaves estrangeiras. O histórico de quatro semanas continua acessível pela rota atual.

As tabelas são aditivas. Um rollback de código pode conservá-las e continuar lendo os resultados pelo histórico. Antes de operar em produção, verificar o armazenamento persistente e ensaiar backup e restauração em cópia. A geração de blueprints pelo Gemini fica no Sprint 3. A liberação de conteúdo fica no Sprint 4.

## Verificações locais

| Comando ou cenário | Resultado |
| --- | --- |
| `python -B -m pytest -p no:cacheprovider -q` em `backend` | 102 passaram. |
| `npm run test` em `frontend` | 35 passaram. |
| `npm run lint` e `npm run build` em `frontend` | Passaram. |
| Comparação do catálogo com o commit de base | Os 72 IDs, rótulos, descrições e aliases foram preservados. |
| Migração, falha simulada, reinício e duas contas | Os testes confirmaram preservação do JSON original, salvamento atômico, recuperação após falha, acesso restrito, revisões de curso e exclusão em cascata. |

O backend manteve o aviso de depreciação do TestClient. O build manteve o aviso de tamanho do chunk de Three.js. Os testes usaram SQLite temporário e Gemini simulado. O Sprint 2 foi implementado localmente na branch `V3`.

## Arquivos alterados

- Backend: `backend/app/catalog.py`, `learning.py`, `history.py` e `main.py`. A lista redundante `backend/app/career_labels.json` foi substituída pela fonte canônica.
- Frontend: `frontend/src/careers.json`, `App.tsx`, `CareerPicker.tsx` e `CareerPicker.test.tsx`.
- Testes: `backend/tests/test_api.py` e `test_learning.py`.
- Documentação: `README.md`, `backend/README.md`, `docs/08-sprints-kanban.md`, `docs/decisoes.md` e este registro.
