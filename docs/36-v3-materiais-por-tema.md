# SkillBridge V3 — Materiais por tema

Em **Meus cursos**, abra um curso e selecione uma lição já preparada. Entre em **Materiais do tema**, autorize o envio do conteúdo pedagógico da lição e escolha **Preparar materiais**. Os seis formatos partem da mesma revisão salva.

| Formato | O que aparece |
| --- | --- |
| Videoaula | Slides com exemplos, diagrama de etapas e transcrição por cena. Ao gerar a narração, o player sincroniza a mudança de slide ao fim da faixa. |
| Audiolivro | Um capítulo com seções, texto para leitura e narração por seção. |
| Podcast | Uma conversa entre apresentador e especialista, com duas vozes sintéticas e transcrição identificada por locutor. |
| Mapa mental | Tópico central e ramos expansíveis pelo teclado ou toque. |
| Quiz | Três questões de revisão, com feedback depois de cada resposta. |
| Simulado | Quatro ou cinco questões de aplicação, com pontuação e feedback após enviar todas as respostas. |

Quiz e simulado são prática formativa. A prova de domínio, o mínimo de 80% e os desbloqueios pertencem ao Sprint 6.

## Configuração de Gemini

A preparação usa as variáveis existentes `GEMINI_API_KEY`, `GEMINI_MODEL` e `GEMINI_FREE_TIER_CONFIRMED`. Para sintetizar voz, configure também `GEMINI_TTS_MODEL` com um modelo que aceite geração de WAV e duas vozes na API Interactions. O projeto sinaliza o áudio como indisponível até que `GEMINI_TTS_FREE_TIER_CONFIRMED` esteja habilitado. Confirme o modelo, a cota ativa e o plano gratuito no Google AI Studio antes de habilitar. As variáveis e a chave ficam no backend. [Geração de voz do Gemini](https://aistudio.google.com/docs/speech-generation) · [Limites por projeto](https://aistudio.google.com/docs/rate-limits#current-rate-limits)

Cada formato falado tem seu próprio pedido de consentimento. A preparação envia título, objetivo, explicação, exemplo e resumo, sem dados da conta ou respostas da avaliação. A síntese usa o texto validado dos materiais. O podcast usa duas vozes do catálogo do Gemini e não coleta amostras de voz. O player monta a videoaula com HTML e áudio, sem serviço de geração de cenas. Na configuração padrão, as chamadas compartilham o limite do backend e os arquivos prontos são reaproveitados.

## API e armazenamento

As rotas abaixo usam o prefixo privado `/api/lessons/{id}/materials` e exigem a conta titular da revisão da lição.

| Método e caminho relativo | Contrato |
| --- | --- |
| `GET /` | Consulta o estado, os seis formatos validados e as gravações disponíveis. |
| `POST /` | Enfileira a preparação com `consent: true`. Uma nova tentativa explícita informa `retry_attempt`. |
| `POST /audio/{kind}` | Enfileira a narração sob demanda para `video`, `audiobook` ou `podcast`. |
| `GET /audio/{kind}/{segment}` | Reproduz um trecho WAV da revisão pronta. Aceita um intervalo de bytes para navegação no áudio. |
| `POST /{kind}/grade` | Corrige `quiz` por questão ou `simulation` após todas as respostas. O gabarito fica no servidor. |

A migração aditiva 5 cria `theme_jobs` e `theme_audio`. A chave por revisão e formato impede duplicar jobs. Segmentos já gravados da mesma configuração são reaproveitados após falha. A fila tem prazo por chamada, intervalo após atingir a cota e limite de três execuções por job. Os materiais validados e as gravações prontas continuam acessíveis após reinício ou desligamento da geração. As tabelas anteriores não são reconstruídas. A exclusão de uma avaliação por seu titular remove os materiais associados em cascata.

O WAV é gravado no mesmo SQLite privado. Antes de operar com dados reais e publicar, valide tamanho, durabilidade, backup e restauração do banco na hospedagem. O ensaio ao vivo com as duas vozes e o modelo de texto depende de cota confirmada no projeto.

## Verificações locais

- `python -B -m pytest -p no:cacheprovider -q` em `backend`. 137 testes passaram. A suíte cobre consentimento, privacidade, deduplicação, recuperação de segmentos, correção, faixas de áudio, reinício, cascata e contrato do SDK com transporte simulado.
- `npm run test`, `npm run lint` e `npm run build` em `frontend`. 45 testes passaram, assim como lint e build. Os testes cobrem escolha do formato, consentimento e correção, mudança de slide e recuperação de jobs.
- Edge a 320 px. Abri os seis formatos, reproduzi a videoaula e o áudio do podcast, confirmei o avanço automático de cenas, abri um ramo do mapa pelo teclado e corrigi quiz e simulado. Os arquivos salvos reapareceram ao recarregar e a tela não teve rolagem horizontal.
- O ensaio usou uma conta e um banco temporários, texto simulado e WAV de teste. A inspeção com `git diff --check` também passou. Permanecem os avisos de depreciação do TestClient e do tamanho do chunk Three.js. A naturalidade do português, a distinção das vozes e a duração real de geração dependem da validação com o provedor.

## Arquivos alterados

- Backend. `backend/app/theme_content.py`, `theme_materials.py`, `theme_tts.py`, `config.py`, `history.py` e `main.py`.
- Frontend. `frontend/src/ThemeMaterials.tsx`, `theme-api.ts`, `theme.css` e `CourseLibrary.tsx`.
- Testes. `backend/tests/test_theme_materials.py`, `test_theme_tts.py`, `test_learning.py` e `frontend/src/ThemeMaterials.test.tsx`.
- Configuração e documentação. `.env.example`, `backend/.env.example`, os dois READMEs, o plano mestre, o Kanban e o registro de decisões.
