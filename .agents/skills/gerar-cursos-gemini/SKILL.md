---
name: gerar-cursos-gemini
description: Construir geração de cursos e microlições com Gemini gratuito, schemas, validação automática, versionamento e tolerância a falhas.
---

# Cursos sob demanda com Gemini

1. Reutilize `backend/app/gemini.py`, config existente e padrões de erro. Nunca fixe modelo presumido nem inclua chave no frontend. Não habilite cobrança.
2. Primeiro gere blueprint relacionando diagnóstico, 12 semanas, competências, módulos, lições e pré-requisitos. Só depois gere conteúdo de módulo/lição quando necessário.
3. Defina schemas Pydantic e JSON versionado; valide referências, IDs, progresso pedagógico, número de opções e gabarito, feedback coerente, limites e segurança. Correção objetiva é determinística.
4. Modele job `queued/running/ready/failed/needs_review`, timeout, rate limit, retry limitado e idempotência. Cacheie versões publicadas para evitar chamadas repetidas.
5. Rejeite conteúdo inválido; jamais substitua IA indisponível por curso fingidamente personalizado. Reporte erro compreensível e permita tentar novamente sem perder plano.
6. Registre métricas de latência, status, prompt_version e tokens quando fornecidos, sem texto completo de respostas pessoais ou segredos.
7. Teste com fake client e fixtures para 429, 503, timeout, JSON quebrado, gabarito contraditório, duplicação e sucesso.

## Entrega

Pipeline com publicação condicionada a validação, contrato documentado e testes offline sem custo de API.
