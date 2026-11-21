# SkillBridge — instruções para Codex

## Missão
Construir um MVP web responsivo de orientação de competências para universitários buscando primeiro emprego, com questionário gerado pelo Gemini, autoavaliação, diagnóstico orientativo e trilha personalizada. Entrega acadêmica F108/Unifor até 27/11/2026.

## Regras inegociáveis
1. Leia todos os arquivos `docs/` e `prompts/` antes de alterar código. Execute apenas a fase solicitada; não implemente o projeto inteiro de uma vez.
2. Crie código executável, testado e documentado; não invente resultados de testes, entrevistas, evidências, métricas ou commits.
3. Frontend React + TypeScript + Vite + Tailwind; backend FastAPI + Python; SQLite local. Não exija autenticação no MVP.
4. Chave Gemini exclusivamente no backend via `GEMINI_API_KEY` em `.env` não versionado. `.env.example` sem segredo. Não registrar dados pessoais nem prompts integrais em logs.
5. Modelo Gemini configurável via `GEMINI_MODEL`, escolhido entre os modelos com cota gratuita efetivamente disponíveis na conta. Não presumir nome ou cota. SDK oficial `google-genai`.
6. IA não determina aptidão para emprego: resultados são orientativos, derivados de autoavaliação; nunca alegar certificação ou contratação garantida.
7. Validar JSON gerado pela IA com Pydantic, limitar tamanho, normalizar entradas, lidar com timeout, erro 429 e resposta inválida; sem modo demonstração ou fallback sem IA; falhas devem informar indisponibilidade e permitir nova tentativa preservando respostas.
8. Dados mínimos, consentimento informado para teste, identificação anônima por código, exclusão dos dados de teste quando solicitado.
9. Mobile-first, acessibilidade básica (rótulos, teclado, contraste, estados de carregamento/erro), visual SaaS profissional com azul profundo/violeta, animações discretas e opção de movimento reduzido.
10. Cada fase: listar arquivos alterados, comandos de teste, resultados e pendências. Registrar decisões em `docs/decisoes.md` e atualizar Kanban/sprints.
11. Não afirmar que houve teste com 10 usuários até que a equipe realize e registre os testes de verdade.
12. Não executar deploy com custo, enviar dados a serviços externos ou criar recursos pagos sem aprovação do usuário.

## Sequência obrigatória
Fase 0: auditoria dos documentos e backlog; Fase 1: scaffold e protótipo navegável; Fase 2: API e persistência; Fase 3: Gemini e fluxo de ponta a ponta; Fase 4: testes e publicação; Fase 5: validação com usuários e documentação acadêmica. Pare para validação após cada fase.
