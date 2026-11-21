# Avaliação exclusivamente com IA — 18/11/2026

## Solicitação e decisão

RF10 substituído a pedido explícito do responsável: retirar a opção “Usar demonstração sem IA” e todos os resultados de contingência sem Gemini. Esta decisão substitui o fallback previsto nos documentos e prompts iniciais. Não altera os estudos 3D locais ainda aguardando aprovação.

## Comportamento e contrato

- Perfil, questionário, diagnóstico e trilha usam exclusivamente a integração Gemini existente. Não há botão ou caminho alternativo que produza avaliação genérica.
- O cliente não envia mais `demo`; a API rejeita esse campo legado com 422. Respostas públicas aceitam apenas `source_mode: gemini`; o frontend também rejeita a origem antiga.
- Configuração ausente e indisponibilidade retornam 503; timeout, 504; resposta inválida, 502; cota/limite local, 429 com `Retry-After: 60`. Erros Gemini têm `detail`, `code` e `retryable: true`, sem questionário ou diagnóstico parcial.
- A falha mantém profissão, consentimento, níveis, exemplos e contexto na memória da página. A pessoa aciona “Tentar novamente” ou “Tentar diagnóstico novamente”. Sem repetição automática das chamadas.
- Token assinado e cálculo `max(0, referência − nível autodeclarado)` preservados. O token continua expirando após uma hora e após reiniciar a API. Reiniciar avaliação ou recarregar a página apaga respostas locais; não existe persistência recuperável.
- Textos de consentimento e limites da autoavaliação permanecem. O envio ao Google está explícito, sem sugerir que IA seja opcional.
- Dados genéricos antigos ficam somente como fixtures de testes offline; nenhuma importação no fluxo da aplicação/endpoints. As fixtures não representam geração real da IA.

## Arquivos alterados

| Área | Arquivos |
| --- | --- |
| Interface | `frontend/src/App.tsx`, `api.ts` |
| Testes frontend | `App.test.tsx`, `integration.test.tsx`, `api.test.ts`, `test-fixtures.ts` (substitui `local-demo.ts`) |
| Backend | `backend/app/main.py`, `schemas.py`; `demo.py` identificado como fixture offline |
| Testes backend | `backend/tests/test_api.py` |
| Evidência visual | `docs/assets/avaliacao-somente-ia-perfil.jpg` (captura real da página pública, sem dados preenchidos) |
| Apresentação | `frontend/public/apresentacao.html`: somente frase sobre tratamento de erros |
| Regras e documentação | `AGENTS.md`, `README.md`, `docs/02-requisitos.md`, `03-escopo-mvp.md`, `04-arquitetura.md`, `05-integracao-gemini.md`, `06-design-ux.md`, `08-sprints-kanban.md`, `10-testes-qualidade.md`, `decisoes.md`, este registro e `prompts/02-FASE-3-GEMINI.md` |

## Verificação

Testes com mocks, sem chamadas reais ao Gemini e sem dados de participantes. Cobrem falhas do provedor, rejeição de `demo`, contratos apenas Gemini, nova tentativa com payload preservado, navegação, consentimento e reinício.

| Comando | Resultado |
| --- | --- |
| `npm test` (frontend local completo) | 26 testes aprovados em 6 arquivos; inclui 6 testes de estudos 3D locais que não integram a publicação |
| `npm run lint` e `npm run build` (frontend local) | Aprovados; aviso já existente de chunk Three.js acima de 500 kB |
| `npm test` (pacote isolado da publicação) | 20 testes aprovados em 4 arquivos; estudos 3D locais excluídos |
| `npm run lint` e `npm run build` (pacote isolado) | Aprovados; somente entradas app e personagens publicáveis, aviso Three.js existente |
| `backend/.venv/Scripts/python.exe -m pytest -q` (cwd backend, executável relativo `.venv/Scripts/python.exe`) | 56 aprovados; 1 aviso já existente Starlette/httpx. Sandbox travou em socket local do TestClient; execução fora dele concluiu em 1,02 s |
| `git diff --check` | Aprovado |

A cópia de publicação é derivada do último commit mais os arquivos desta alteração. Configuração Vite e modelos das revisões 3D locais não integram o pacote. Não houve validação de usabilidade com participantes nesta rodada; SB10 e relatório acadêmico final permanecem pendentes.

## Publicação e visualização

Aplicação: https://skillbridge-two-rosy.vercel.app. Commit funcional `21743c1a2d134c0d9c30f440183de0c0b4fb75d4`, enviado à branch main.

- Vercel `dpl_3Xh8GQzfGZqr9Y8Xcc8Porev2TEB`: READY, domínio estável associado ao commit correto.
- Render `dep-dbv1fph7lnhs738uanq0`: live, mesmo commit funcional.
- HTTP publicado: `/health` 200; `/api/config` 200 com `gemini_enabled: true`; OpenAPI sem campo `demo` em Profile/AssessmentRequest e origem restrita a `gemini`.
- POST com o campo legado `demo:true` rejeitado com 422 antes da geração. Nenhuma chamada real Gemini foi usada nesta rodada. A configuração habilitada não comprova cota disponível no momento.
- Perfil público conferido no navegador Edge: avisos revisados, botão “Começar autoavaliação”, ausência do botão demonstrativo e fim do formulário visível. [Captura real](assets/avaliacao-somente-ia-perfil.jpg). Não houve teste em aparelho físico nesta revisão.

Após atualizar, recarregue a página: clientes antigos enviam `demo:false`, removido do contrato. Isso apaga respostas que estejam apenas na memória da interface.
