# Disponibilidade e diagnóstico Gemini — 19/11/2026

## Relato e investigação

O responsável apresentou captura de erro no início da autoavaliação. O frontend exibia a mensagem de indisponibilidade associada ao HTTP 503. A publicação funcional estava ativa no Render (`21743c1`) e os registros disponíveis mostravam inicialização normal, sem a causa do erro do provedor.

Conferência na conta AI Studio, projeto SKILLBRIDGE: nível gratuito; Gemini 3.5 Flash Lite com limites observados de 15 RPM, 250 mil TPM e 500 RPD. A tabela exibia máximos de 2 RPM, 4,73 mil TPM e 10 RPD nos últimos 28 dias; são dados de pico, não garantia de capacidade instantânea. Nenhum faturamento foi ativado. Modelo no Render confirmado como `gemini-3.5-flash-lite`, igual ao ambiente local. Prazo de 30 s confirmado no Render; não foi alterado.

Duas solicitações reais de diagnóstico, ambas com profissão sintética “Designer de interfaces” e sem dados pessoais:

1. API pública: 200, origem Gemini, oito competências; geração em 26,19 s após o serviço acordar.
2. Adaptador local: `ServerError`, código 503, categoria `UNAVAILABLE` do provedor.

Isso reproduz uma falha intermitente do Gemini. Não prova que toda indisponibilidade histórica teve a mesma causa. Não houve alteração de chave, modelo ou plano. Nenhuma chave, mensagem bruta do provedor, conteúdo integral de prompt ou dado pessoal foi gravado nos registros da investigação.

## Correção

- Cada geração pode executar no máximo duas tentativas totais, somente para erros HTTP 500/502/503/504. Espera de 1 s, apenas se houver orçamento de tempo útil.
- Cliente, chamadas e espera compartilham um único `asyncio.timeout` com o prazo configurado em `GEMINI_TIMEOUT_SECONDS`. Não existe novo prazo completo na segunda tentativa; retries internos do SDK continuam com `attempts=1`.
- Sem repetição automática para 429, 400/401/403/404, JSON inválido, timeout global ou erro de transporte sem status transitório conhecido.
- Erros 400/404 têm categoria `configuration`; 401/403, `access_denied`. Essas categorias e `not_configured` retornam `retryable:false`. Falhas transitórias continuam recuperáveis. Todos mantêm mensagens públicas controladas, sem dados do provedor.
- Logs somente com categoria controlada, status numérico 400–599 (ou ausente) e número da tentativa. Sem stack trace, mensagem bruta, prompt, exemplo, dado do estudante ou chave.
- Nenhum resultado demonstrativo. Na falha final, as respostas continuam na memória do navegador para nova solicitação manual.
- O limite local existente conta gerações do aplicativo. Com 5 gerações/minuto, podem ocorrer até 10 tentativas HTTP; não é medição nem garantia da cota Google. O funcionamento com uma única instância/worker permanece.

## Arquivos e verificação

Código: `backend/app/gemini.py`, `backend/app/main.py`. Testes: `backend/tests/test_api.py`. Documentação: README, integração Gemini, plano de qualidade, decisões, Kanban, relatório F108 e este registro. Frontend, apresentação e estudos 3D locais preservados.

| Comando/check | Resultado |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q` em `backend` | 70 aprovados; 1 aviso preexistente de depreciação Starlette/httpx; execução final de 4,34 s fora do sandbox |
| Revisão independente | Sem bloqueios na implementação |
| Cenários novos | Recuperação de 500/502/503/504; 503 persistente no máximo 2 tentativas; ausência de retry em erros de cliente/cota/JSON; logs sem segredo |
| Prazo global | Teste inclui latência inicial de 0,6 s, pausa real de 1 s e segunda chamada lenta; encerra no prazo total de 3,2 s, detectando reinício indevido do orçamento |
| Frontend | Sem mudança de código nesta rodada; última suíte do pacote publicável: 20 testes em 18/11/2026 |
| Publicação | Commit funcional `435182e`, Vercel READY e Render live |
| Fluxo público após correção | Falhou na geração: dois 503 seguidos do Google. Logs seguros comprovaram tentativas 1 e 2; perfil e consentimento preservados |

O sandbox bloqueou socket local durante a execução inicial, como já observado na suíte. Os testes finais foram executados fora dele, com SDK mockado, sem consumir Gemini. A pesquisa com beneficiários, métricas de eficácia e fechamento do relatório F108 continuam pendentes.

## Referências oficiais

[Tratamento de erros e retentativas Gemini](https://aistudio.google.com/docs/troubleshooting), [limites por projeto](https://aistudio.google.com/docs/rate-limits) e [limites ativos da conta](https://aistudio.google.com/rate-limit). As recomendações gerais não identificam por si só a causa de uma solicitação; o 503 foi observado diretamente nesta investigação.

## Resultado publicado e limite externo

Commit funcional: `435182e4f3fae4bc3649e38101c7a1c96438476f`. Vercel `dpl_DCXW1ATNkWJY4rXxSs88CBVPS9Dv` READY; Render `dep-dbvhpmnf3r2c73814vbg` live.

O teste no navegador após publicar ainda recebeu 503 nas duas tentativas. Os registros mostraram somente `reason=unavailable provider_status=503 attempt=1` e depois `attempt=2`, sem entrada ou segredo. Não foi possível chegar ao diagnóstico ou à trilha; não se declara o fluxo normalizado. [Captura real da falha pública com dados sintéticos](assets/gemini-503-verificado.jpg).

Antes de qualquer troca em produção, foram conferidas na conta e testadas localmente estas alternativas, com o mesmo contrato estruturado:

| Modelo | Cota gratuita observada | Resultado real |
| --- | --- | --- |
| `gemini-3.1-flash-lite` | 15 RPM, 250 mil TPM, 500 RPD | 503 nas duas tentativas |
| `gemini-2.5-flash-lite` | 10 RPM, 250 mil TPM, 20 RPD | 404 sem nova tentativa; a documentação restringe acesso a usuários antigos |
| `gemini-3.8-flash` | 5 RPM, 250 mil TPM, 20 RPD | 503 nas duas tentativas |

Mantidos em produção o modelo original 3.5 Flash Lite, o prazo de 30 s e a chave existente. Não houve recurso pago, mudança de cobrança ou substituição por resultado sem IA. Foram seis operações técnicas de geração nesta investigação, totalizando nove tentativas HTTP aos modelos (inclui a rejeição 404), sem dados pessoais; o único sucesso foi o questionário público anterior à correção. Não são testes com participantes.

A recuperação da disponibilidade externa continua pendente. A melhoria de retentativa foi validada com mocks; não elimina falta de capacidade do provedor. O limite exibido no AI Studio não garante capacidade de atendimento. O [modelo 2.5](https://aistudio.google.com/docs/models/gemini-2.5-flash-lite) possui restrição de acesso histórico, e há [resposta da equipe do Google sobre 503 no 3.5](https://discuss.ai.google.dev/t/intermittent-http-503-from-generatecontent-with-gemini-3-5-flash-lite/201338) atribuindo-o à sobrecarga temporária, sem confirmar incidente global em 19/11.
