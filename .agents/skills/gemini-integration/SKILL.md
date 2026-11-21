---
name: gemini-integration
description: Integrar Gemini de forma segura, econômica e auditável no backend.
---
# Procedimento
1. Ler `docs/05-integracao-gemini.md`.
2. Confirmar modelo e cota gratuita; usar SDK `google-genai`.
3. Guardar segredo somente em `.env`; schemas JSON validados.
4. Tratar timeout, rate limit, erros de parse e modo demo rotulado.
5. Testar com mocks sem gastar tokens em testes automatizados.
