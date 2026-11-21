# Implementação de login, histórico e perfil

O questionário é público. A primeira etapa de autenticação aparece após a última resposta ou ao selecionar voluntariamente Minhas avaliações. Usar uma conta gratuita com código por e-mail e Google, garantindo retorno à avaliação.

- [x] Implementar sessão de conta no FastAPI, verificação do Google e códigos de uso único. Cobrir criação, vínculo, validade e saída com testes sem rede.
- [x] Proteger a geração do diagnóstico. Salvar registros privados no SQLite antes de exibir, reaproveitar submissões repetidas e verificar retomada, isolamento e exclusão.
- [x] Integrar tela de entrada e rascunho no React. Adicionar histórico, edição de perfil e foto opcional. Testar o fluxo de visitante e as falhas recuperáveis.
- [x] Documentar configuração e limitações de hospedagem. Executar as suítes, lint e build da branch.
