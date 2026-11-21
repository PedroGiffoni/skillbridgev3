# SkillBridge V3 — Ensaio com Gemini real e plano de piloto

## Configuração confirmada em 21/11/2026

O Google AI Studio mostrou o projeto SKILLBRIDGE no nível gratuito. A chave já configurada no backend local corresponde à credencial mascarada desse projeto. Os ensaios usaram modelos que exibiam cota ativa e um SQLite temporário. O e-mail de teste foi simulado. As chamadas ao Gemini receberam apenas exemplos pedagógicos e perfis fictícios. [Limites por projeto](https://aistudio.google.com/docs/rate-limits#current-rate-limits)

| Modelo | Limite observado no projeto | Uso |
| --- | --- | --- |
| Gemini 3.5 Flash Lite | 15 solicitações por minuto e 500 por dia | Questionário, trilha e pacote multimodal inicial. |
| Gemini 3.1 Flash Lite | 15 solicitações por minuto e 500 por dia | Repetição controlada de texto durante indisponibilidade. |
| Gemini 3.8 Flash Lite TTS | 3 solicitações por minuto e 10 por dia | Áudio da videoaula, audiolivro e podcast. |

## Resultados observados

| Cenário | Resultado |
| --- | --- |
| Diagnóstico de Análise de Dados | Questionário real com 8 competências e trilha real de 12 semanas. |
| Materiais reais de JOINs em SQL | Duas gerações completas a partir da mesma lição sintética. Ambas disponibilizaram slides, capítulo, roteiro de podcast, mapa, quiz e simulado. |
| Podcast | O modelo gerou um WAV de 64,9 segundos para um roteiro de 10 falas e duas vozes configuradas. Verifiquei a leitura parcial por intervalo, o quiz e a reabertura do mesmo áudio após reinício. |
| Videoaula | Os três trechos WAV ficaram disponíveis pela API e somaram 39,2 segundos. |
| Audiolivro | As três seções narradas ficaram disponíveis pela API e somaram 65,6 segundos. |
| Geração da estrutura do curso | O primeiro ensaio reproduziu HTTP 400 causado pela complexidade do esquema de saída. O esquema enviado ao Gemini foi simplificado. O backend preservou a validação Pydantic e as regras de cobertura da trilha. O prompt passou a pedir quatro módulos de três semanas, uma microlição por semana e cobertura de todos os IDs previstos. |
| Fluxo completo, do questionário ao painel | Depois do ajuste, o Gemini 3.5 Flash Lite gerou o questionário, a trilha e o curso com quatro módulos. Uma microlição foi gerada e reaberta na biblioteca. A prova de 10 questões foi corrigida pelo servidor e o painel registrou 50 XP pela aprovação de teste. |

As locuções de videoaula e audiolivro foram solicitadas com espaçamento de pelo menos 22 segundos entre chamadas de voz no ensaio, respeitando a cota observada. O aplicativo salva trechos já gerados para reaproveitar em caso de erro. O ensaio preservou uma cópia de `skillbridge-podcast-joins-validacao.wav` e o roteiro para revisão. SHA-256 do WAV `d04625fc19266a87b11e0be2b2fc9f49be83809e640fea46dc1771fb14499445`.

## Regressão técnica

A estrutura de curso recebeu uma projeção de JSON Schema menos complexa para a API do Gemini. Tipos, campos e enumerações continuam explícitos. Limites de tamanho, IDs e cobertura continuam verificados no backend antes de publicar uma revisão para a conta. A nova revisão do prompt não altera cursos publicados. Durante o ensaio houve respostas 503 intermitentes. Na última execução, a retentativa existente recuperou o job do curso.

O comando `python -B -m pytest -p no:cacheprovider -q` executado em `backend` passou com 144 testes. O comando `python -B -m pytest -p no:cacheprovider -q tests/test_course_generation.py` passou com 18 testes após o ajuste final do prompt. Na execução real, as verificações do fluxo passaram antes de o coletor de arquivos temporários do Windows sinalizar um arquivo SQLite aberto. A verificação e a limpeza do arquivo sintético foram tratadas separadamente do resultado da API.

## Hospedagem e decisão de piloto

O painel do Render confirmou o backend existente na branch `main`, com instância Free e sem disco persistente disponível. O SQLite desse serviço é efêmero. A V3 guarda histórico, cursos, provas, XP e WAV no arquivo SQLite, portanto a publicação desse conjunto com contas reais depende de armazenamento durável. [Limitações do Render Free](https://render.com/docs/free#local-files-lost-on-redeploy)

O piloto sem contratação pode acontecer presencialmente, em um computador com o checkout local da V3, um banco dedicado e backup restaurado em cópia. O protocolo acadêmico pede pelo menos dez universitários adultos reais, com consentimento informado e registros anônimos. Valide login e revise uma amostra de conteúdo antes da primeira sessão. A separação por códigos evita vincular e-mails das contas de teste à planilha acadêmica. [Protocolo F108](07-metricas-validacao.md)

| Bloco | Tarefas observáveis |
| --- | --- |
| Diagnóstico e trilha | Escolher a carreira, concluir o questionário, explicar a lacuna principal e localizar a primeira ação da trilha. |
| Curso e materiais | Abrir uma lição, escolher um formato, consumir o material e achar o quiz ou a transcrição. |
| Domínio e retomada | Localizar critérios da prova, encontrar o reforço após erro e retomar a lição pelo painel. |

Em cada sessão, registre apenas o código, tarefa, conclusão sem ajuda, duração, erros ou bloqueios, compreensão da lacuna e nota de utilidade de 1 a 5. As metas acadêmicas de conclusão, compreensão e utilidade são de 80%. O tempo é exploratório para a versão atual de 20 perguntas. Registre dificuldades qualitativas sem nomes, e-mails, rostos ou exemplos pessoais.

A cota de voz deve ser contada por projeto. Para comparar a experiência de ouvir e navegar com dez voluntários, o mesmo exemplo de áudio aprovado pode ser reapresentado, e a geração individual fica reservada a um ensaio separado conforme a cota. A coleta de participantes permanece pendente.

## Arquivos desta etapa

- `backend/app/blueprint.py`, `backend/app/blueprint_jobs.py`, `backend/app/gemini.py` e `backend/tests/test_course_generation.py`.
- Este relatório, o registro de decisões e o Kanban.
