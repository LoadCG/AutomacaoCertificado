# 🎓 Gerador de Certificados Profissional

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Build](https://img.shields.io/badge/Build-PyInstaller-orange?style=for-the-badge)
![Release](https://img.shields.io/github/v/release/LoadCG/AutomacaoCertificado?style=for-the-badge&color=blue)

O **Gerador de Certificados** é uma solução desktop de alto desempenho projetada para automatizar a criação massiva de certificados personalizados. Desenvolvido com foco em UX/UI moderna e estabilidade técnica, o sistema permite transformar templates do PowerPoint e planilhas de dados em centenas de documentos prontos para entrega em segundos.

> [!IMPORTANT]
> **[⬇️ Baixe a versão mais recente (v1.1.0)](https://github.com/LoadCG/AutomacaoCertificado/releases/latest)** — não precisa instalar Python nem nada além do Windows. Veja também todos os [releases anteriores](https://github.com/LoadCG/AutomacaoCertificado/releases).


---

## 📖 Sumário

- [Visão Geral](#-visão-geral)
- [Funcionalidades Principais](#-funcionalidades-principais)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Requisitos e Compatibilidade](#-requisitos-e-compatibilidade)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Guia de Instalação](#-guia-de-instalação)
- [Como Utilizar](#-como-utilizar)
- [Desenvolvimento e Build](#-desenvolvimento-e-build)
- [Solução de Problemas (Troubleshooting)](#-solução-de-problemas-troubleshooting)
- [Contribuição](#-contribuição)
- [Licença e Créditos](#-licença-e-créditos)
- [Roadmap](#-roadmap)
- [FAQ](#-faq)

---

## 🌟 Visão Geral

Este aplicativo nasceu da necessidade de simplificar o fluxo de trabalho de equipes de treinamento e eventos. Ao contrário de soluções baseadas em "mala direta" tradicionais, o sistema oferece controle total sobre a formatação original do template, exportação nativa para PDF e um sistema inteligente de mapeamento de dados.

### Propósito
Automatizar o preenchimento de variáveis em templates `.pptx` (PowerPoint) ou `.docx` (Word) utilizando dados provenientes de planilhas `.xlsx`, `.ods` ou `.csv`, mantendo a integridade visual e facilitando a gestão de grandes volumes de participantes.

### Principais Funcionalidades
- **Mapeamento Fuzzy Inteligente:** Identifica automaticamente quais colunas da planilha correspondem às variáveis do template (ex: `{{NOME}}` → `Nome do Aluno`).
- **Drag & Drop Nativo:** Arraste templates e planilhas diretamente para a interface.
- **Gestão da Tabela de Dados:** Busque, ordene por coluna e ative/desative linhas individualmente (ou em massa) para excluí-las da geração sem precisar editar a planilha original.
- **Processamento em Segundo Plano:** Geração multithread que não trava a interface do usuário.
- **Relatório de Erros:** Falhas individuais durante o lote geram um CSV detalhado, acessível direto pela interface.
- **Preview em Tempo Real:** Visualize como os nomes dos arquivos serão gerados antes de iniciar o processo.
- **Atalhos de Teclado:** `Ctrl+O`/`Ctrl+Shift+O` para abrir arquivos, `Enter` para gerar, `Esc` para voltar.
- **Suporte a Temas:** Alternância entre Modo Escuro e Modo Claro.
- **Exportação Dupla:** Gere arquivos editáveis (`.pptx`/`.docx`) e versões finais em `.pdf` simultaneamente.
- **Persistência de Sessão:** O aplicativo lembra suas últimas seleções e configurações.

---

## 🛠 Tecnologias Utilizadas

O projeto utiliza o que há de mais moderno no ecossistema Python para aplicações desktop:

- **Linguagem:** [Python 3.11+](https://www.python.org/)
- **Interface Gráfica:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (UI Moderna e Responsiva)
- **Manipulação de PPTX:** [python-pptx](https://python-pptx.readthedocs.io/)
- **Processamento de Dados:** [Pandas](https://pandas.pydata.org/) e [OpenPyXL](https://openpyxl.readthedocs.io/)
- **Interoperabilidade Windows:** [PyWin32](https://github.com/mhammond/pywin32) (para conversão PDF via PowerPoint COM)
- **Distribuição:** [PyInstaller](https://pyinstaller.org/)

---

## 💻 Requisitos e Compatibilidade

### Requisitos Mínimos
- **Sistema Operacional:** Windows 10 ou 11 (recomendado para exportação PDF).
- **Python:** Versão 3.9 ou superior (3.11 recomendada).
- **Software Adicional:** Microsoft PowerPoint **ou** LibreOffice instalado (necessário apenas para a funcionalidade de exportação em PDF — o app tenta PowerPoint primeiro e cai para LibreOffice automaticamente se não encontrá-lo).

### Compatibilidade
| Recurso | Windows | Linux/macOS |
| :--- | :---: | :---: |
| Interface UI | ✅ | ✅ |
| Geração PPTX | ✅ | ✅ |
| Exportação PDF | ✅ | ❌ (Requer Office COM) |
| Drag & Drop | ✅ | ✅ |

---

## 📂 Estrutura do Projeto

```text
AutomacaoCertificado/
├── app/
│   ├── core/           # Motor de geração, loaders e parsers
│   ├── ui/             # Componentes, janelas e estilos CSS-like
│   └── utils/          # Configurações, logs e eventos
├── assets/             # Ícones e recursos visuais
├── docs/               # Documentação técnica e guias de usuário
├── scripts/            # Scripts de automação e build
├── tests/              # Testes automatizados (Pytest)
├── main.py             # Ponto de entrada da aplicação
├── build.spec          # Configuração do PyInstaller
└── requirements.txt    # Dependências de produção
```

---

## 🚀 Guia de Instalação

### Opção A — Só quero usar o app (recomendado para a maioria)

Não é necessário instalar Python, clonar o repositório nem nada técnico:

1. Acesse a página de **[Releases](https://github.com/LoadCG/AutomacaoCertificado/releases/latest)**.
2. Na seção **Assets** do release mais recente, baixe o arquivo `Gerador_Certificados_vX.X.X.exe`.
3. Execute o `.exe` baixado — pronto, o app abre direto (o Windows pode exibir um aviso do SmartScreen por não reconhecer o publicador; clique em "Mais informações" → "Executar assim mesmo").

> [!TIP]
> Todas as versões publicadas — incluindo notas de lançamento e binários de releases anteriores — ficam disponíveis na aba **[Releases](https://github.com/LoadCG/AutomacaoCertificado/releases)** do repositório.

### Opção B — Quero rodar/modificar o código-fonte (desenvolvedores)

#### 1. Clonar o Repositório
```bash
git clone https://github.com/LoadCG/AutomacaoCertificado.git
cd AutomacaoCertificado
```

#### 2. Configuração do Ambiente Virtual (Recomendado)
```bash
python -m venv venv
# No Windows:
.\venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate
```

#### 3. Instalação de Dependências
```bash
pip install -r requirements.txt
# Para desenvolvimento/testes:
pip install -r requirements-dev.txt
```

---

## 📖 Como Utilizar

### Execução em Desenvolvimento
Para iniciar o aplicativo via terminal:
```bash
python main.py
```

### Fluxo Operacional
1. **Selecionar Template:** Arraste (ou clique para procurar) um arquivo `.pptx`/`.docx` que contenha variáveis no formato `{{NOME_DA_VARIAVEL}}`.
2. **Carregar Dados:** Faça o mesmo com a planilha (`.xlsx`, `.xls`, `.ods` ou `.csv`) dos participantes.
3. **Mapear Variáveis:** O app associa as colunas automaticamente por similaridade de nome. Ajuste manualmente onde necessário, ou use o modo "Texto" para um valor fixo (igual em todos os certificados).
4. **Revisar os Dados (opcional):** Clique em **"Ver Tabela Completa"** para buscar, ordenar e desativar participantes específicos que não devem receber certificado — sem editar a planilha original.
5. **Configurar Saída:** Escolha a pasta de destino e o padrão de nomenclatura dos arquivos (ex: `Certificado - {{NOME}}`).
6. **Gerar:** Clique no botão de destaque e acompanhe o progresso pela barra e pelo log. Se algum participante falhar, os demais continuam normalmente e um relatório de erros em CSV fica disponível ao final.

> [!TIP]
> O app tem um tutorial embutido — clique no ícone **"?"** no canto superior direito a qualquer momento para rever o passo a passo com exemplos visuais de cada etapa. Também há tooltips explicativos ao passar o mouse sobre a maioria dos botões e campos.
>
> Para criar modelos `.pptx`/`.docx` corretamente, consulte o **[Guia de Templates](docs/GUIA_TEMPLATE.md)**.

---

## 📦 Desenvolvimento e Build

### Gerando o Executável (.exe)
O projeto conta com um script automatizado para gerar a versão de produção:

```bash
# Via script batch (Windows)
.\scripts\build.bat
```

Ou manualmente via PyInstaller:
```bash
pyinstaller build.spec --clean
```
O executável final será gerado na pasta `dist/`.

### Executando Testes
Garantimos a estabilidade através de testes automatizados:
```bash
pytest tests/
```

---

## 🛠 Solução de Problemas (Troubleshooting)

### Logs e Depuração
Os logs da aplicação são salvos automaticamente no diretório do usuário:
- **Caminho:** `C:\Users\<SeuUsuario>\.gerador_certificados\app.log`
- Você pode visualizar eventos detalhados clicando no botão **CONSOLE** na barra de status inferior do app.

### Problemas Comuns
- **Windows SmartScreen bloqueou o `.exe`:** É esperado para apps sem certificado de assinatura de código. Clique em "Mais informações" → "Executar assim mesmo". O executável é gerado publicamente a partir deste repositório (veja `build.spec`) — não há nada oculto.
- **Erro na Exportação PDF:** Certifique-se de que o Microsoft PowerPoint ou o LibreOffice está instalado e não há diálogos de erro abertos no Office.
- **Variável não detectada:** Verifique se a variável no PowerPoint/Word está escrita exatamente como `{{VARIAVEL}}`, sem espaços internos ou quebras de linha manuais.
- **Planilha não carrega:** Certifique-se de que a planilha não está aberta em outro programa (como Excel) durante a importação.

---

## 🤝 Contribuição

Contribuições são o que fazem a comunidade open source um lugar incrível para aprender e criar!

1. **Abra uma Issue:** Para bugs ou sugestões de melhorias.
2. **Fork o projeto.**
3. **Crie uma Feature Branch:** `git checkout -b feature/NovaFuncionalidade`.
4. **Commit suas mudanças:** `git commit -m 'feat: Adiciona nova funcionalidade'`.
   - *Nota: Seguimos o padrão [Conventional Commits](https://www.conventionalcommits.org/).*
5. **Push para a Branch:** `git push origin feature/NovaFuncionalidade`.
6. **Abra um Pull Request.**

---

## ⚖️ Licença e Créditos

Este projeto está licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

**Desenvolvido por:** [Cauan Gabriel](https://github.com/LoadCG)
**Ícones e Design:** Equipe de Treinamentos / Antigravity Design System.
**Tipografia:** [Montserrat](https://github.com/JulietaUla/Montserrat), licenciada sob a [SIL Open Font License 1.1](assets/fonts/OFL.txt).

---

## 🗺 Roadmap

- [ ] Suporte a envio automático por E-mail.
- [ ] Editor de template simplificado dentro do app.
- [ ] Suporte a assinaturas digitais.
- [ ] Versão nativa para macOS (sem dependência de COM).

---

## ❓ FAQ

**O aplicativo funciona sem internet?**
Sim, 100% offline. Nenhum dado é enviado para servidores externos.

**Posso usar templates com muitas imagens?**
Com certeza. O motor preserva todos os elementos visuais do seu PowerPoint.

**Existe limite de certificados por lote?**
Tecnicamente não, mas lotes acima de 1.000 unidades podem levar alguns minutos dependendo do seu hardware.

---
<p align="center">Feito com ❤️ pela equipe de automação.</p>
