# Ativação Gemini — 11/11/2026

## Conta, modelo e limites observados

No Google AI Studio, o projeto SKILLBRIDGE (`gen-lang-client-0174031911`) apresentou nível gratuito. A chave local corresponde a esse projeto. A página de limites do projeto, com todos os modelos exibidos, apresentou `gemini-3.5-flash-lite` com 15 RPM, 250 mil TPM e 500 RPD. Esses valores são observações desta data, não garantia futura.

Escolha: `GEMINI_MODEL=gemini-3.5-flash-lite`. O modelo permanece configurável; limite interno conservador de 5 chamadas/minuto e timeout de 30 segundos. Uma avaliação normal faz duas chamadas. Sem ativar faturamento ou criar recursos pagos.

Fontes oficiais: [modelo](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [preços](https://ai.google.dev/gemini-api/docs/pricing), [limites](https://ai.google.dev/gemini-api/docs/rate-limits). A elegibilidade foi conferida no projeto correto, além da documentação geral.

## Teste técnico real local

Executado com Python do ambiente virtual, `TestClient(create_app(Settings()))`, configuração local ignorada pelo Git e SDK oficial `google-genai`. Dados exclusivamente sintéticos: profissão Desenvolvedor frontend júnior, consentimento ativo, níveis autodeclarados 2, sem exemplos ou contexto pessoal.

| Verificação | Resultado observado |
| --- | --- |
| POST `/api/questionnaire` | HTTP 200, `source_mode=gemini`, 6 competências |
| POST `/api/assessment` | HTTP 200, `source_mode=gemini`, 4 semanas |
| Cálculos | Todas as lacunas iguais a `max(0, esperado - autodeclarado)` |
| Consumo | Duas chamadas reais, sem retentativa automática |

Não foi necessária alteração de código. Não constitui pesquisa com usuários, entrevista, certificação ou validação de eficácia. Aviso de depreciação do TestClient/httpx observado, sem falha do teste.

## Render e teste publicado — concluídos

Configurados por merge, preservando CORS/Python: modelo, confirmação da cota, timeout e limite interno. Deploy inicial de configuração `dep-dbq5p556e07s73c7jjo0` atingiu live. O titular inseriu a chave diretamente no Render após a importação automática ser bloqueada pela extensão do navegador e a revisão automática impedir leitura do editor que pudesse expor o segredo.

Deploy após a chave: `dep-dbq5qhoae00c73ddhiag`, live. GET `/api/config` retornou `{"gemini_enabled":true}`. Nenhuma chave impressa ou enviada pelo chat; permanece fora do frontend e do Git.

Fluxo no domínio público https://skillbridge-two-rosy.vercel.app:

1. Perfil sintético Desenvolvedor frontend júnior, consentimento ativo e campos opcionais vazios.
2. Questionário exibiu conteúdo gerado por Gemini e seis competências.
3. Preenchidas seis respostas no nível 2, sem exemplos pessoais.
4. Diagnóstico exibiu conteúdo gerado por Gemini. Referências 2, 2, 1, 1, 1, 1 e lacunas 0 em todos os casos: conferidas com `max(0, referência - 2)`.
5. Trilha gerada por Gemini exibiu semanas 1–4, objetivos, ações e entregáveis.

Duas chamadas reais adicionais pelo fluxo do navegador; quatro chamadas nesta rodada contando o teste local. Sem retentativas manuais. Capturas reais: [diagnóstico](assets/gemini-diagnostico-real.jpg) e [trilha](assets/gemini-trilha-real.jpg). Não representam participantes ou validação de eficácia.

## Verificação desta rodada

| Comando | Resultado |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=30` (em backend, executável relativo `.venv/Scripts/python.exe`) | 36 aprovados, 1 aviso de depreciação Starlette/httpx |
| `.venv/Scripts/python.exe -m pip check` (backend) | Nenhuma dependência quebrada |
| `npm test` (frontend) | 8 testes aprovados em 3 arquivos |
| `npm run lint` (frontend) | Aprovado |
| `npm run build` (frontend) | Aprovado, Vite 7.3.8 |
| `git diff --check` | Sem erros |

A primeira execução backend no sandbox não concluiu e foi interrompida; a execução fora do sandbox concluiu em 0,81 s. Nenhuma alteração de código necessária. Alterados README, documentação de ativação, decisões, Kanban e assets reais; configuração local `.env` ignorada pelo Git. Arquivo temporário de importação removido após uso.

## Preferência permanente de README

Registrada em `04-Skills-e-Prompts/Padrao-README-GitHub.md` no Segundo Cérebro e nas instruções globais do Codex. Nota e índice sincronizados no commit `c82f28c` do repositório do cérebro. README do SkillBridge enriquecido com ilustração identificada, navegação, arquitetura, tabelas e status reais.
