# Sprint 5 da SkillBridge V3 — player e prática

## Praticar na biblioteca

Abra **Meus cursos**, selecione um curso e escolha uma lição com conteúdo salvo. O player apresenta objetivo, explicação, exemplo e exercício. Ao corrigir, exibe feedback e resumo e permite uma nova tentativa. Use **Lição anterior** e **Próxima lição** para navegar.

| Formato | Interação | Critério de acerto |
| --- | --- | --- |
| Múltipla escolha | Selecione uma alternativa. | O ID escolhido corresponde ao gabarito. A API devolve o feedback da alternativa escolhida. |
| Ordenação | Use **Subir** e **Descer** para organizar os passos. | Todos os passos estão na posição esperada. Quando a sequência difere, o feedback indica quantos passos estão na posição correta. |
| Lacuna | Digite até 80 caracteres. | A API compara a resposta e o gabarito depois de normalizar Unicode, espaços e maiúsculas. Acentos continuam significativos. |

A prática é concluída com o primeiro acerto, mesmo quando há dica. Erros em novas tentativas não apagam essa conclusão. Ao voltar à lição, o player recupera o resultado da tentativa mais recente e o número de tentativas. Avaliação somativa de 80% e desbloqueio por domínio pertencem ao Sprint 6.

## API e migração

| Rota privada | Contrato |
| --- | --- |
| `POST /api/exercises/{lesson_id}/hint` | Recebe `attempt_id` e retorna uma sugestão genérica com recibo assinado para a conta, a revisão da lição e a tentativa. A emissão não cria linha no banco. |
| `POST /api/exercises/{lesson_id}/attempts` | Recebe `attempt_id`, `answer` e um `hint_receipt` opcional. Corrige com o gabarito da revisão publicada e devolve `attempt` e `practice`. |
| `GET /api/lessons/{id}` | Acrescenta `practice` com total, conclusão e última tentativa. O mesmo campo aparece na projeção da lição pronta de um job. |
| `GET /api/courses/{id}/lessons?course_revision=2` | Acrescenta `practice_completed` em cada item da revisão. |

A migração aditiva `learning_migrations.version=4` cria `practice_attempts`, um índice de leitura e um trigger de imutabilidade. Nenhuma tabela existente precisa ser reconstruída. Contas, avaliações de quatro semanas, planos e lições previamente salvas continuam legíveis. Em caso de rollback do código, mantenha a tabela para recuperar as tentativas quando voltar ao Sprint 5. A exclusão de uma avaliação pelo titular também remove suas tentativas, em cascata.

A revisão da lição e a conta delimitam cada tentativa. O servidor registra resultado, feedback, horário e indicador de dica. A resposta fica representada por uma assinatura HMAC para reconhecer reenvios. O texto digitado fica fora da tabela e a correção ocorre localmente. O mesmo ID e resposta devolvem a correção original, inclusive em reenvios concorrentes. Reutilizar o ID com outra resposta retorna `409`. Mantenha `AUTH_OTP_SECRET` estável entre reinícios. Se for rotacionado, o progresso gravado continua acessível, mas recibos anteriores e reenvios com o mesmo ID podem exigir uma nova tentativa.

## Verificações locais

| Comando ou cenário | Resultado |
| --- | --- |
| `python -B -m pytest -p no:cacheprovider -q` em `backend` | 125 testes passaram. Incluem gabaritos, normalização, titularidade, concorrência, reinício e cascata. |
| `npm run test` em `frontend` | 41 testes passaram. Incluem os três formatos, teclado, reenvio com o mesmo ID, navegação e reabertura. |
| `npm run lint`, `npm run build` e `git diff --check` | Passaram. |
| Edge com viewport de 320 px | Corrigi os três formatos por teclado, confirmei o foco na dica, no botão após reordenar e no feedback. O curso mostrou 3 de 12 práticas concluídas, sem rolagem horizontal. A contagem, a última correção e o uso da dica reapareceram ao recarregar. |

A validação usou conta sintética, SQLite temporário e um simulador do Gemini. A validação do fluxo de geração com Gemini real está pendente. Permanecem os avisos de depreciação do TestClient e de tamanho do chunk Three.js.

## Arquivos alterados no Sprint 5

- Backend: `backend/app/practice.py`, `history.py`, `library.py`, `lesson_content.py` e `main.py`.
- Frontend: `frontend/src/LessonPlayer.tsx`, `CourseLibrary.tsx`, `course-api.ts` e `account.css`.
- Testes: `backend/tests/test_practice.py`, `test_learning.py`, `test_library.py`, `frontend/src/LessonPlayer.test.tsx` e `CourseLibrary.test.tsx`.
- Documentação: `README.md`, `backend/README.md`, `docs/08-sprints-kanban.md`, `docs/decisoes.md` e este registro.
