---
name: criar-dashboards
description: Criar dashboards reais, acessíveis e responsivos do estudante e administração SkillBridge V3, com rastreabilidade das métricas.
---

# Dashboards orientados por evidências

1. Leia seção D1–D3 do plano mestre. Inventarie fontes de verdade antes de criar visualizações. Sem métricas mockadas no ambiente de produção.
2. Dashboard aluno: 12 semanas, progresso, dominadas versus em estudo, lições, carga planejada/realizada, continuidade e CTA de retomada.
3. Dashboard de curso: mapa de módulos, bloqueios explicados, acertos por competência, reforços e conquistas.
4. Dashboard admin (somente papel autorizado): jobs Gemini, 429/503, validador, reportes e custos/tokens quando disponíveis. Agregue, minimize identificação e preserve privacidade.
5. Componentes: cartões de KPIs, gráfico de evolução, matriz de competências, cartões das 12 semanas, estados loading/empty/error, filtros de período. Defina formatos e unidades; gráficos devem ter alternativa textual.
6. Motion refinado em transições e conquistas; não animar números de forma enganosa; usar `prefers-reduced-motion`. Mobile-first sem rolagem horizontal de página.
7. Testar agregações com registros conhecidos: 0, 1, muitos; duas contas; fuso horário; dados incompletos; bloqueios e performance.

## Entrega

Dashboard reproduzível com dados persistidos, testes de reconciliação e captura visual desktop/mobile para revisão.
