# Changelog 📜

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-br/1.0.0/), e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.1.0] - 2026-08-11

### Adicionado
- Novo design system: tipografia Montserrat (com pesos ExtraBold/SemiBold/Medium embutidos como fontes privadas, sem exigir instalação), cantos arredondados e paleta off-white/off-black com subtom marrom no modo escuro.
- Suporte a planilhas `.ods` (OpenDocument), além de `.xlsx`, `.xls` e `.csv`.
- Gestão da tabela de dados: busca em qualquer coluna, ordenação por cabeçalho, ativação/desativação de linhas individuais ou em massa (linhas desativadas não entram na geração).
- Tela cheia dedicada para a tabela de dados, aberta sob demanda — não compete mais por espaço com o formulário de configuração.
- Relatório de erros da geração em CSV, com botão de acesso direto na interface quando um lote termina com falhas.
- Atalhos de teclado: `Ctrl+O` (template), `Ctrl+Shift+O` (planilha), `Enter` (gerar), `Esc` (voltar).
- Validação exibida diretamente nos cards de Template/Planilha (borda vermelha + mensagem), em vez de apenas na barra de status.
- Banner de boas-vindas no primeiro uso, ocultado automaticamente após o primeiro arquivo carregado.
- Tutorial embutido (ícone "?" no cabeçalho): passo a passo do fluxo completo, cada passo com uma reprodução em miniatura do elemento real da interface e texto explicativo.
- Tooltips explicativos ao passar o mouse sobre botões, checkboxes e campos menos óbvios (modos de mapeamento, tags de nome de arquivo, ações em massa da tabela, etc.).
- Suíte de testes de contraste (WCAG AA) cobrindo os pares de cor usados na interface.

### Corrigido
- Botão "Gerar Certificados" com texto ilegível quando desabilitado (contraste insuficiente sobre o fundo laranja).
- `python-docx` ausente de `requirements.txt` apesar de necessário para templates `.docx`.
- Cor de aviso (`AVISO`) idêntica à cor primária no modo claro, perdendo o significado semântico.
- Navegação entre telas (Configurações/Tabela/Ajuda) unificada num só mecanismo — corrige o caso em que fechar Configurações sempre voltava ao formulário principal, mesmo estando na tela da tabela.
- Tooltip em `CTkSegmentedButton` (seletor Planilha/Texto do mapeamento) travava a tela de mapeamento inteira (a biblioteca não suporta `.bind()` nesse widget).

### Alterado
- Layout reestruturado para coluna única, centralizada, com fluxo guiado (arquivos → mapeamento → configurações → gerar).

## [1.0.0] - 2026-05-15

### Adicionado
- Versão inicial do **Gerador de Certificados**.
- Interface gráfica moderna com suporte a temas (Dark/Light).
- Motor de geração de certificados baseado em PowerPoint (`.pptx`).
- Mapeamento inteligente (fuzzy) de variáveis para colunas de planilha.
- Exportação nativa para PDF via Microsoft PowerPoint COM.
- Suporte a Drag & Drop para seleção de arquivos.
- Sistema de logs rotativos e persistência de sessão.
- Documentação completa para publicação open source.

---

[1.1.0]: https://github.com/LoadCG/AutomacaoCertificado/releases/tag/v1.1.0
[1.0.0]: https://github.com/LoadCG/AutomacaoCertificado/releases/tag/v1.0.0
