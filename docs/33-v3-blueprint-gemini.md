# Sprint 3 da SkillBridge V3 — geração de blueprint

1. Fixar o contrato de módulos e microlições e testar cobertura das 12 semanas, IDs, competências e dependências.
2. Registrar solicitações no SQLite, limitar chamadas e salvar um rascunho validado na mesma transação que conclui o job.
3. Testar reenvio, reinício, acesso entre contas e falhas do Gemini com dados sintéticos.

## Usar pela API privada

O titular de um plano V3 pode chamar `POST /api/courses/generate` com os campos `plan_id` e `consent: true`. O cliente deve informar que o Gemini receberá a carreira e os dados pedagógicos do plano antes de solicitar esse consentimento. A rota devolve `202` com o ID do job. `GET /api/courses/jobs/{id}` consulta o andamento. As duas rotas exigem sessão e só dão acesso ao titular. O rascunho aparece em `draft` no estado `ready`. A rota de cursos publicados continua reservada a revisões aprovadas.

| Estado | Significado |
| --- | --- |
| `queued` | O job está persistido e aguarda o worker. |
| `running` | Um worker reservou a tentativa por tempo limitado. |
| `ready` | O blueprint passou pela validação e foi salvo como revisão de rascunho. |
| `failed` | A geração foi interrompida ou falhou. O campo `error.code` identifica o motivo. |
| `needs_review` | O formato ou conteúdo falhou na validação. A resposta bruta é descartada. |

Repetir a solicitação para o mesmo plano, revisão, modelo e versões de prompt e schema retorna o mesmo job. Se `error.retryable` estiver ativo, envie `retry_attempt` igual a `attempts` da falha observada, junto com o plano e o consentimento. Reenviar o mesmo número não consome uma tentativa adicional. O limite é de três execuções do worker por job. Um HTTP 429 do provedor aguarda 60 segundos antes de nova tentativa explícita. O adaptador já limita a repetição automática de 503 e outras falhas temporárias a uma, dentro do prazo da chamada. A configuração local incompleta é rejeitada com HTTP 503 antes de enfileirar um job novo.

## Contrato e armazenamento

O blueprint de schema `1` organiza as 12 semanas em módulos e esboços de microlições. O contrato aceita de três a oito módulos, com três a oito esboços por módulo, e o prompt prefere quatro a seis módulos. Cada esboço tem semana, objetivo e competências previstas no plano. A validação confere IDs, cobertura das semanas e competências, dependências entre módulos concluídos e tamanho dos campos. O esboço indica um formato de prática do P0. Enunciados completos, gabaritos, publicação e player pertencem aos sprints seguintes.

A migração aditiva `learning_migrations.version=2` cria `generation_jobs`. O job referencia uma revisão específica do plano e a revisão do curso criada ao concluir. O worker retoma jobs pendentes e concessões expiradas do modelo e das versões que ele suporta. Um job de outro modelo permanece consultável pela conta e uma nova solicitação com a configuração ativa recebe a sua própria chave. Um token de concessão impede conclusão tardia após a substituição de um worker. Salvar o rascunho e marcar o job como pronto usam a mesma transação. A exclusão do diagnóstico remove os jobs e rascunhos associados.

O payload enviado ao provedor contém a carreira canônica e somente os IDs, rótulos, lacunas e a programação pedagógica necessária. Identificadores de conta, token do questionário, respostas originais e texto integral do resultado ficam no SkillBridge. O job guarda duração, estado, versões técnicas e contagens de entrada e saída do Gemini na última resposta processável, quando disponíveis. A chave e o modelo continuam configurados no backend.

## Verificações locais

| Comando ou cenário | Resultado |
| --- | --- |
| `python -B -m pytest -p no:cacheprovider -q` em `backend` | 119 testes passaram, incluindo 17 do Sprint 3. |
| `npm run test` em `frontend` | 35 testes passaram. |
| `npm run lint`, `npm run build` e `git diff --check` | Passaram. |
| Gemini simulado | Sucesso, uso de tokens, 429, 503, timeout e JSON malformado. |
| Contrato e fila | Rejeição de semanas e competências incompletas, dependências inválidas, IDs repetidos e texto inseguro. Reuso entre solicitações, limite de novas tentativas, controle entre contas, recuperação após reinício e rollback de escrita. |

Os testes usaram SQLite temporário, dados sintéticos e Gemini simulado. A integração com o modelo real e a durabilidade da hospedagem permanecem pendentes. O backend manteve o aviso de depreciação do TestClient. O Vite manteve o aviso de tamanho do chunk Three.js.

## Arquivos alterados

- Código: `backend/app/blueprint.py`, `blueprint_jobs.py`, `gemini.py`, `history.py`, `learning.py` e `main.py`.
- Testes: `backend/tests/test_course_generation.py` e ajuste da fixture de migração em `test_learning.py`.
- Documentação: `README.md`, `backend/README.md`, `docs/08-sprints-kanban.md`, `docs/decisoes.md` e este registro.
