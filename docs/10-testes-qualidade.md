# Plano de qualidade

## Backend
Testar contratos Pydantic, profissão vazia/extensa, escala fora de 0–4, IDs de competência inconsistentes, duplicatas, cálculo de lacuna, timeout Gemini, HTTP 429, JSON inválido, rejeição do antigo campo demo, ausência de chave sem resultado demonstrativo, segredo fora de logs, recuperação de 503 com uma única nova tentativa, interrupção no prazo global e ausência de repetição automática para erro de acesso/configuração/429/saída inválida.

## Frontend
Testar formulário, progresso, navegação anterior, carregamento, erro, dashboard, responsividade 360/768/1280, teclado e redução de movimento.

## Integração
Mock Gemini em testes automatizados; teste real manual apenas com chave configurada e consentimento de uso. Não depender de IA real no CI.

## Critérios de pronto
Testes automatizados passando, instruções de instalação e deploy no README, nenhum segredo commitado, fluxo ponta a ponta executado e limitações documentadas.
