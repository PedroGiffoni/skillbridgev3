# Login, histórico e perfil do SkillBridge

A mudança na branch `developer-login` adiciona a área privada do estudante. O questionário inicia sem conta e o acesso é solicitado na conclusão. A conta do SkillBridge é gratuita. O acesso voluntário a Minhas avaliações também permite entrar para consultar resultados anteriores.

## Fluxo e dados

- E-mail com código de uso único ou botão Entrar com Google. No primeiro acesso, o sistema cria a conta. A vinculação a uma conta com e-mail já confirmado exige prova de acesso a esse endereço.
- O rascunho do questionário é temporário no navegador. O servidor valida a sessão antes de solicitar o diagnóstico ao Gemini e salva o resultado antes de responder.
- O histórico guarda data, profissão, lacunas, diagnóstico e trilha. O servidor consulta e exclui cada registro pelo identificador da conta autenticada. Reabrir uma avaliação usa o resultado salvo.
- O perfil é editável e opcional. Foto, nome de exibição, curso, semestre e objetivo profissional pertencem à conta. E-mail, identidade Google e dados do perfil ficam fora das entradas de geração de diagnóstico.

## Configuração local

1. Use `backend/.env.example` como referência para `backend/.env`. Configure o Gemini conforme as instruções do README.
2. Configure `AUTH_OTP_SECRET` com um valor aleatório de pelo menos 32 caracteres. Use a mesma chave entre reinícios para validar questionários emitidos no intervalo de validade. Mantenha o valor fora do código e dos logs.
3. Para e-mail, preencha o host, usuário, senha e endereço remetente SMTP. A porta padrão 587 usa STARTTLS. Para servidor com TLS implícito, configure a porta correspondente e `AUTH_SMTP_SSL=true`.
4. Para o Google, configure um cliente OAuth do tipo aplicativo da Web e informe seu ID em `AUTH_GOOGLE_CLIENT_ID`. Cadastre a origem exata aberta no navegador em **Origens JavaScript autorizadas**, como `http://localhost:5173`. O app recebe o ID público via `/api/auth/config`.
5. Inicie a API e o frontend conforme o README. Abra a URL do Vite cuja origem está cadastrada. O Vite encaminha `/api` ao FastAPI. O arquivo SQLite fica no caminho `AUTH_DB_PATH`, com padrão `backend/data/skillbridge.sqlite3`.

A sessão usa cookie de aplicação. Em HTTPS, configure `AUTH_COOKIE_SECURE=true` e inclua a origem do frontend em `CORS_ORIGINS`. O frontend chama `/api` na própria origem. O Vercel encaminha a rota para o backend configurado em `frontend/vercel.json`.

### Login local com endereço de teste

Quando `GET /api/auth/config` retorna `email_enabled: false` e `google_client_id: null`, configure um dos métodos de entrada ou use o [servidor de teste local](../README.md#testar-o-login-local). Ele roda apenas no localhost e entrega o código para `aluno@example.test` em um arquivo ignorado pelo Git. A chave de assinatura tem seu próprio arquivo. As contas e o histórico ficam em um SQLite separado do servidor normal. Depois de mudar de servidor, inicie outro questionário para usar a chave correspondente. O login pode ser verificado em **Minhas avaliações**, independentemente da disponibilidade do Gemini.

Uma publicação com histórico precisa de armazenamento durável para o SQLite e de um transporte de e-mail acessível pelo backend. A configuração gratuita do Render registrada na V1 tem disco efêmero e bloqueia as portas SMTP padrão. Confirme as condições da hospedagem antes de ativar o login publicado. [Render Free](https://render.com/docs/free) · [Configuração do cliente Google](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid)

## Rastreabilidade

| Requisito | Interface | API | Verificação |
| --- | --- | --- | --- |
| Questionário público e diagnóstico após entrar | Autoavaliação e acesso gratuito | `POST /api/questionnaire`, `POST /api/assessment` | Visitante gera perguntas, recebe 401 no diagnóstico e pode continuar após entrar |
| Código e Google | Tela de acesso | `/api/auth/email/*`, `/api/auth/google` | Código inválido, vínculo confirmado e continuação da avaliação |
| Histórico privado | Meu histórico | `GET /api/history`, `GET/DELETE /api/history/{id}` | Persistência após reinício, uma entrada por submissão e isolamento entre contas |
| Perfil com foto | Meu perfil | `GET /api/account`, `POST /api/account/profile` | Edição opcional, foto substituível e remoção |

## Verificação local

- `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` na raiz. 76 testes passaram, com o aviso de depreciação Starlette/httpx já observado na V1.
- `backend/.venv/Scripts/python.exe -m pip check` na raiz. Dependências compatíveis.
- `npm test`, `npm run lint` e `npm run build` em `frontend`. 27 testes, lint e build passaram. O build informa que o chunk já existente de Three.js ultrapassa 500 KiB.
- Os testes exercitam as rotas e SQLite temporário, com serviços externos simulados. Permanecem pendentes o teste em navegador com credenciais reais de Google e SMTP e a validação do armazenamento na hospedagem.

## Ambiente de testes da V2

| Serviço | Endereço | Origem |
| --- | --- | --- |
| Interface | [SkillBridge V2](https://skillbridge-v2-login.vercel.app) | Projeto Vercel `skillbridge-v2-login`, branch `developer-login` |
| Backend | [Saúde da API V2](https://skillbridge-api-v2-login.onrender.com/health) | Render Free no workspace Hobby `SkillBridge V2 Testes` |

O Vercel encaminha `/api/*` exclusivamente à API V2. O Render usa `cd backend && pip install -r requirements.txt` para build e `cd backend && sh start.sh` para iniciar. O endereço Vercel da V2 deve ser cadastrado em `CORS_ORIGINS` e, depois de configurar o cliente Google da V2, como origem JavaScript autorizada.

O objetivo desta publicação é verificar interface, proxy e proteção de rotas. O Render Free usa SQLite efêmero e restringe as portas SMTP padrão. A ativação do fluxo completo depende de credenciais próprias de Gemini e Google e da configuração de e-mail e armazenamento para o ambiente escolhido. [Limites do Render Free](https://render.com/docs/free)

A cópia exata do primeiro commit de login, sem os estudos locais de personagens, passou em 76 testes de backend, 21 de frontend, lint e build.

## Aplicação principal

A branch `main` usa o endereço original da aplicação e o serviço Render `skillbridge-api-pedrogiffoni`. O Vercel encaminha `/api/*` para esse backend na mesma origem. Para habilitar o Google no ambiente principal, cadastre `https://skillbridge-two-rosy.vercel.app` como origem JavaScript autorizada e configure `AUTH_GOOGLE_CLIENT_ID`, `AUTH_OTP_SECRET`, `AUTH_COOKIE_SECURE=true` e `CORS_ORIGINS` no serviço principal. O fluxo completo exige Gemini e pelo menos um método de entrada. O histórico publicado precisa de armazenamento durável para sobreviver a reinícios.
