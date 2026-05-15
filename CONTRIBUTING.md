# Guia de Contribuição 🤝

Obrigado por seu interesse em contribuir para o **Gerador de Certificados**! Este documento fornece diretrizes para garantir que o processo de contribuição seja eficiente e agradável para todos.

## Como posso contribuir?

### Reportando Bugs 🐛
Se você encontrar um erro, por favor abra uma **Issue** no GitHub descrevendo:
- O comportamento esperado e o comportamento atual.
- Passos detalhados para reproduzir o problema.
- Informações sobre seu ambiente (Versão do Windows, Python, etc.).
- Logs relevantes (encontrados em `~/.gerador_certificados/app.log`).

### Sugerindo Melhorias ✨
Adoramos novas ideias! Sinta-se à vontade para abrir uma Issue de "Feature Request" com sua sugestão.

### Pull Requests (PRs) 🚀
1. Faça um **Fork** do repositório.
2. Crie uma branch para sua modificação: `git checkout -b feature/minha-melhoria` ou `fix/problema-resolvido`.
3. Siga os padrões de código do projeto (veja abaixo).
4. Certifique-se de que os testes passam: `pytest tests/`.
5. Envie um Pull Request detalhando suas mudanças.

## Padrões de Código

### Estilo Python
- Seguimos as diretrizes da **PEP 8**.
- Utilize `typing` para anotações de tipo sempre que possível.
- Documente novas funções e classes utilizando Docstrings no formato Google/NumPy.

### Convenção de Commits
Seguimos o padrão [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` para novas funcionalidades.
- `fix:` para correções de bugs.
- `docs:` para alterações na documentação.
- `style:` para alterações de formatação de código que não afetam a lógica.
- `refactor:` para refatoração de código.
- `test:` para adição ou correção de testes.

## Processo de Pull Request
1. O PR deve ser aberto contra a branch `main`.
2. Inclua prints ou vídeos se a alteração envolver a Interface Gráfica (UI).
3. Aguarde a revisão de um mantenedor.

Obrigado por ajudar a tornar este projeto melhor!
