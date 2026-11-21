---
name: construir-microlicoes
description: Implementar player gamificado, exercícios, tentativas e desbloqueio por domínio no SkillBridge V3, com UI acessível.
---

# Player, prática e domínio

1. Reuse design system e navegação atuais. Implemente player mobile-first com objetivo → explicação → exemplo → exercício → feedback → resumo.
2. Tipos P0: múltipla escolha, preencher lacuna e ordenar itens; cada tipo tem JSON contract, componente, validação e fixture.
3. Persistir `Attempt` com aluno, versão do exercício, resultado, momento e uso de dica. Não confiar no cliente para pontos ou desbloqueio.
4. Treino admite dicas. Avaliação somativa aplica ≥80% e cobertura crítica no servidor; 79% bloqueia e oferece reforço; nova prova deve variar itens equivalentes. Não tratar XP como prova de competência.
5. Bloqueio deve ser verificado em cada rota protegida; usuário não deve abrir módulo futuro digitando URL.
6. Implementar XP com ledger idempotente. Feedback agradável, Motion com redução de movimento, foco visível, teclado e suporte 320px; Three.js opcional somente se não prejudicar compreensão e performance.
7. Testar aprovação, reprovação, retry, refresh, duas contas e duplicação de XP.

## Entrega

Fatia vertical demonstrável de uma carreira e um módulo, sem fingir evolução das demais 71 carreiras.
