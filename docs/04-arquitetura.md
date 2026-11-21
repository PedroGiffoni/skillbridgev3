# Arquitetura proposta

`React/TypeScript/Vite/Tailwind` → `FastAPI` → `Gemini API (google-genai)`; `SQLite` apenas para metadados mínimos e registros não identificáveis, se necessário. A interface nunca chama Gemini diretamente.

## Rotas sugeridas
- `GET /health` — saúde sem expor segredo.
- `POST /api/questionnaire` — recebe profissão e contexto opcional; devolve competências e perguntas em JSON.
- `POST /api/assessment` — recebe questionário + autoavaliação; calcula lacunas no servidor e consulta Gemini para narrativa/trilha.
- `POST /api/feedback` — opcional, coleta anônima de métricas de usabilidade com consentimento; evitar IP e identificadores persistentes.

## Contratos
Definir schemas Pydantic de request/response e tipos TypeScript equivalentes. Competência: `id`, `name`, `description`, `expected_level` (0–4, **estimativa gerada**), `question`. Resposta: `competency_id`, `self_level` (0–4), `example?`. Resultado: lacunas determinísticas + `summary`, `strengths`, `priorities`, `weeks[4]`, `limitations`, `source_mode` (`gemini` exclusivamente).

## Segurança e privacidade
Não salvar segredo no Git, sanitizar profissão e exemplos, limitar caracteres e quantidade de competências, controlar CORS, rate-limit por IP de modo proporcional, restringir logs e remover dados ao fim da pesquisa. Enviar à API externa somente dados necessários e informar isso ao participante.

## Deploy
Selecionar hospedagem gratuita compatível com backend Python e frontend estático, verificando limites e hibernação; não presumir disponibilidade ou persistência de SQLite em disco efêmero. Para MVP sem dados identificáveis, preferir processamento em memória e exportação manual de evidências anonimizadas; se persistir, usar serviço com volume/banco persistente.
