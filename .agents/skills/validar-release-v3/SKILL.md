---
name: validar-release-v3
description: Executar gates de testes, regressão, segurança, acessibilidade e preparação segura da branch V3 antes de publicar o SkillBridge.
---

# Qualidade e entrega segura

1. Confirme branch `V3`, diff e estado Git; não sobrescreva alterações existentes nem faça push/deploy sem autorização.
2. Execute suíte de testes existente, tests V3, lint, build e E2E dos fluxos diagnóstico → 12 semanas → curso → 80% → dashboard. Registre comandos e falhas sem ocultar bloqueios.
3. Teste compatibilidade com histórico V1/V2 de quatro semanas, persistência após refresh/login, isolamento entre contas, mensagens para falha Gemini e ausência de segredos em client/logs.
4. Inspecione UX em 320px, tablet e desktop; teclado, contraste, reduz movimento, gráfico com descrição, loading/erro/vazio.
5. Revise schema migrations, plano de rollback e backup antes de produção. Não execute migração destrutiva ou habilite serviço pago.
6. Entregue relatório de release: recursos entregues, testes executados e resultados, bugs, evidências, riscos pendentes e recomendação go/no-go.

## Gate

Só considerar release se contrato de 12 semanas, limiar de 80%, autorização e dashboards reais passarem nos testes. Nunca declarar deploy/teste não feito.
