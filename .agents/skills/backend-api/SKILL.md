---
name: backend-api
description: Implementar API FastAPI, contratos Pydantic e cálculo determinístico de lacunas.
---
# Procedimento
1. Ler `docs/04-arquitetura.md` e `docs/10-testes-qualidade.md`.
2. Criar schemas e endpoints, validação e erros consistentes.
3. Calcular lacuna `max(0, esperado - autodeclarado)` no backend.
4. Isolar integração externa por serviço substituível.
5. Testar entradas inválidas, ausência de API e erros.
