# Apresentação SkillBridge — 11/11/2026

Pedido: apresentação PowerPoint e versão HTML com movimento e animações, para comunicar a proposta aos beneficiários e apresentar na atividade. As capturas da plataforma foram tratadas como referência dos objetivos de comunicação, sem afirmar que a conversa com beneficiários já aconteceu.

Entregas locais em outputs/apresentacao: PowerPoint editável de 12 slides 16:9, com notas de fala, 12 transições e 56 entradas animadas; HTML independente com tipografia em movimento, contador, movimento de capturas, avanço automático e redução de movimento; guia de uso. Nenhuma alteração na aplicação publicada.

Conteúdo: problema como hipótese, público universitário, fluxo, 20 perguntas, contexto, lacunas determinísticas, diagnóstico, exemplo de quatro semanas, privacidade, estado atual e convite a experimentar e compartilhar impressões. Fontes e ressalvas nas notas de fala. Capturas reais dos registros 17/18; respostas sintéticas identificadas. Sem entrevistas ou validações inventadas.

Verificação: 12 slides renderizados e revisados individualmente. Validador de integridade, geometria, fontes Segoe UI e importação Artifact Tool aprovados. XML confirmou 12 transições e 56 entradas. HTML com 12 slides e imagens incorporadas, sem dependências de rede; JavaScript passou em node --check. Navegação, contador, controles de reprodução, movimento reduzido e encerramento conferidos em navegador local. Não houve inspeção no aplicativo PowerPoint; reprodução nativa das animações pode variar entre visualizadores. Relatórios técnicos e fontes intermediárias ficam no diretório privado de build, não nas entregas.

A pesquisa com universitários continua pendente. A produção destes materiais não representa realização de ação de extensão ou coleta de feedback.


## Versão para celular

A pedido do usuário, versão vertical independente em outputs/apresentacao/SkillBridge-celular.html e cópia pública em frontend/public/apresentacao.html. Mantém 12 slides, texto a partir de 18px no corpo, rolagem natural, botões de 48px, avanço/volta, contador, animações de entrada, redução de movimento e ampliação de capturas por toque. Imagens incorporadas, sem dependências externas. Rota pública: https://skillbridge-two-rosy.vercel.app/apresentacao.html.

Teste de viewport no navegador: 390×844 e 360×800, sem largura horizontal excedente no conteúdo. Em 360px: 12 seções, texto de corpo 18px e botões inferiores de 48px. Ampliação e fechamento de imagem, navegação e redução de movimento conferidos. Teste de tela simulada não equivale a teste em aparelho físico.

Publicação móvel verificada: commit 724446b, Vercel dpl_BWxLrmpbPxVxy9R5xUyLdrgnGCfL READY. Página abriu no domínio estável e navegação pública até a seção 2 funcionou. Build frontend aprovado; JavaScript passou em node --check; arquivo para download idêntico à cópia pública, com 12 seções e imagens incorporadas. Captura técnica em assets/apresentacao-celular.jpg. Viewport temporário restaurado ao final.

## Preferência final: horizontal no celular
Usuário solicitou manter o formato horizontal. A rota /apresentacao.html e o arquivo SkillBridge-celular.html passam a usar os slides 16:9 com escala proporcional, controles de toque compactos, suporte a gesto lateral e sugestão de girar o aparelho. Os registros da versão vertical acima permanecem como histórico. Aplicação principal na raiz preservada.

Atualização horizontal verificada: commit 4b52fbb, deploy Vercel dpl_29EZYBN7sDrfNpXDoKaMkPQy4dmq READY. Em viewport 844×390, proporção observada 1,78 (16:9), rodapé dos slides em y=309 e controles a partir de y=324, sem sobreposição. Navegação pública até o slide 2 aprovada; viewport restaurado. Build e node --check aprovados. Evidência: assets/apresentacao-horizontal-celular.jpg.
