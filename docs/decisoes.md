# Registro de decisões

- 10/11/2026 — Público: universitários buscando primeiro emprego.
- 10/11/2026 — Profissões: campo livre, com critérios gerados pela IA e apresentados como estimativas.
- 10/11/2026 — Entrada: questionário, sem upload de currículo.
- 10/11/2026 — Provedor principal: Gemini API em modalidade gratuita, conforme disponibilidade real.
- 10/11/2026 — Visual: híbrido profissional/tecnológico.
- Pendente — hospedagem, escolha do modelo Gemini elegível, integrantes, pesquisa com usuários, evidências reais.

- 10/11/2026 — Fases 0 e 1 autorizadas juntas. Protótipo em memória, competências e trilha genéricas rotuladas; sem API, Gemini ou deploy. SQLite condicionado a necessidade real. Referência demo fixa 3/4, backend será autoritativo na Fase 2. Ver docs/11-auditoria-plano.md.

- 10/11/2026 — Usuário aprovou o protótipo e solicitou Gemini; implementadas base FastAPI (Fase 2) e integração preparada (Fase 3) com testes mockados. SQLite dispensado por ausência de necessidade. Modelo e cota da conta ainda pendentes, chamadas reais desativadas. Sem deploy. Ver docs/13-integracao-gemini.md.
- 10/11/2026 — Questionário protegido por token HMAC efêmero, prazo 1h, sem banco. Sem retries automáticos SDK; nova tentativa manual limitada globalmente por processo. Consentimento informa envio ao Google e termos do serviço gratuito.

- 10/11/2026 — Usuário solicitou criar repositório e subir o projeto. Criado PedroGiffoni/skillbridge privado por padrão. Versionamento inclui código, testes e documentação; .env e artefatos locais excluídos. Não constitui deploy nem avanço de fase. Ver docs/14-repositorio-github.md.

- 10/11/2026 — Usuário autorizou publicar no Render e Vercel (Fase 4). Backend Python no Render Free e interface Vite na Vercel Hobby; sem recursos pagos. Frontend terá URL pública configurável e CORS restrito no backend. Gemini hospedado seguirá desativado até confirmar modelo/cota gratuita. Status real em docs/15-publicacao.md.

- 11/11/2026 — Publicação efetiva em https://skillbridge-two-rosy.vercel.app (frontend) e https://skillbridge-api-pedrogiffoni.onrender.com (backend Free), ambos verificados. CORS restrito ao domínio estável Vercel; API URL configurada no build de produção. Gemini permanece desativado, sem upload da chave local. Dados sintéticos usados somente para teste técnico.

- 11/11/2026 — Cota gratuita conferida no projeto SKILLBRIDGE; escolhido gemini-3.5-flash-lite (15 RPM/500 RPD observados). Duas chamadas reais locais aprovadas com dados sintéticos. Configuração não secreta enviada ao Render; chave e teste online ainda pendentes. Preferência permanente de README registrada no Segundo Cérebro. Ver docs/16-ativacao-gemini.md.

- 11/11/2026 — Titular adicionou chave no Render; deploy dep-dbq5qhoae00c73ddhiag live e gemini_enabled=true. Fluxo real no navegador aprovado (6 competências, diagnóstico orientativo e 4 semanas). Capturas reais e resultados em docs/16-ativacao-gemini.md.

- 11/11/2026 — A pedido do usuário, aprofundar avaliação para 20 perguntas: 8 competências práticas (5 técnicas, 3 transversais no contexto profissional) + 12 perguntas contextuais opcionais. Contexto não pontua nem altera lacunas; orienta planejamento de 4 semanas. Mesmas duas chamadas Gemini e estado somente em memória. Ver docs/17-questionario-aprofundado.md.

- 11/11/2026 — Questionário aprofundado publicado e verificado no navegador: 20 perguntas, diagnóstico contextualizado e trilha em blocos de 1h respeitando 2h/semana informadas no cenário sintético. Não equivale a comprovar melhoria com usuários reais. Evidências no registro 17.

- 11/11/2026 — A pedido do usuário, interface pública revisada com linguagem de produto: removidas menções ao trabalho acadêmico, F108, Unifor, ODS e pendências de pesquisa na tela de conclusão. Preservados público universitário, consentimento, limites da autoavaliação e identificação de demonstração. Documentação acadêmica permanece nos arquivos internos.

- 11/11/2026 — Apresentação em PPTX editável e HTML independente, com animações adaptadas a cada formato. Identidade visual do SkillBridge, capturas reais e notas de fonte. Nenhuma entrevista ou validação alegada. Entregas locais; sem publicar o material externamente.

- 11/11/2026 — Versão HTML da apresentação para celular com layout vertical próprio, em vez de reduzir o slide 16:9. Publicar em /apresentacao.html no mesmo frontend Vercel, sem backend adicional ou custo. Arquivo independente também disponível para download.

- 11/11/2026 — Usuário pediu manter a apresentação horizontal também no celular. Rota /apresentacao.html passa a usar slides 16:9 com escala proporcional, navegação por toque e orientação para girar o aparelho. Aplicativo principal preservado.

- 17/11/2026 — Substituir a escala textual genérica por cinco alternativas contextualizadas por competência (0–4), geradas na mesma chamada Gemini. A opção descreve prática autodeclarada, sem gabarito. Nível 4 não exige ensinar terceiros. Pydantic e frontend validam cobertura, ordem, limites e duplicatas; diagnóstico recupera o rótulo assinado. Lacuna determinística preservada. Ver docs/20-alternativas-contextualizadas.md.

## 17/11/2026 — Temas e movimento
Adotar tokens claro/escuro com preferência local exclusiva de aparência. Usar Motion respeitando movimento reduzido e Three.js dinâmico para ornamento de quatro segundos; nenhuma animação contínua no questionário. Preservar aplicação e apresentação em rotas distintas. Ver registro 21.

## 17/11/2026 - Registro visual em PDF
Organizar as 25 capturas fornecidas em documento de 27 páginas, com imagens integrais, títulos, legendas e índice. Não apresentar capturas como validação com usuários. Registro 22 e artefato em output/pdf.

## 17/11/2026 - Primeiros personagens 3D
Produzir dois GLB originais com modelagem procedural e articulações rígidas, quatro clips e prévia própria em /personagens.html. Aguardar revisão do acabamento antes de inserir nas telas da jornada. Aplicação e apresentação preservadas. Ver registro 23.

## 17/11/2026 - Fluidez dos personagens
Substituir poses lineares por curvas amostradas com envelope suave e combinar ações com fades, sem reset instantâneo nas trocas. Preservar rig atual e registrar limites; ver registro 24.

## 18/11/2026 — Avaliação exclusivamente com Gemini
A pedido explícito do usuário, retirar o modo sem IA e o fallback demonstrativo, substituindo a regra anterior. Questionário, diagnóstico e trilha exigem Gemini; falhas produzem erros HTTP recuperáveis, preservando respostas no cliente para nova tentativa. Fixtures genéricas ficam restritas aos testes offline. Sem novas chamadas reais de IA nesta revisão. Ver registro 27.

## 19/11/2026 — Recuperação limitada de falha temporária Gemini
Após relato de indisponibilidade e reprodução real de ServerError 503, permitir no máximo duas tentativas totais para HTTP 500/502/503/504 com pausa de 1 s, dentro do mesmo prazo global. Não repetir automaticamente erro de cliente/acesso/modelo, 429, timeout global ou JSON inválido. Distinguir categorias e registrar apenas status/categoria/tentativa. Não mudar modelo, chave, plano de hospedagem ou reintroduzir demonstração. Ver registro 28.

## 20/11/2026 — Login, histórico e perfil
Na branch `developer-login`, a autoavaliação é pública. A entrada gratuita por código de e-mail ou Google aparece na conclusão, com retomada do rascunho. O FastAPI protege a geração do diagnóstico e guarda o resultado em SQLite por conta. O perfil com foto e dados opcionais é privado. A publicação depende de credenciais, transporte de e-mail acessível e armazenamento durável. Ver [registro 30](30-login-historico-perfil.md).

## 20/11/2026 — Alternativas em todas as perguntas da V2

Substituir as respostas livres da autoavaliação e do contexto por alternativas de escolha. Manter 8 competências, 12 perguntas contextuais opcionais e a possibilidade de pular. A situação de prática por competência passa a ser opcional e categórica. O cálculo das lacunas continua baseado nos níveis 0 a 4. Ver [requisitos da V2](02-requisitos.md#questionário-de-alternativas-na-v2).

## 20/11/2026 — Carreiras de tecnologia na V2

Posicionar a página inicial para universitários que buscam o primeiro estágio ou emprego em tecnologia. Oferecer o mesmo catálogo de 72 opções por navegação em 12 áreas ou por busca com sugestões. Exigir a confirmação de uma carreira e validar seu rótulo antes de iniciar a geração. O catálogo restringe novas avaliações. A profissão armazenada continua visível em resultados anteriores. Ver [requisitos da V2](02-requisitos.md#catálogo-de-carreiras-na-v2).


## 20/11/2026 — Base da SkillBridge V3 e compatibilidade histórica

A branch local `V3` parte da `main` em `3dff00b`, já com o PR de integração da V2, e foi selecionada em um checkout separado. A proposta de Sprint 1 mantém os JSON de quatro semanas sem regravação e usa versão explícita nos resultados novos, com leitura compatível das duas versões. O primeiro PR proposto prepara os leitores e a fixture legada antes de habilitar a geração de 12 semanas. O [relatório de S0](AUDITORIA_V3.md) registra o baseline, os critérios de aceite e o rollback.

## 20/11/2026 — Sprint 1 da V3

A API grava novos diagnósticos com versão 3 e 12 semanas. Leitura e reenvio aceitam os resultados versionados e os registros de quatro semanas. O SQLite mantém o JSON original. O seletor de recuperação troca apenas a geração futura. [Contrato, recuperação e testes](31-v3-trilha-12-semanas.md).

## 20/11/2026 — Sprint 2 da V3

O SQLite recebe tabelas aditivas para planos, semanas e versões de curso. A transação que conclui uma avaliação V3 também salva a revisão inicial. O catálogo canônico mantém a busca local e serve de fonte para o endpoint público e para a validação da API. [Contrato, migração e testes](32-v3-persistencia-catalogo.md).

## 20/11/2026 — Sprint 3 da V3

A geração de blueprint usa fila SQLite e reaproveita jobs por revisão do plano, modelo e versões de prompt e schema. A conclusão salva uma revisão privada de rascunho na mesma transação. Uma tentativa explícita exige consentimento e o número observado da última falha. [Contrato e verificação](33-v3-blueprint-gemini.md).


## 20/11/2026 — Sprint 4 da V3

A biblioteca da conta publica revisões separadas de blueprints já validados. A geração de uma lição exige autorização explícita e grava uma revisão imutável depois de validar o exercício. A leitura do conteúdo salvo reutiliza a mesma revisão. [API e verificações](34-v3-biblioteca-microlicoes.md).

## 20/11/2026 — Sprint 5 da V3

A API corrige exercícios com base na revisão publicada e salva o resultado de cada tentativa na migração aditiva 4. O primeiro acerto conclui a prática. A dica de treino tem recibo assinado e o reenvio reaproveita o mesmo ID. O player recupera o progresso da conta. [Contrato, migração e verificações](35-v3-player-pratica.md).

## 20/11/2026 — Materiais por tema da V3

Cada revisão de lição pode ter seis materiais gerados a partir do mesmo conteúdo. O Gemini prepara o pacote textual e sintetiza voz sob demanda com consentimento separado. A migração aditiva 5 registra jobs e trechos WAV privados, que são reaproveitados na reabertura ou após falhas. O quiz e o simulado usam correção determinística no servidor. [Contrato, configuração e verificações](36-v3-materiais-por-tema.md).

## 21/11/2026 — Sprints 6 a 8 da V3

Todas as competências declaradas em um módulo contam como críticas na prova de dez itens. A API exige pelo menos 80% e um acerto por competência antes de liberar dependentes. Os painéis leem evidências persistidas. O tempo informado pelo aluno e o replanejamento preservam as revisões e os registros anteriores. A qualidade administrativa usa contas verificadas autorizadas e suprime agregados pequenos. [Regras, migrações, verificação e piloto](37-v3-dominio-dashboards-release.md).

## 21/11/2026 — Validação na cota gratuita

O ensaio sintético percorreu questionário, trilha, curso, prova e painel com Gemini real. Os seis materiais e as gravações das três modalidades faladas foram verificados em um tema de SQL. A geração de cursos usa um esquema de resposta simplificado e conserva a validação completa da V3. O Render Free não oferece disco persistente para o SQLite da plataforma. [Resultados e roteiro do piloto](38-v3-ensaio-gratuito-piloto.md).

## 21/11/2026 — Publicação de testes da V3

A V3 usa a `main` de um repositório dedicado que incorpora o histórico original. A interface na Vercel Hobby encaminha `/api/*` na mesma origem para um serviço Python separado no Render Free. A configuração permite a origem HTTPS estável da Vercel e mantém cookies seguros.

Verifiquei a interface, `/health`, a versão OpenAPI 0.3.0, o catálogo pelo proxy e o retorno HTTP 401 de cursos sem sessão. A geração e o login hospedados dependem de credenciais no Render. O banco é efêmero e o ambiente serve para testes com dados sintéticos. [Interface de testes](https://skillbridgev3.vercel.app) · [Saúde da API](https://skillbridge-v3-api-pedrogiffoni.onrender.com/health)
