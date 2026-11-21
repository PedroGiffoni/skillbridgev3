# Backend SkillBridge

FastAPI, Pydantic, Gemini e SQLite. Consulte [execução local](../README.md#executar-localmente) e [configuração de login](../docs/30-login-historico-perfil.md).

| Rota | Acesso e comportamento |
| --- | --- |
| `GET /health`, `GET /api/config` | Público. Saúde e disponibilidade do Gemini. |
| `GET /api/careers` | Público. Catálogo versionado de carreiras. |
| `POST /api/questionnaire` | Público. Gera oito competências ou solicita esclarecimento. Assina o questionário por uma hora. |
| `GET /api/auth/config`, `GET /api/auth/google/nonce` | Público. Disponibilidade dos métodos e desafio temporário para o Google. |
| `POST /api/auth/email/request`, `POST /api/auth/email/verify` | Solicita e verifica código por e-mail. |
| `POST /api/auth/google`, `POST /api/auth/logout` | Autentica pelo Google ou encerra a sessão. |
| `GET /api/account`, `POST /api/account/profile` | Requer sessão. Consulta e altera o perfil privado. |
| `POST /api/assessment` | Requer sessão, questionário assinado e consentimento. Calcula as lacunas, valida a trilha gerada pelo Gemini e salva no histórico da conta. Reenvios de uma submissão já salva retornam o resultado original. |
| `GET /api/history`, `GET/DELETE /api/history/{id}` | Requer sessão. Lista, abre e exclui avaliações da própria conta. |
| `GET /api/study-plans/{id}` | Requer sessão. Abre a última revisão do plano do titular. |
| `GET /api/courses/{id}` | Requer sessão. Abre a última revisão publicada do curso do titular. |
| `POST /api/courses/generate` | Requer sessão e consentimento. Enfileira ou reutiliza um job de blueprint. |
| `GET /api/courses/jobs/{id}` | Requer sessão. Consulta o estado e o conteúdo privado do titular. |
| `GET /api/study-plans/{id}/course-job` | Consulta o blueprint ou job da trilha. |
| `GET /api/courses` | Lista a biblioteca privada do titular. |
| `POST /api/courses/{id}/publish` | Publica um rascunho de blueprint já validado. |
| `GET /api/courses/{id}/lessons` | Lista os esboços e as lições salvas de uma revisão. |
| `POST /api/courses/{id}/lessons/{outline_id}/generate` | Solicita uma lição com consentimento. |
| `GET /api/lessons/{id}` | Reabre a lição imutável e o progresso de prática do titular. |
| `POST /api/exercises/{lesson_id}/hint` | Emite uma dica e um recibo para a tentativa do titular. |
| `POST /api/exercises/{lesson_id}/attempts` | Corrige e registra uma tentativa. Reenvios reaproveitam o resultado. |
| `GET/POST /api/lessons/{id}/materials` | Consulta ou solicita os formatos de estudo da revisão do tema. |
| `POST /api/lessons/{id}/materials/audio/{kind}` | Solicita a narração com consentimento próprio. |
| `GET /api/lessons/{id}/materials/audio/{kind}/{segment}` | Reproduz áudio privado com suporte a intervalos de bytes. |
| `POST /api/lessons/{id}/materials/{kind}/grade` | Corrige quiz ou simulado. |
| `GET/POST /api/courses/{id}/modules/{module_id}/assessment` | Consulta ou prepara a prova do módulo. |
| `POST /api/courses/{id}/modules/{module_id}/assessment/submit` | Corrige, grava evidência e verifica aprovação. |
| `GET /api/me/dashboard` e `POST /api/me/dashboard/time` | Consulta o progresso e salva tempo de estudo. |
| `POST /api/study-plans/{id}/replan` | Cria revisão da trilha preservando semanas concluídas. |
| `POST /api/content-reports` | Registra um problema de conteúdo na conta. |
| `GET /api/admin/access` e `GET /api/admin/quality` | Consultam a permissão e as métricas administrativas agregadas. |

A V3 gera 12 semanas por padrão e mantém a leitura dos registros de quatro semanas. Consulte [o contrato e a configuração de recuperação](../docs/31-v3-trilha-12-semanas.md) e [a migração de planos, cursos e catálogo](../docs/32-v3-persistencia-catalogo.md). Execute o backend com o checkout integral para incluir o catálogo de carreiras.

Solicitações POST são limitadas a 64 KiB. As saídas do Gemini são limitadas e validadas antes de salvar. Os diagnósticos usam autoavaliação orientativa. Falhas de geração permitem nova tentativa, com o rascunho temporário da interface.

Mantenha segredos no backend. Use `--no-access-log` e um worker na configuração atual. Em produção, use HTTPS, `AUTH_COOKIE_SECURE=true`, origens autorizadas explícitas e SQLite em disco durável. Os testes usam armazenamento temporário e substituem somente os serviços externos.
