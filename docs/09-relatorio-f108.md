# Estrutura do relatório acadêmico — F108

**Base:** proposta F108 enviada pelo usuário, atividade parcial. **Envio:** Dream Shape + PDF + evidências; prazo 27/11/2026; equipes 4–6.

1. Descrição do problema: contexto ODS 8, dores, cenário atual, brainstorming real.
2. Planejamento de requisitos da solução geral: RF/RNF e objetivos.
3. Documentação das funcionalidades: descrições, tabelas e prints.
4. Planejamento de requisitos e criação do MVP: escopo e justificativa.
5. Métricas para avaliar o MVP: definição, objetivo, vínculo com funcionalidades.
6. Planejamento de sprints e comunicação: quadro Kanban, ferramentas, prints de todas as sprints.
7. Validação do MVP: plano, ferramentas, público, ≥10 usuários reais, resultados e relação com métricas.
8. Evidências e relatório final: ≥5 evidências, gráficos de métricas reais, impacto esperado, limitações, ajustes e aprendizados.

## Rubrica (5 pontos)
Problema 1,0; solução geral + MVP 1,0; métricas 0,5; plano e execução com ≥10 usuários 0,5; evidências e gráficos 1,0; relatório/sprints/ajustes 1,0.

## Checklist de submissão
[ ] Equipe 4–6 [ ] PDF cobre 8 tópicos [ ] Dream Shape preenchido [ ] ≥10 usuários reais [ ] ≥5 evidências reais [ ] Gráficos e análise [ ] Prints de todas as sprints [ ] Reflexão e ajustes [ ] Envio até 27/11.

## Situação em 10/11/2026
Auditoria e protótipo técnico de demonstração preparados (Fases 0 e 1). Ver docs/11-auditoria-plano.md e docs/12-verificacao-fase-1.md. Problema ainda é hipótese. Brainstorming, integrantes, pesquisa com ≥10 usuários, gráficos, capturas de sprints e anexos finais seguem pendentes. Testes automatizados não equivalem a validação acadêmica.

## Atualização técnica — 10/11/2026
Backend FastAPI e integração Gemini preparados, com testes automatizados usando mocks e fluxo HTTP demo. Chave local configurada pelo operador; modelo/cota e teste real pendentes. Ver docs/13-integracao-gemini.md. Isso não equivale a validação do MVP com universitários; itens de pesquisa e evidências reais continuam pendentes.

## Atualização técnica — 18/11/2026
A pedido do responsável, o fluxo passou a depender exclusivamente de Gemini: retirada demonstração pública e substituídos fallbacks por erros recuperáveis, com respostas preservadas para nova tentativa. Testes offline e publicação técnica registrados em docs/27-avaliacao-somente-ia.md. Isso não constitui teste com beneficiários ou evidência de eficácia; pesquisa, métricas reais e fechamento do relatório continuam pendentes.

## Manutenção operacional — 19/11/2026
Investigação de indisponibilidade e reprodução real de HTTP 503 do Gemini. Correção com uma única nova tentativa seletiva dentro de prazo global e diagnóstico técnico sem dados pessoais; 70 testes offline aprovados. Publicação e verificação em docs/28-resiliencia-gemini.md. Não representa teste com beneficiários nem evidência de eficácia.

Verificação publicada desta manutenção: retentativa passou nos testes com mocks, mas o fluxo real continuou bloqueado por HTTP 503 do Google. Não foi concluído diagnóstico/trilha nesta rodada; nenhuma normalização ou eficácia é alegada.
