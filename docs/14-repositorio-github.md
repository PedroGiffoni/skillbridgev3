# Repositório GitHub — 10/11/2026

A pedido do usuário, repositório privado criado em https://github.com/PedroGiffoni/skillbridge para versionar o projeto. Branch principal: main. Esta ação publica código no repositório autorizado; não é deploy da aplicação e não ativa Gemini.

Git inicializado localmente. Antes do primeiro commit, git check-ignore confirmou a exclusão de backend/.env, backend/.venv, frontend/node_modules, frontend/dist, frontend/.npm-cache e frontend/tsconfig.tsbuildinfo. Apenas os modelos .env.example sem segredo são versionáveis. Conferência adicional compara a chave local aos arquivos do índice em memória sem revelar seu valor. Nenhuma chave deve constar em commits.

Os testes desta versão estão registrados em docs/13-integracao-gemini.md: 36 backend, 7 frontend, lint e build aprovados. Não há alteração funcional nesta rodada; não foram repetidos testes do produto somente por criar o repositório. Modelo/cota Gemini e validação com usuários reais continuam pendentes.

Verificação de envio: confirmar que o SHA de HEAD local coincide com refs/heads/main no origin e que git status não aponta alterações rastreadas pendentes. O SHA real será informado após o envio; este registro não inventa um identificador antecipadamente.
