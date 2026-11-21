# Fase 4 — publicação Render + Vercel (10/11/2026)

Solicitação expressa do usuário: publicar backend no Render e frontend na Vercel. Sem contratação de plano pago. Gemini permanece desativado: modelo e cota gratuita da conta ainda não confirmados. Validação com participantes reais continua pendente.

## Configuração preparada

- Render: web service Python, raiz backend, build pip install -r requirements.txt; start sh start.sh (0.0.0.0, porta PORT, um worker, sem access log). Python 3.13.5 em .python-version; saúde /health. Plano Free sujeito às limitações vigentes e disponibilidade na conta. Sem banco, disco pago ou outros serviços.
- Vercel: projeto na conta Hobby PedroGiffoni's projects, repositório PedroGiffoni/skillbridge, branch main, raiz frontend, preset Vite, build npm run build, saída dist. Só a interface na Vercel.
- VITE_API_BASE_URL: origem HTTPS pública efetiva do backend, sem chave ou caminho. Valor injetado durante build na Vercel; mudar exige redeploy. No desenvolvimento local, vazio preserva proxy Vite. Produção sem URL oferece demo explícita, sem tentar endpoint fictício.
- CORS_ORIGINS: lista JSON com origem efetiva publicada na Vercel, sem wildcard; atualizar no Render após conhecer a URL. Não colocar segredos no frontend.
- GEMINI_FREE_TIER_CONFIRMED=false e ausência de modelo/chave no serviço hospedado mantêm fallback visível, sem chamadas Google. Chave local não deve ser copiada ao frontend, ao Git ou aos registros.
- Timeout do cliente ampliado de 65 para 120 segundos para acomodar início a frio; timeout Gemini no servidor permanece 30 segundos. Cancelamento disponível. Não usar monitor artificial para impedir hibernação do plano gratuito.
- Cabeçalhos da API: Cache-Control: no-store e X-Content-Type-Options: nosniff. Frontend: nosniff, Referrer-Policy e X-Frame-Options: DENY.

## Testes antes de publicar

- Backend: .venv/Scripts/python.exe -m pytest -q: 36 passed, um aviso de depreciação Starlette/httpx.
- Frontend: npm test: 8 passed (inclui endereço HTTPS, produção sem API e URL inválida); npm run lint e npm run build aprovados.
- O build com VITE_API_BASE_URL vazio é intencionalmente capaz de servir demo local e informar que a API hospedada ainda não está configurada.

## Situação de acesso

Consultas de contas via conectores Render/Vercel não responderam e foram encerradas sem mutações. Fallback para painéis web. Vercel autenticada, plano Hobby visível. Login Render inicialmente retornou à tela de acesso; solicitada conclusão do login pelo usuário enquanto a preparação continua. Nenhum deploy será declarado concluído apenas por ter sido iniciado.

## Verificação necessária após deploy

Confirmar status live no Render e Ready na Vercel, commit efetivo, GET /health e /api/config, CORS da URL efetiva, fluxo HTTP demo completo e navegação no navegador. Registrar URLs e resultados reais nesta seção ao obtê-los. Ainda não há URL publicada confirmada neste registro inicial.

## Fontes oficiais verificadas

https://render.com/docs/free.md — plano gratuito tem hibernação, limites e disco efêmero.
https://render.com/docs/compute-plans.md — web service free consta no catálogo atual.
https://render.com/docs/deploys.md e https://render.com/docs/health-checks.md — deploy assíncrono e saúde HTTP.
https://render.com/docs/configure-environment-variables.md — variáveis no serviço, segredos fora do repositório.
https://vercel.com/docs/plans/hobby — conta Hobby; plano observado no painel.

## Arquivos desta rodada

backend/start.sh, backend/.python-version, backend/app/main.py; frontend/.env.example, frontend/vercel.json, frontend/src/vite-env.d.ts, frontend/src/api.ts e api.test.ts; README.md, docs/08-sprints-kanban.md, docs/decisoes.md e este registro. Novos resultados de deploy serão acrescentados sem fabricar evidências.

## Situação após tentativa de publicação

- Configuração revisada enviada ao GitHub no commit 70b8fec (main). 36 testes backend + 8 frontend, lint e build aprovados. npm audit --omit=dev retornou zero vulnerabilidades nas dependências de produção; alertas de ferramentas registrados anteriormente continuam separados.
- Vercel: importação configurada para frontend/Vite no workspace Hobby PedroGiffoni's projects. Ao clicar Deploy, o painel exibiu “Verify Your Identity” e “Use Passkey”. Não houve confirmação de Ready, URL pública ou deploy concluído. Verificação de identidade depende do titular; não foi tentado contorná-la.
- Render: login existente via GitHub chegou à etapa “Signing you in”, sem acesso confirmado ao workspace. Nova navegação voltou ao login; nova tentativa ainda não comprovou sessão autenticada. Não foi criado serviço nem recurso pago.
- Usuário informou estar pelo celular. Publicação fica pendente do acesso às contas; as configurações concretas estão prontas no repositório. Não divulgar URLs estimadas como se estivessem ativas. Continuação: concluir autenticação, criar Render Free com a configuração acima, obter URL real, configurar VITE_API_BASE_URL na Vercel e CORS_ORIGINS no Render, concluir deploy e executar o fluxo HTTP/navegador.

## Avanço no acesso Render

Nova tentativa de login via GitHub concluiu com sucesso no workspace ativo My Workspace (tea-d91f9gtaeets73fd5i20). Ao criar Web Service, skillbridge não apareceu: a credencial PedroGiffoni do Render tem acesso a apenas quatro repositórios (um próprio e três de outra conta), sem o novo repositório privado. Foi aberta a configuração existente do app Render no GitHub; o GitHub exigiu sudo mode. Acionada confirmação pelo GitHub Mobile para o titular aprovar, sem ler senha ou código de e-mail. Nenhuma permissão de repositório foi alterada até este registro. Vercel continua exigindo sua verificação de identidade. Ainda não há serviço SkillBridge criado nem URL pública confirmada.

## Publicação e teste efetivos — 11/11/2026

A autenticação dos conectores foi confirmada nesta rodada. O projeto Vercel já existia e tinha deploy de produção Ready, mas não havia backend SkillBridge no Render. Foi criado o serviço gratuito e concluída a comunicação entre os dois, conforme autorização de publicação anterior.

### Recursos e versões verificados

- Frontend público: https://skillbridge-two-rosy.vercel.app
- Vercel: projeto prj_4VesTKrMGe7QykQqp0hk3mttNlna, workspace team_jhsC07ea1a2WswIDb28TygO6 (PedroGiffoni's projects), deploy de produção dpl_FnGJKhWRsyZP9LrAsskLr7W7SQVV: READY, aliases aplicados sem erro.
- API pública: https://skillbridge-api-pedrogiffoni.onrender.com
- Render: serviço srv-dbq5fuk9v7es73cjfcn0, workspace tea-d91f9gtaeets73fd5i20, Virginia, plano Free, um processo. Deploy dep-dbq5fv49v7es73cjfdrg: live.
- Commit da aplicação servido por ambos: a2adf8fa25468218067207ed2a60ce61f383ef9e, branch main. Registros posteriores de documentação não alteram o código testado.
- Criação Render pelo conector: build cd backend && pip install -r requirements.txt; start cd backend && sh start.sh; raiz do serviço é a do repositório (comandos entram em backend). PYTHON_VERSION=3.13.5.
- Vercel: VITE_API_BASE_URL=https://skillbridge-api-pedrogiffoni.onrender.com, alvo production. Novo build após configurar a variável.
- CORS_ORIGINS no Render limitado à origem https://skillbridge-two-rosy.vercel.app. O domínio estável acima deve ser usado para testes; outros aliases não foram autorizados no CORS.
- GEMINI_FREE_TIER_CONFIRMED=false, nenhuma chave Gemini enviada aos provedores nesta rodada. IA real continua pendente de modelo/cota e configuração exclusiva no backend. Sem banco ou recursos pagos criados.

### Evidências técnicas reais

- GET do frontend público: HTTP 200, HTML SkillBridge e bundle JS presentes. O bundle contém a URL pública correta do Render.
- GET /health no Render: HTTP 200 e status ok.
- GET /api/config: HTTP 200 e gemini_enabled=false.
- Respostas da API com Cache-Control: no-store e Access-Control-Allow-Origin para o domínio correto.
- POST /api/questionnaire em demo com profissão sintética Designer: HTTP 200, cinco competências e source_mode=demo.
- POST /api/assessment com níveis sintéticos 0,1,2,3,4: HTTP 200; lacunas 3,2,1,0,0; quatro semanas em ordem; source_mode=demo.
- Token adulterado: HTTP 409. Consentimento ausente/negado: HTTP 422.
- Preflight CORS permitido: HTTP 200. Origem desconhecida: HTTP 400, rejeitada.
- Navegador Edge na URL pública: início → perfil Designer sem dados pessoais → consentimento → questionário obtido da API Render (sem escolher demo local) → cinco respostas nível 2 → diagnóstico com cinco lacunas 1 → trilha de quatro semanas. Avisos de demonstração visíveis durante todo o fluxo de resultados. Dados apenas sintéticos; sem chamadas Google.
- Primeira versão do script HTTP de verificação falhou ao tentar ler a resposta textual OK do preflight como JSON; corrigida a leitura conforme Content-Type e o script completo passou. Não foi falha do produto.

Testes anteriores da mesma versão de código: 36 backend, 8 frontend, lint/build aprovados. Não se repetiram esses testes sem mudança de código nesta rodada; acrescentou-se a verificação real dos serviços publicados. Isto é teste técnico pelo agente, não validação com universitários ou pesquisa acadêmica.

### Limitações ainda abertas

Gemini real desativado. Render Free pode hibernar e reiniciar, invalidando tokens de sessão: se necessário, iniciar nova avaliação. Métricas com participantes, auditoria completa de acessibilidade, responsividade em todos os tamanhos e relatório final F108 continuam pendentes. Planos gratuitos seguem sujeitos às cotas oficiais; não foi configurado monitor artificial de disponibilidade nem contratado upgrade.

## Atualização Gemini — 11/11/2026
Gemini ativado após confirmação de cota gratuita no projeto SKILLBRIDGE e chave inserida pelo titular no backend Render. Modelo gemini-3.5-flash-lite; deploy dep-dbq5qhoae00c73ddhiag live; /api/config com gemini_enabled=true. Fluxo real publicado verificado no navegador, seis competências e quatro semanas. Evidências: [ativação](16-ativacao-gemini.md). Registros anteriores de modo demonstrativo permanecem como histórico.
