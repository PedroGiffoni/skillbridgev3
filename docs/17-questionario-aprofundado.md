# Questionário aprofundado — 11/11/2026

Pedido: cerca de 20 perguntas com mais contexto para a orientação. Implementação: 8 perguntas práticas geradas pelo Gemini e 12 perguntas contextuais fixas, relacionadas à profissão escolhida. Contextuais opcionais e puláveis, com até 500 caracteres cada. Sem afirmar eficácia superior antes de pesquisa real.

## Conteúdo e uso

Competências: cinco técnicas/práticas da área e três transversais em situações da profissão; escala 0–4, exemplo opcional sobre situação, ação, apoio e resultado. Contexto: motivação, experiência, projeto, ferramentas, resolução de problema, colaboração, feedback, dificuldade, estratégia de aprendizagem, disponibilidade semanal, recursos e objetivo concreto em quatro semanas. Não exige emprego anterior.

A segunda chamada recebe perguntas e respostas contextualizadas, competências, exemplos e lacunas. O prompt pede evidências autodeclaradas, reconhecimento de contradições/ausências, até três frentes prioritárias, carga ajustada ao tempo, ações compatíveis com recursos e entregáveis observáveis. Branco significa não informado; nenhuma resposta qualitativa entra no cálculo de lacunas. Continua sendo orientação educacional, sem certificação.

## Contratos, privacidade e compatibilidade

`AssessmentRequest.context`: mapa opcional de até 12 chaves conhecidas, valores normalizados, até 500 caracteres por resposta; chaves desconhecidas ou valores inválidos retornam 422. Catálogo backend/frontend conferido por teste. Corpo HTTP limitado a 64 KiB para acomodar contexto, token e exemplos; saída Gemini continua limitada a 24 KiB/6.000 tokens. Timeout/429/fallback e duas chamadas por avaliação preservados.

Geração nova exige oito competências; contratos de leitura mantêm 5–8 para compatibilidade durante atualização. Recarregar a interface pode ser necessário após publicação; questionários em andamento expiram quando a API reinicia. Demonstração tem oito competências genéricas e doze contextuais, sem análise IA das respostas. Contexto não é persistido e é apagado ao reiniciar. Consentimento já contempla respostas enviadas ao Google; avisos pedem não incluir dados pessoais/sensíveis.

## Rastreabilidade e arquivos

RF03–05/RF07 → SB03/SB08 → telas questions/context → `/api/questionnaire` e `/api/assessment` → testes de fluxo, revisão, contexto, limites e cálculo.

- Backend: `app/context.py`, `schemas.py`, `main.py`, `demo.py`, `tests/test_api.py`.
- Frontend: `src/context.ts`, `App.tsx`, `api.ts`, `demo.ts`, `App.test.tsx`, `integration.test.tsx`.
- Documentação: README, requisitos, escopo, integração Gemini, métricas, decisões, Kanban e este registro.

## Verificação técnica

- `.venv/Scripts/python.exe -m pytest -q` em backend: 41 aprovados; aviso preexistente Starlette/httpx.
- `npm test` em frontend: 8 aprovados, incluindo as vinte perguntas, revisão e contexto enviado após consentimento.
- `npm run lint` e `npm run build`: aprovados.
- Primeiro teste de catálogo revelou erro de codificação na exportação; corrigido com leitura UTF-8 explícita e suíte repetida com sucesso.

## Publicação e teste real desta versão

Commit funcional `128f3b1ad23ce8ccbd054aab56673b2e120e5433`. Render `dep-dbqg9o59el5s73esc640`: live. Vercel `dpl_CbHeycQpDajy55N2b3rTbmFAkFSb`: READY, production. Mesmo domínio público: https://skillbridge-two-rosy.vercel.app.

Teste técnico pelo navegador com profissão Desenvolvedor frontend júnior e respostas exclusivamente sintéticas: oito competências geradas pelo Gemini, progresso de 1/20 a 20/20, oito níveis 2 e onze respostas contextuais preenchidas; pergunta sobre feedback pulada. Navegação por teclado conferida nas competências e no contexto. Não é uma auditoria completa de acessibilidade.

Diagnóstico e trilha identificados como conteúdo Gemini. Resumo considerou duas horas semanais, recursos gratuitos, dificuldade em eventos JavaScript e objetivo de página responsiva com formulário validado. Trilha exibiu quatro semanas, duas ações de uma hora em cada semana e entregáveis relacionados ao objetivo. Campo pulado foi descrito como ausência de informação, sem alterar lacunas: todas conferidas como zero para referências 1 ou 2 e nível autodeclarado 2. Duas chamadas reais nesta rodada, sem repetição.

Evidências novas: [pergunta 20/20](assets/questionario-20-contexto.jpg) e [diagnóstico contextualizado](assets/questionario-20-diagnostico.jpg). Sem participantes reais, métricas de usabilidade ou afirmação de eficácia superior nesta rodada. Render Free continua sujeito a hibernação e expiração dos questionários após reinício.
