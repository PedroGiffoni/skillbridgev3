# Alternativas contextualizadas — 17/11/2026

## Problema observado e decisão

Usuário enviou captura de uma pergunta sobre planejar a lógica de um programa e investigar loop infinito. As cinco opções genéricas de autonomia não respondiam ao enunciado. Agora a primeira chamada Gemini deve produzir cinco descrições práticas para cada pergunta, em primeira pessoa e relacionadas à situação. Não é um teste de conhecimento com gabarito.

Progressão orientativa: 0 ainda não praticou; 1 segue exemplo com orientação próxima; 2 executa parte e busca ajuda pontual; 3 realiza e verifica situações habituais; 4 analisa situações menos previsíveis e ajusta a estratégia. Todos os níveis precisam descrever a tarefa específica. Ensinar terceiros não é requisito do nível 4. A qualidade e a progressão semântica ainda exigem revisão humana; validação estrutural não certifica a coerência da IA.

## Implementação

- `Competency.options`: cinco objetos value/label. Valores inteiros estritos 0–4 em ordem, sem duplicação. Rótulos normalizados, distintos e de 12–220 caracteres.
- Opções vinculadas ao questionário HMAC. A resposta do navegador continua enviando nível e exemplo; o backend recupera option_label do token, sem confiar em descrição enviada pelo cliente.
- Diagnóstico recebe rótulo, nível, exemplo e contexto como autorrelato. Fórmula de lacuna inalterada.
- UI mostra as alternativas próprias da pergunta, com rótulos clicáveis, teclado, texto com quebra de linha e escala identificada.
- Demonstração possui 8 conjuntos editoriais próprios. Catálogos Python/TypeScript conferidos por teste. Não há geração de frases genéricas silenciosa para substituir opções inválidas.
- Geração real ausente/inválida continua caindo em demonstração identificada. Sem alteração de timeout, 429, duas chamadas, modelo ou chave.
- Questionários anteriores à publicação devem ser gerados novamente após o reinício da API. O frontend valida o novo contrato; a apresentação HTML permanece independente.

## Arquivos

Backend: schemas.py, main.py, demo.py, demo_options.py e tests/test_api.py. Frontend: api.ts, App.tsx, styles.css, demo.ts, local-demo.ts, demo-options.ts e testes api/App/integration. README, requisitos, integração, decisões, Kanban e este registro atualizados.

## Testes executados

| Comando | Resultado |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q` em backend | 52 aprovados, aviso preexistente Starlette/httpx |
| `npm test` em frontend | 15 aprovados |
| `npm run lint` em frontend | Aprovado |
| `npm run build` em frontend | Aprovado |

Verificados: ausência/quantidade/ordem/tipo/duplicatas/limites das opções, rejeição de resposta inválida da IA, rótulo escolhido recuperado do token, impossibilidade de substituir o rótulo pelo request, preservação das lacunas, alternativas da API diferentes entre perguntas, revisão de respostas e fluxo de 20 perguntas. A execução inicial de build no sandbox foi interrompida por demora; lint/build fora dele concluíram.

## Publicação e verificação real

Commit funcional `f315de3ebe0e7757f94535045a6dce96a6db2d00`. Vercel `dpl_2asLE2LaRbFyY13JDeWeNmq59jAh`: READY. Render `dep-dbudgu3bc2fs73a7jebg`: live. Domínio do aplicativo: https://skillbridge-two-rosy.vercel.app. Apresentação não foi alterada.

Antes das chamadas, conferido o projeto SKILLBRIDGE no AI Studio em 17/11/2026: nível gratuito e Gemini 3.5 Flash Lite com limites 15 RPM / 250 mil TPM / 500 RPD observados, sem alteração de faturamento ou credenciais.

Teste técnico no navegador com profissão sintética Desenvolvedor de software, sem contexto pessoal, exemplos ou campos acadêmicos. Oito perguntas Gemini, cada uma com cinco alternativas próprias, incluindo código funcional, depuração, controle de versão e documentação. Conferida mudança de alternativas entre perguntas e seleção do nível 2 preservada ao voltar. Doze contextuais puladas. Diagnóstico e quatro semanas retornaram em modo Gemini, sem fallback. Referências 1 ou 2 e nível autodeclarado 2 resultaram em lacunas zero, conforme fórmula. Duas chamadas reais nesta rodada.

Captura real com respostas sintéticas: [alternativas contextualizadas](assets/alternativas-contextualizadas-exemplo.jpg). Revisão visual confirma que as opções respondem à situação da pergunta; isso não comprova uma escala psicométrica. A IA omitiu acentos em trechos deste retorno, limitação editorial observada. Tentativa de viewport 390px não alterou a largura efetiva da aba (1912px), portanto esta rodada não declara aprovação visual móvel; override restaurado. Capturas CDP de página inteira/recorte expiraram; evidência final obtida pela captura normal do navegador.

Nenhuma entrevista ou validação com participantes nesta rodada.
