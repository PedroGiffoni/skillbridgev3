# Integração Gemini — Fases 2/3 preparadas em 10/11/2026

## Autorização e limites

Após aprovar visualmente o protótipo (“ficou muito bom”), o usuário solicitou integração ao Gemini. O backend da Fase 2 foi implementado como pré-requisito para integração solicitada da Fase 3. Fases 4 e 5 não iniciadas. A chave foi inserida pelo operador em backend/.env; verificou-se somente sua presença, sem exibir seu valor. Nenhuma chamada real Gemini executada, modelo e elegibilidade gratuita da conta ainda não confirmados. Imagem do Playground informa gemini-3.8-flash, mas isso não comprova cota gratuita da API. GEMINI_MODEL continua vazio e GEMINI_FREE_TIER_CONFIRMED=false; não houve ativação ou custo.

Skills aplicadas: backend-api, gemini-integration, frontend-design e quality-assurance locais; revisão de React conforme skill já lida na Fase 1. Todos os documentos e prompts foram relidos antes das alterações.

## Implementação e decisões

- FastAPI com /health, /api/config, /api/questionnaire e /api/assessment; sem autenticação.
- Contratos Pydantic com normalização Unicode/espaços/controles, limites de campos e arrays, IDs únicos, consentimento obrigatório e escala inteira 0–4. Mensagens de erro não repetem valores pessoais de entrada.
- Referências e IDs protegidos por token assinado HMAC efêmero, sem persistir sessões. Token contém questionário, não é criptografia nem autenticação, expira em uma hora e é invalidado ao reiniciar. Entrada máxima 32 KiB; assinatura verificada antes de descompactar o token.
- Lacunas sempre determinísticas no servidor: max(0, esperado − autodeclarado). Gemini não calcula nem altera lacunas. No modo local explícito da interface o cálculo é demonstrativo.
- SDK oficial google-genai 2.34.0 testado, modelo só ambiente, sem padrão presumido. Ativação requer chave, modelo e confirmação do operador sobre cota gratuita. A confirmação por variável não verifica faturamento automaticamente.
- JSON Schema enviado via response_json_schema e validação Pydantic após retorno. Máximo 24 KiB de JSON antes de validar, 6.000 tokens de saída. Timeout do transporte em milissegundos e deadline assíncrono em segundos.
- SDK configurado para uma tentativa total (sem retries automáticos), evitando multiplicar consumo. Retentativa manual sujeita ao rate limit global por processo, conservador e configurável (padrão 5/min, não cota Google). Sem registrar IP ou respostas no limiter; não há rate limit distribuído.
- Timeout, 429, falha de rede/provedor, JSON inválido, vazio ou excessivo geram fallback rotulado. Se questionário já veio do Gemini mas o diagnóstico falhar, preservam-se suas referências e lacunas; narrativa/trilha passam a demo e isso é informado.
- Profissão ambígua pode gerar pergunta de esclarecimento sem competências. Frontend valida contratos recebidos, mostra carregamento/cancelamento, ignora resposta tardia após reset, permite revisar respostas e usar demo local sem API.
- Proxy Vite /api para 127.0.0.1:8000, CORS restrito às origens locais configuradas. Servidores locais sem deploy. Uma única instância/worker nesta etapa.
- Estado em memória, sem banco ou analytics. SQLite não é necessário. Logs sem chave, prompts integrais ou exemplos; iniciar uvicorn com --no-access-log. Evitar habilitar debug HTTP do SDK.
- Consentimento descreve envio ao Google e uso de dados do serviço gratuito, linka termos, recomenda não incluir dados pessoais/sensíveis. Exclusão local não remove dados já processados pelo provedor. Pesquisa com IA deve usar participantes adultos.

## Rastreabilidade atualizada

| Cartão / requisito | Implementação | Evidência técnica real | Estado |
|---|---|---|---|
| SB07 RF01–06, RNF03–06 | backend/app/{schemas,main,tokens}.py | tests/test_api.py: entradas inválidas, consentimento, IDs, escala, assinatura/expiração, tamanho, CORS, cálculo e 429 local | Fase 2 técnica pronta para revisão |
| SB08 RF03, RF07, RF10, RNF04 | backend/app/gemini.py e frontend/src/api.ts/App.tsx | testes de SDK com mocks, fallback timeout/429/JSON, clarificação, fluxo UI API, cancelamento | Preparado; chamada real e elegibilidade pendentes |
| SB04 RF08 | Narrativa, pontos fortes, prioridades e quatro semanas recebidas da API | testes de contrato/fluxo backend e frontend | Integrado com mocks/demo; IA real não validada |
| SB05 RF09 | Cancelar/reset/revisar e descarte de resposta tardia | frontend/src/integration.test.tsx e App.test.tsx | Verificado automaticamente |
| SB06 RNF01–02 | Loading, erros, foco, reduced-motion, inputs bloqueados durante processamento | testes DOM; inspeção visual completa e leitor de tela ainda pendentes | Parcial |
| SB11 RNF07 / F108 | README, decisões, Kanban e este registro | arquivos desta entrega | Atualizado |

## Arquivos criados/alterados nesta rodada

Criados: backend/app/__init__.py, config.py, schemas.py, demo.py, tokens.py, gemini.py, main.py; backend/tests/test_api.py; backend/pytest.ini; backend/requirements.in e requirements.txt; backend/.env.example; frontend/src/api.ts, local-demo.ts, api.test.ts e integration.test.tsx; este documento.

Alterados: README.md, .env.example (modelo sem segredo), backend/README.md; frontend/src/App.tsx, App.test.tsx e styles.css; frontend/vite.config.ts; docs/02-requisitos.md, 05-integracao-gemini.md, 08-sprints-kanban.md, 09-relatorio-f108.md, 11-auditoria-plano.md e decisoes.md.

Arquivo local não versionável: backend/.env criado sem segredo e preenchido pelo operador. Não incluído nos artefatos/documentos nem exibido nos logs. Diretório não é um repositório Git, portanto não houve commit.

## Verificações executadas

- Instalação de dependências no venv Python 3.13.5; requisitos congelados com pip freeze.
- Primeira execução Pytest a partir da raiz falhou ao importar app; corrigido pythonpath no pytest.ini. Execuções dentro do sandbox bloquearam o socket interno do asyncio Windows (trace confirmou socketpair). Reexecução com acesso local fora do sandbox e mocks: 36 testes passaram.
- Backend: .venv/Scripts/python.exe -m pytest -q — 36 passed, aviso de depreciação Starlette/TestClient com httpx (preferência futura por httpx2). Não afeta a aprovação dos testes atuais.
- Frontend: npm test — três arquivos, sete testes passaram; a execução ampliada encerrou sem o aviso de close timeout observado na Fase 1.
- npm run lint — aprovado, saída 0.
- npm run build — TypeScript e bundle aprovados, saída 0.
- Saúde GET /health respondeu status ok e /api/config respondeu gemini_enabled=false.
- HTTP via proxy Vite: GET / retornou 200; POST /api/questionnaire com demo=true retornou cinco competências; POST /api/assessment retornou demo e quatro semanas. Usados apenas dados sintéticos genéricos, nunca apresentados como pesquisa real.
- Vite precisou ser reiniciado fora do sandbox para socket local funcionar; API local também iniciada fora do sandbox. Nenhum dado enviado ao Google.
- Busca estática no código/build frontend por api_key, GEMINI_API_KEY e .env não encontrou ocorrências. Nenhuma chave no frontend. Configuração .gitignore protege .env; sem repositório Git para executar check-ignore/status com sucesso.

## Pendências

Confirmar modelo/cota na conta e registrar modelo escolhido; então configurar ambiente e executar teste real consentido (sem dados pessoais) do questionário e diagnóstico. Não afirmar integração real validada antes disso. Revisão visual/acessibilidade completa e deploy só após autorização da Fase 4. Alertas moderados da cadeia de lint registrados na Fase 1 continuam pendentes; dependências npm não foram alteradas nesta rodada. Revisão humana de recomendações educacionais necessária. Testes com ≥10 usuários, métricas, atas, fotos e evidências acadêmicas reais permanecem não realizados.

## Fontes oficiais consultadas em 10/11/2026

- SDK: https://github.com/googleapis/python-genai — cliente assíncrono, contexto e erros; campos de HttpOptions/HttpRetryOptions/GenerateContentConfig também conferidos no SDK instalado, sem chamada de rede.
- JSON estruturado: https://ai.google.dev/gemini-api/docs/structured-output — JSON Schema e Pydantic; configuração conferida no SDK instalado.
- Cotas: https://ai.google.dev/gemini-api/docs/rate-limits — limites ativos dependem do projeto/modelo e devem ser conferidos no AI Studio.
- Termos/privacidade: https://ai.google.dev/gemini-api/terms — uso gratuito e dados enviados; acesso a IA direcionado a adultos.

Verificações finais adicionais: pip check retornou 'No broken requirements found'. Comparação em memória da chave real com arquivos de código/documentação/build (excluindo .env e dependências) não encontrou a chave; somente presença/configuração foram informadas, nunca o segredo.
