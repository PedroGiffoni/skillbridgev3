---
name: auditar-skillbridge
description: Auditar o repositório SkillBridge antes de desenvolver a V3, verificando compatibilidade entre V1/V2, fluxo de diagnóstico, Git, testes e infraestrutura.
---

# Auditoria e governança V3

1. Leia `AGENTS.md`, `SKILLBRIDGE_V3_PLANO_MESTRE.md` e a documentação relevante no repositório. Inspecione branch, `git status`, testes e arquivos de configuração sem expor valores secretos.
2. Compare funcionalidades existentes com M01–M14. Produza tabela `manter/adaptar/criar/remover mediante aprovação`, apontando caminhos reais dos arquivos.
3. Confirme o catálogo de 72 carreiras e 12 áreas em `frontend/src/careers.json`; registre divergências com rótulos aceitos pelo backend.
4. Localize todas as dependências do contrato `weeks[4]`, inclusive testes, fixtures, textos, documentação, histórico e schema. Desenhe migração aditiva para `weeks[12]` sem reescrever dados históricos.
5. Execute comandos de testes existentes apenas quando ambiente/dependências permitirem; registre resultados reais e bloqueios.
6. Entregue `AUDITORIA_V3.md`, risco, sequência recomendada, primeiro PR mínimo e rollback. Não altere código de produção nem crie/push branch sem confirmar o estado Git e autorização.

## Critério de aceite

Relatório reproduzível com referências a arquivos, comandos, resultados e dúvidas bloqueadoras. Nenhuma modificação destrutiva.
