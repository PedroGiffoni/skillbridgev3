---
name: planejar-12-semanas
description: Evoluir o plano SkillBridge de 4 para 12 semanas com versionamento, compatibilidade histórica, personalização por lacunas e testes.
---

# Planejador 12 semanas

1. Leia o plano mestre, schemas Pydantic, endpoint `/api/assessment`, contrato TypeScript, UI do plano, testes e histórico SQLite antes de editar.
2. Separe respostas legadas V1/V2 (`weeks[4]`) de V3 (`weeks[12]`) por versão explícita. Preserve leitura de históricos antigos; nunca sobrescreva entradas de 4 semanas.
3. Gere semanas 1–12 ordenadas, cada qual com objetivo, competências, atividade, estimativa de horas, entregável e revisão; vincule às lacunas calculadas pelo backend.
4. Valide lista completa, ordinais únicos, limites de tamanho, pre-requisitos acíclicos, esforço compatível com disponibilidade e ausência de campos pessoais no prompt.
5. Quando plano inviável em 12 semanas, sinalize restrição e priorize escopo; não prometa aptidão profissional.
6. Renderize calendário/trilha responsiva, semanas agrupadas em três blocos de quatro sem confundir calendário com domínio; mostre carregamento, erro e retomada.
7. Atualize fixtures e testes: V3 com 12; legado com 4; invalidar 11/13, repetidas, lacunas não referenciadas; replanejamento versionado preserva semanas feitas.

## Entrega

PR pequeno com migrations (se necessárias), validação API/frontend, testes e explicação de compatibilidade/rollback.
