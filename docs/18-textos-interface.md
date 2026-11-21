# Textos públicos de produto — 11/11/2026

Pedido: remover da aplicação os comentários sobre o trabalho da faculdade e usar textos de uma apresentação final do produto. A mudança é editorial; não declara que houve validação com usuários ou conclusão da pesquisa acadêmica.

## Alterações

- Cabeçalho: identificação acadêmica substituída por “Seu próximo passo”.
- Landing: bloco ODS substituído por proposta prática de autoconhecimento e ações na rotina.
- Rodapé: removidos F108, Unifor e ano de entrega; mantido o limite de orientação por autoavaliação.
- Conclusão: removidos comentários sobre protótipo, coleta de feedback e validação pendente; incluídos próximo passo e informação de que a sessão não é salva.
- Demonstração e mensagens de indisponibilidade: linguagem para quem usa o serviço, sem pedir configuração de backend, API ou consulta de cotas pelo usuário.
- Público universitário, campo de curso/semestre, consentimento, identificação da IA e da demonstração e limites da orientação permanecem por fazerem parte do produto.

## Arquivos e verificação

Frontend: App.tsx, styles.css, demo.ts, local-demo.ts, api.ts e testes existentes App.test.tsx/api.test.ts. Backend: gemini.py (somente mensagens públicas). Documentação: README, decisões, Kanban e este registro.

`pytest -q`: 41 aprovados (aviso preexistente de depreciação Starlette/httpx). `npm test`: 8 aprovados. `npm run lint` e `npm run build`: aprovados. Busca nos textos da interface não encontrou F108, Unifor, projeto acadêmico, protótipo ou comentários sobre validação pendente. Sem mudanças em contratos, persistência, questionário ou cálculo das lacunas; sem chamadas reais Gemini necessárias para esta revisão textual.


## Publicação observada

Commit funcional `cc4361560062d102eee4a82bfed07a8a2cfb5fe6`. Vercel `dpl_AjoG5sd71vbw9Zod5zReXMBdyMHX`: READY. Render `dep-dbqgf7t9el5s73esi6q0`: live. Domínio estável https://skillbridge-two-rosy.vercel.app.

Verificação no navegador: landing com cabeçalho/rodapé novos; fluxo local de demonstração com 8 níveis e 12 contextuais puladas; diagnóstico, quatro semanas e conclusão com próximo passo e aviso de sessão temporária. Sem chamadas Gemini ou dados de participantes. Captura completa da landing expirou no navegador; captura de viewport foi salva com sucesso. Evidências reais: [início](assets/interface-produto-inicio.jpg) e [conclusão](assets/interface-produto-conclusao.jpg). Capturas anteriores permanecem como histórico.
