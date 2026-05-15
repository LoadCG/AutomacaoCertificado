"""
Janela principal do Gerador de Certificados.

Layout em 3 painéis:
- Esquerdo: Configuração (etapas 1/2/3 + checkbox PDF + botão Gerar)
- Central: Mapeamento de variáveis + preview da planilha
- Inferior: Progresso, contador e log
"""

from app.ui import styles
from app.ui.styles import fontes
import threading
import unicodedata
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

import customtkinter as ctk
import pandas as pd

from app.core import certificate_engine, data_loader, template_parser
from app.ui.components import (
    FilePickerRow,
    FolderPickerRow,
    LogArea,
    PreviewPlanilha,
    SectionHeader,
    StatusBar,
    VariavelMapRow,
)
from tkinterdnd2.TkinterDnD import DnDWrapper, _require
from app.ui.styles import cores, esp, fonte_ctk
from app.utils.config import Config
from app.utils.events import EventoGerador
from app.utils.logger import obter_logger

log = obter_logger(__name__)


# ---------------------------------------------------------------------------
# Funções de auto-mapeamento fuzzy
# ---------------------------------------------------------------------------


def _normalizar_str(s: str) -> str:
    """
    Normaliza string para comparação fuzzy: minúsculo, sem acentos, sem espaços/underlines.

    Ex: 'Nome Completo' → 'nomecompleto', 'FUNÇÃO' → 'funcao'
    """
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace(" ", "").replace("_", "").replace("-", "")


def _auto_mapear(variavel: str, colunas: list[str]) -> Optional[str]:
    """
    Tenta mapear automaticamente uma variável de template para a coluna mais similar.

    Estratégia em ordem de prioridade:
    1. Match exato normalizado ({{NOME}} = "Nome" = "nome" = "NOME")
    2. Coluna começa com o nome da variável ({{NOME}} → "Nome Completo")
    3. Nome da variável está contido na coluna ({{RG}} → "Número RG")
    4. Coluna está contida no nome da variável ({{NOME_COMPLETO}} → "Nome")

    Args:
        variavel: Variável do template, ex: '{{NOME_COMPLETO}}'.
        colunas: Lista de colunas disponíveis na planilha.

    Returns:
        Nome da coluna que melhor corresponde, ou None se não encontrar.
    """
    if not colunas:
        return None

    # Extrai o nome sem chaves e normaliza
    nome_var = _normalizar_str(variavel.strip("{}"))

    # 1. Match exato normalizado
    for col in colunas:
        if _normalizar_str(col) == nome_var:
            return col

    # 2. Coluna começa com o nome da variável
    for col in colunas:
        if _normalizar_str(col).startswith(nome_var):
            return col

    # 3. Nome da variável está contido na coluna normalizada
    for col in colunas:
        if nome_var in _normalizar_str(col):
            return col

    # 4. Coluna normalizada está contida no nome da variável (ex: {{NOME_COMPLETO}} → "Nome")
    for col in colunas:
        col_norm = _normalizar_str(col)
        if col_norm and col_norm in nome_var and len(col_norm) >= 3:
            return col

    return None


class MainWindow(ctk.CTk, DnDWrapper):
    """
    Janela principal da aplicação Gerador de Certificados.

    Gerencia o fluxo completo: seleção de arquivos → mapeamento de
    variáveis → geração em thread separada → atualização da UI via polling.
    """

    TITULO_APP = "Gerador de Certificados"

    def __init__(self) -> None:
        super().__init__()

        # Inicializa suporte a Drag & Drop
        self.TkdndVersion = _require(self)

        # Estado interno
        self._config = Config.carregar().validar_caminhos()
        self._df: Optional[pd.DataFrame] = None
        self._variaveis: list[str] = []
        self._mapeamento: dict[str, str] = {}
        self._map_rows: list[VariavelMapRow] = []
        self._fila: Queue[EventoGerador] = Queue()
        self._thread: Optional[threading.Thread] = None
        self._gerando = False
        self._padrao_nome: str = (
            self._config.padrao_nome or certificate_engine.PADRAO_NOME_PADRAO
        )

        self._configurar_janela()
        self._construir_layout()
        self._restaurar_sessao()

    # ------------------------------------------------------------------
    # Configuração da janela
    # ------------------------------------------------------------------

    def _configurar_janela(self) -> None:
        """Configura título, tamanho mínimo, ícone e grid principal adaptativo."""
        self.title(self.TITULO_APP)
        self.minsize(esp.LARGURA_MINIMA_JANELA, esp.ALTURA_MINIMA_JANELA)
        # Tamanho inicial otimizado para laptops e monitores menores
        self.geometry("1100x720")
        
        # Aplica o tema salvo antes de mostrar a janela
        styles.aplicar_tema(self._config.tema_aparencia)
        self.configure(fg_color=cores.FUNDO_PRINCIPAL)

        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Configuração de expansão: Área central e Logs podem crescer
        self.grid_columnconfigure(0, weight=0)  # Sidebar largura fixa
        self.grid_columnconfigure(1, weight=1)  # Central elástica
        self.grid_rowconfigure(0, weight=0)     # Header fixo
        self.grid_rowconfigure(1, weight=1)     # Conteúdo central elástico
        self.grid_rowconfigure(2, weight=0)     # Área de logs (expandível se aberta, mas peso 0 mantém proporção)
        self.grid_rowconfigure(3, weight=0)     # StatusBar fixa

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    # ------------------------------------------------------------------
    # Construção do layout
    # ------------------------------------------------------------------

    def _construir_layout(self) -> None:
        """Constrói todos os painéis da janela."""
        self._construir_header()
        self._construir_painel_esquerdo()
        self._construir_painel_central()
        self._construir_painel_inferior()
        
        # O terminal inicia escondido (não chamamos .grid() no painel_inferior por padrão)
        self._terminal_visivel = False

        self._status_bar = StatusBar(self, ao_clicar_console=self._alternar_terminal)
        self._status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

    def _construir_header(self) -> None:
        """Cabeçalho superior com design compacto e minimalista."""
        header = ctk.CTkFrame(
            self, fg_color=cores.FUNDO_PRINCIPAL, height=64, corner_radius=0
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.pack_propagate(False)

        # Título principal
        ctk.CTkLabel(
            header,
            text=self.TITULO_APP.upper(),
            font=fonte_ctk(fontes.TAMANHO_NORMAL, "bold"),
            text_color=cores.TEXTO_PRINCIPAL,
        ).pack(side="left", padx=esp.PADDING_GRANDE)

        # Indicador de versão sutil
        # Botão de Configurações (Ícone sutil)
        self._btn_config = ctk.CTkButton(
            header,
            text="⚙️",
            width=32,
            height=32,
            font=fonte_ctk(16),
            fg_color="transparent",
            text_color=cores.TEXTO_SECUNDARIO,
            hover_color=cores.FUNDO_PAINEL,
            command=self._alternar_visualizacao,
        )
        self._btn_config.pack(side="right", padx=esp.PADDING_GRANDE)

        # Divisor sutil
        ctk.CTkFrame(header, fg_color=cores.DIVISOR, height=2).pack(
            fill="x", side="bottom"
        )

    def _construir_painel_esquerdo(self) -> None:
        """Painel lateral de configuração com fluxo guiado."""
        self._painel_esquerdo = ctk.CTkScrollableFrame(
            self,
            width=esp.LARGURA_PAINEL_ESQUERDO,
            fg_color=cores.FUNDO_PAINEL,
            scrollbar_button_color=cores.PRIMARIA,
            corner_radius=0,
        )
        self._painel_esquerdo.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Adiciona um padding interno manual
        content = ctk.CTkFrame(self._painel_esquerdo, fg_color="transparent")
        content.pack(
            fill="both", expand=True, padx=esp.PADDING_MEDIO, pady=esp.PADDING_MEDIO
        )

        SectionHeader(content, "Arquivos de Origem", "📂").pack(fill="x", pady=(0, 20))

        # Etapa 1 — Template
        self._picker_template = FilePickerRow(
            content,
            rotulo="1. Template de Certificado (.pptx)",
            tipos_arquivo=[("Apresentação PowerPoint", "*.pptx")],
            callback_selecao=self._ao_selecionar_template,
            valor_inicial=self._config.ultimo_template,
        )
        self._picker_template.pack(fill="x", pady=(0, 24))

        # Etapa 2 — Planilha
        self._picker_planilha = FilePickerRow(
            content,
            rotulo="2. Dados dos Participantes (.xlsx, .csv)",
            tipos_arquivo=[
                ("Planilhas", "*.xlsx *.xls *.csv"),
                ("Excel", "*.xlsx *.xls"),
                ("CSV", "*.csv"),
            ],
            callback_selecao=self._ao_selecionar_planilha,
            valor_inicial=self._config.ultima_planilha,
        )
        self._picker_planilha.pack(fill="x", pady=(0, 24))

        # Etapa 3 — Pasta de saída
        self._picker_saida = FolderPickerRow(
            content,
            rotulo="3. Destino dos Arquivos",
            callback_selecao=self._ao_selecionar_pasta_saida,
            valor_inicial=self._config.ultima_pasta_saida,
        )
        self._picker_saida.pack(fill="x", pady=(0, 32))

        SectionHeader(content, "Ações e Exportação", "🚀").pack(fill="x", pady=(0, 20))

        # Etapa 4: Padrão do nome do arquivo
        lbl_padrao = ctk.CTkLabel(
            content,
            text="4. NOME DOS ARQUIVOS",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
        )
        lbl_padrao.pack(fill="x", pady=(0, 4))

        frame_padrao = ctk.CTkFrame(
            content,
            fg_color=cores.FUNDO_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
        )
        frame_padrao.pack(fill="x", pady=(0, 6))

        self._entry_padrao = ctk.CTkEntry(
            frame_padrao,
            placeholder_text="Ex: Certificado - {{NOME}}",
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            fg_color="transparent",
            border_width=0,
            text_color=cores.TEXTO_PRINCIPAL,
            height=36,
        )
        self._entry_padrao.insert(0, self._padrao_nome)
        self._entry_padrao.pack(fill="x", padx=12, pady=2)
        
        # Bind para preview em tempo real
        self._entry_padrao.bind("<KeyRelease>", lambda e: self._atualizar_preview_nome())
        self._entry_padrao.bind("<FocusOut>", self._ao_mudar_padrao_nome)

        # Container de Ajuda e Preview
        self._frame_ajuda_nome = ctk.CTkFrame(content, fg_color="transparent")
        self._frame_ajuda_nome.pack(fill="x", pady=(0, 20))

        self._lbl_preview_nome = ctk.CTkLabel(
            self._frame_ajuda_nome,
            text="PREVIEW: ...",
            font=fonte_ctk(10, "bold"),
            text_color=cores.PRIMARIA,
            anchor="w",
            wraplength=300,
            justify="left"
        )
        self._lbl_preview_nome.pack(fill="x", pady=(4, 8))

        self._lbl_dica_vars = ctk.CTkLabel(
            self._frame_ajuda_nome,
            text="Variáveis disponíveis: (carregue um template)",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_DESABILITADO,
            anchor="w",
            wraplength=300,
            justify="left"
        )
        self._lbl_dica_vars.pack(fill="x")

        # Opções Adicionais
        self._var_pdf = ctk.BooleanVar(value=self._config.exportar_pdf)
        self._chk_pdf = ctk.CTkCheckBox(
            content,
            text="Gerar exportação em PDF",
            variable=self._var_pdf,
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            command=self._ao_mudar_pdf,
            fg_color=cores.PRIMARIA,
            hover_color=cores.PRIMARIA_HOVER,
            border_color=cores.BORDA_SUTIL,
            corner_radius=6,
        )
        self._chk_pdf.pack(fill="x", pady=(0, 40))

        # Botão Gerar — Destaque máximo (Apple Style)
        self._btn_gerar = ctk.CTkButton(
            content,
            text="GERAR CERTIFICADOS",
            height=54,
            font=fonte_ctk(fontes.TAMANHO_SUBTITULO, "bold"),
            fg_color=cores.PRIMARIA,
            hover_color=cores.PRIMARIA_HOVER,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=12,
            command=self._iniciar_geracao,
            state="disabled",
        )
        self._btn_gerar.pack(fill="x", pady=(0, 12))

        self._lbl_validacao = ctk.CTkLabel(
            content,
            text="Preencha os campos para iniciar",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO),
            text_color=cores.AVISO,
            anchor="center",
        )
        self._lbl_validacao.pack(fill="x")

        if not certificate_engine.com_disponivel():
            self._chk_pdf.configure(state="disabled", text="PDF (Requer MS PowerPoint)")

    def _construir_painel_central(self) -> None:
        """Painel principal para mapeamento e visualização de dados."""
        self._painel_central = ctk.CTkFrame(self, fg_color="transparent")
        self._painel_central.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=esp.PADDING_GRANDE,
            pady=esp.PADDING_GRANDE,
        )
        self._painel_central.grid_columnconfigure(0, weight=1)
        self._painel_central.grid_rowconfigure(1, weight=1)
        self._painel_central.grid_rowconfigure(3, weight=2)

        # Mapeamento de Variáveis
        SectionHeader(
            self._painel_central, 
            "Vínculo de Variáveis", 
            "🔗", 
            acao_callback=self._atualizar_mapeamento,
            acao_icone="🔄",
            tooltip="Tenta vincular automaticamente variáveis a colunas similares da planilha"
        ).grid(row=0, column=0, sticky="ew")

        self._frame_vars_container = ctk.CTkScrollableFrame(
            self._painel_central,
            fg_color="transparent",
            height=280,
            scrollbar_button_color=cores.PRIMARIA,
        )
        self._frame_vars_container.grid(row=1, column=0, sticky="nsew", pady=(0, 24))

        self._frame_vars = ctk.CTkFrame(
            self._frame_vars_container, fg_color="transparent"
        )
        self._frame_vars.pack(fill="both", expand=True)

        self._lbl_sem_vars = ctk.CTkLabel(
            self._frame_vars,
            text="Aguardando importação de template .pptx...",
            font=fonte_ctk(fontes.TAMANHO_NORMAL, "italic"),
            text_color=cores.TEXTO_DESABILITADO,
        )
        self._lbl_sem_vars.pack(pady=40)

        # Preview da Planilha
        SectionHeader(self._painel_central, "Visualização dos Dados", "📊").grid(
            row=2, column=0, sticky="ew"
        )

        self._preview = PreviewPlanilha(self._painel_central)
        self._preview.grid(row=3, column=0, sticky="nsew")

    def _construir_painel_inferior(self) -> None:
        """Área de progresso e log com visual de terminal integrado."""
        self._painel_inferior = ctk.CTkFrame(self, fg_color=cores.FUNDO_PAINEL, corner_radius=0)
        # Removida a chamada automática de .grid() aqui para iniciar escondido
        self._painel_inferior.grid_columnconfigure(0, weight=1)

        # Container interno com padding
        content = ctk.CTkFrame(self._painel_inferior, fg_color="transparent")
        content.pack(fill="x", padx=esp.PADDING_GRANDE, pady=esp.PADDING_MEDIO)

        # Cabeçalho do log + Botão Limpar
        header_prog = ctk.CTkFrame(content, fg_color="transparent")
        header_prog.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header_prog,
            text="PROGRESSO DA OPERAÇÃO",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            text_color=cores.TEXTO_SECUNDARIO,
        ).pack(side="left")

        self._lbl_contador = ctk.CTkLabel(
            header_prog,
            text="0 / 0",
            font=fonte_ctk(fontes.TAMANHO_NORMAL, "bold"),
            text_color=cores.PRIMARIA,
        )
        self._lbl_contador.pack(side="right")

        # Barra de progresso moderna
        self._barra_prog = ctk.CTkProgressBar(
            content,
            height=10,
            fg_color=cores.FUNDO_INPUT,
            progress_color=cores.PRIMARIA,
            corner_radius=5,
        )
        self._barra_prog.set(0)
        self._barra_prog.pack(fill="x", pady=(0, 20))

        # Terminal de Log
        terminal_header = ctk.CTkFrame(content, fg_color="transparent")
        terminal_header.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            terminal_header,
            text="TERMINAL DE EVENTOS",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            text_color=cores.TEXTO_SECUNDARIO,
        ).pack(side="left")

        ctk.CTkButton(
            terminal_header,
            text="LIMPAR",
            width=60,
            height=20,
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            fg_color="transparent",
            text_color=cores.TEXTO_DESABILITADO,
            hover_color=cores.FUNDO_CARD,
            command=lambda: self._log.limpar(),
        ).pack(side="right")

        self._log = LogArea(content, height=140)
        self._log.pack(fill="x")

    def _construir_painel_configuracoes(self) -> None:
        """Constrói a tela de configurações e preferências."""
        self._painel_config = ctk.CTkFrame(self, fg_color="transparent")
        # Inicialmente não exibido
        
        content = ctk.CTkFrame(self._painel_config, fg_color=cores.FUNDO_PAINEL, corner_radius=12)
        content.pack(expand=True, padx=100, pady=50)
        
        SectionHeader(content, "Preferências do Aplicativo", "⚙️").pack(fill="x", padx=40, pady=(40, 20))
        
        # Opção de Tema
        frame_tema = ctk.CTkFrame(content, fg_color="transparent")
        frame_tema.pack(fill="x", padx=40, pady=20)
        
        ctk.CTkLabel(
            frame_tema, 
            text="TEMA DA INTERFACE", 
            font=fonte_ctk(fontes.TAMANHO_NORMAL, "bold"),
            text_color=cores.TEXTO_PRINCIPAL
        ).pack(side="left")
        
        self._switch_tema = ctk.CTkSwitch(
            frame_tema,
            text="Modo Escuro",
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            progress_color=cores.PRIMARIA,
            command=self._ao_alternar_tema
        )
        # Sincroniza estado do switch com a config
        if self._config.tema_aparencia == "dark":
            self._switch_tema.select()
        else:
            self._switch_tema.deselect()
            
        self._switch_tema.pack(side="right")
        
        ctk.CTkLabel(
            content,
            text="As alterações de tema são aplicadas instantaneamente.",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO
        ).pack(pady=(0, 40))

    def _alternar_visualizacao(self) -> None:
        """Alterna entre a tela de geração e a tela de configurações."""
        # Se o painel de config ainda não existe, cria (lazy loading visual)
        if not hasattr(self, "_painel_config"):
            self._construir_painel_configuracoes()
            
        if self._btn_config.cget("text") == "⚙️":
            # Muda para modo Config
            self._btn_config.configure(text="🏠", text_color=cores.PRIMARIA)
            # Esconde painéis de geração
            self._painel_esquerdo.grid_forget() if hasattr(self, "_painel_esquerdo") else None
            self._painel_central.grid_forget() if hasattr(self, "_painel_central") else None
            self._painel_inferior.grid_forget() if hasattr(self, "_painel_inferior") else None
            # Mostra painel de config
            self._painel_config.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)
            self._status_bar.definir("CONFIGURAÇÕES DO SISTEMA", cores.INFO)
        else:
            # Volta para modo Geração
            self._btn_config.configure(text="⚙️", text_color=cores.TEXTO_SECUNDARIO)
            self._painel_config.grid_forget()
            # Reaplica grid original
            self._painel_esquerdo.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
            self._painel_central.grid(row=1, column=1, sticky="nsew", padx=esp.PADDING_GRANDE, pady=esp.PADDING_GRANDE)
            self._painel_inferior.grid(row=2, column=0, columnspan=2, sticky="ew")
            self._status_bar.definir("SISTEMA PRONTO", cores.SUCESSO)

    def _ao_alternar_tema(self) -> None:
        """Callback do switch de tema."""
        novo_tema = "dark" if self._switch_tema.get() else "light"
        self._config.tema_aparencia = novo_tema
        self._config.salvar()
        styles.aplicar_tema(novo_tema)
        # Atualiza cor de fundo da janela principal
        self.configure(fg_color=cores.FUNDO_PRINCIPAL)

    def _alternar_terminal(self) -> None:
        """Mostra ou esconde o terminal de logs inferior."""
        if self._terminal_visivel:
            self._painel_inferior.grid_forget()
            self._terminal_visivel = False
            self._status_bar._btn_terminal.configure(fg_color=cores.FUNDO_PAINEL)
        else:
            self._painel_inferior.grid(row=2, column=0, columnspan=2, sticky="ew")
            self._terminal_visivel = True
            self._status_bar._btn_terminal.configure(fg_color=cores.PRIMARIA)

    # ------------------------------------------------------------------
    # Callbacks de seleção de arquivo
    # ------------------------------------------------------------------

    def _ao_selecionar_template(self, caminho: Path) -> None:
        """Detecta variáveis do template e atualiza o painel central."""
        self._status_bar.definir("⏳ Analisando template...", cores.INFO)
        try:
            self._variaveis = template_parser.extrair_variaveis(caminho)
            self._config.ultimo_template = str(caminho)
            self._config.salvar()
            self._atualizar_mapeamento()
            self._status_bar.definir("")
        except Exception as e:
            self._status_bar.definir(f"✗ Erro ao analisar template: {e}", cores.ERRO)
            log.error("Erro ao analisar template '%s': %s", caminho, e)
            if not self._terminal_visivel:
                self._alternar_terminal()
        finally:
            self._validar_e_atualizar_botao()

    def _ao_selecionar_planilha(self, caminho: Path) -> None:
        """Carrega a planilha e atualiza preview e dropdowns."""
        self._status_bar.definir("⏳ Carregando planilha...", cores.INFO)
        try:
            self._df = data_loader.carregar_planilha(caminho)
            self._config.ultima_planilha = str(caminho)
            self._config.salvar()
            self._preview.renderizar(self._df)
            self._atualizar_colunas_nos_dropdowns()
            self._status_bar.definir("")
        except Exception as e:
            self._status_bar.definir(f"✗ Erro ao carregar planilha: {e}", cores.ERRO)
            log.error("Erro ao carregar planilha '%s': %s", caminho, e)
        finally:
            self._atualizar_preview_nome()
            self._validar_e_atualizar_botao()

    def _ao_selecionar_pasta_saida(self, caminho: Path) -> None:
        """Persiste a pasta de saída selecionada."""
        self._config.ultima_pasta_saida = str(caminho)
        self._config.salvar()
        self._validar_e_atualizar_botao()

    def _ao_mudar_pdf(self) -> None:
        """Persiste a preferência de exportação PDF."""
        self._config.exportar_pdf = self._var_pdf.get()
        self._config.salvar()

    def _atualizar_preview_nome(self) -> None:
        """Atualiza o label de preview do nome do arquivo com tolerância a erros de digitação."""
        if not hasattr(self, "_lbl_preview_nome"):
            return

        padrao = self._entry_padrao.get().strip()
        if not padrao:
            padrao = certificate_engine.PADRAO_NOME_PADRAO

        # Prepara dados de exemplo (reais da planilha ou genéricos)
        exemplo_dados = {
            "{{NOME}}": "João Silva",
            "{{RG}}": "00.000.000-0",
            "{{CPF}}": "000.000.000-00",
            "{{CARGO}}": "Participante",
            "{{CURSO}}": "Treinamento",
            "{{HORAS}}": "40"
        }
        
        # Se houver planilha carregada, usa os dados REAIS da primeira linha
        if self._df is not None and not self._df.empty:
            primeira_linha = self._df.iloc[0]
            for row in self._map_rows:
                val = row.valor_mapeado
                if val:
                    if val.startswith("FIXED:"):
                        exemplo_dados[row._variavel] = val.replace("FIXED:", "")
                    elif val in self._df.columns:
                        exemplo_dados[row._variavel] = str(primeira_linha[val])

        try:
            # Tenta formatar, mas se falhar por sintaxe incompleta (ex: '{{'), 
            # apenas mostra o texto original sem tratar como erro crítico
            nome_final = certificate_engine.formatar_nome_arquivo(
                padrao, exemplo_dados, indice=1
            )
            self._lbl_preview_nome.configure(
                text=f"SAÍDA: {nome_final}.pptx",
                text_color=cores.SUCESSO
            )
        except Exception:
            # Durante a digitação (ex: user escreveu '{{'), não mostramos erro em vermelho
            # Mostramos o texto atual como preview 'cru'
            self._lbl_preview_nome.configure(
                text=f"SAÍDA: {padrao}.pptx",
                text_color=cores.TEXTO_SECUNDARIO
            )

    def _ao_mudar_padrao_nome(self, _event=None) -> None:
        """Persiste e valida o padrão de nome de arquivo ao perder o foco."""
        valor = self._entry_padrao.get().strip()
        if not valor:
            valor = certificate_engine.PADRAO_NOME_PADRAO
            self._entry_padrao.delete(0, "end")
            self._entry_padrao.insert(0, valor)
        self._padrao_nome = valor
        self._config.padrao_nome = valor
        self._config.salvar()
        self._atualizar_preview_nome()

    # ------------------------------------------------------------------
    # Atualização do painel de mapeamento
    # ------------------------------------------------------------------

    def _atualizar_mapeamento(self) -> None:
        """Reconstrói as linhas de mapeamento variável ↔ coluna."""
        # Remove rows anteriores
        for row in self._map_rows:
            row.destroy()
        self._map_rows.clear()
        self._mapeamento.clear()

        if not self._variaveis:
            self._lbl_sem_vars.pack(pady=24)
            if hasattr(self, "_lbl_dica_vars"):
                self._lbl_dica_vars.configure(text="Disponíveis: (carregue um template)")
            return

        self._lbl_sem_vars.pack_forget()
        
        # Atualiza dica visual na Etapa 4
        if hasattr(self, "_lbl_dica_vars"):
            vars_str = ", ".join(self._variaveis)
            self._lbl_dica_vars.configure(
                text=f"Disponíveis: {vars_str}\nTags: {{DATA}}, {{HORA}}, {{INDICE}}",
                text_color=cores.TEXTO_SECUNDARIO
            )

        colunas = data_loader.obter_colunas(self._df) if self._df is not None else []

        for variavel in self._variaveis:
            row = VariavelMapRow(
                self._frame_vars,
                variavel=variavel,
                colunas=colunas,
                callback_mudanca=self._ao_mudar_mapeamento,
            )
            row.pack(fill="x", padx=6, pady=3)
            self._map_rows.append(row)

            # Auto-mapeamento fuzzy
            col_match = _auto_mapear(variavel, colunas)
            if col_match:
                row._var_coluna.set(col_match)
                row._ao_mudar_dropdown(col_match)
                self._mapeamento[variavel] = col_match
        
        self._atualizar_preview_nome()

    def _atualizar_colunas_nos_dropdowns(self) -> None:
        """Atualiza a lista de colunas nos dropdowns e tenta preservar mapeamentos."""
        if self._df is None:
            return
        colunas = data_loader.obter_colunas(self._df)

        for row in self._map_rows:
            # Pega o mapeamento atual antes de atualizar a lista
            mapeado_antes = self._mapeamento.get(row._variavel)

            row.atualizar_colunas(colunas)

            # Se for texto fixo, mantemos o valor
            if mapeado_antes and mapeado_antes.startswith("FIXED:"):
                # row.atualizar_colunas já detecta se é modo fixo e não reseta
                continue

            # Se for coluna, verificamos se a coluna ainda existe
            if mapeado_antes and mapeado_antes in colunas:
                row._dropdown.set(mapeado_antes)
                row._indicador.configure(text_color=VariavelMapRow._COR_OK)
            else:
                # Se não existe mais ou não estava mapeado, tenta auto-mapear
                col_match = _auto_mapear(row._variavel, colunas)
                if col_match:
                    row._dropdown.set(col_match)
                    row.configure(border_color=cores.BORDA_DESTAQUE)
                    row._indicador.configure(text_color=cores.SUCESSO)
                    self._mapeamento[row._variavel] = col_match
                else:
                    self._mapeamento.pop(row._variavel, None)

        self._validar_e_atualizar_botao()

    def _ao_mudar_mapeamento(self, variavel: str, coluna: str) -> None:
        """Atualiza o dicionário de mapeamento e valida o botão Gerar."""
        if coluna == "(selecione uma coluna)":
            self._mapeamento.pop(variavel, None)
        else:
            self._mapeamento[variavel] = coluna
        self._atualizar_preview_nome()
        self._validar_e_atualizar_botao()

    # ------------------------------------------------------------------
    # Validação e controle do botão Gerar
    # ------------------------------------------------------------------

    def _validar_e_atualizar_botao(self) -> None:
        """
        Habilita o botão Gerar somente quando todos os campos estão prontos.

        Condições: template selecionado, planilha carregada,
        pasta de saída definida e pelo menos uma variável mapeada.
        """
        template_ok = self._picker_template.caminho is not None
        planilha_ok = self._df is not None
        saida_ok = self._picker_saida.caminho is not None
        
        # O mapeamento só está OK se TODAS as variáveis encontradas no template 
        # tiverem um valor definido (coluna selecionada ou texto fixo não vazio)
        mapeamento_ok = True
        if self._variaveis:
            for var in self._variaveis:
                val = self._mapeamento.get(var)
                if not val or val == "(selecione uma coluna)" or val == "FIXED:":
                    mapeamento_ok = False
                    break
        else:
            # Se não há variáveis, o mapeamento é nulo por definição
            mapeamento_ok = False

        tudo_ok = template_ok and planilha_ok and saida_ok and mapeamento_ok

        if tudo_ok and not self._gerando:
            self._btn_gerar.configure(state="normal")
            self._lbl_validacao.configure(
                text="✓ Pronto para gerar", text_color=cores.SUCESSO
            )
        elif self._gerando:
            self._btn_gerar.configure(state="disabled")
            self._lbl_validacao.configure(
                text="⏳ Gerando certificados...", text_color=cores.INFO
            )
        else:
            self._btn_gerar.configure(state="disabled")
            pendentes = []
            if not template_ok:
                pendentes.append("template")
            if not planilha_ok:
                pendentes.append("planilha")
            if not saida_ok:
                pendentes.append("pasta de saída")
            if not mapeamento_ok:
                pendentes.append("mapeamento")
            self._lbl_validacao.configure(
                text=f"Aguardando: {', '.join(pendentes)}",
                text_color=cores.AVISO,
            )

    # ------------------------------------------------------------------
    # Geração em thread separada
    # ------------------------------------------------------------------

    def _iniciar_geracao(self) -> None:
        """Valida e inicia a geração de certificados em thread separada."""
        template = self._picker_template.caminho
        pasta_saida = self._picker_saida.caminho

        if template is None or self._df is None or pasta_saida is None:
            return

        self._gerando = True
        self._validar_e_atualizar_botao()
        self._log.limpar()
        self._barra_prog.set(0)
        self._lbl_contador.configure(text=f"0 / {len(self._df)}")
        self._status_bar.definir("⏳ Gerando certificados...", cores.INFO)
        self._log.append(
            f"Iniciando geração de {len(self._df)} certificado(s)...", "info"
        )

        # Limpa fila de eventos residuais
        while not self._fila.empty():
            try:
                self._fila.get_nowait()
            except Empty:
                break

        self._thread = threading.Thread(
            target=certificate_engine.gerar_lote,
            args=(
                template,
                self._df,
                self._mapeamento,
                pasta_saida,
                self._fila,
                self._var_pdf.get(),
                self._padrao_nome,
            ),
            daemon=True,
        )
        self._thread.start()
        self.after(100, self._verificar_fila)

    def _verificar_fila(self) -> None:
        """
        Polling não-bloqueante da fila de eventos da thread de geração.

        Chamada a cada 100ms via `after()`. Atualiza barra de progresso,
        contador e log conforme eventos chegam da thread.
        """
        try:
            while True:
                evento = self._fila.get_nowait()
                self._processar_evento(evento)
        except Empty:
            pass

        # Continua polling enquanto a thread estiver rodando
        if self._thread is not None and self._thread.is_alive():
            self.after(100, self._verificar_fila)

    def _processar_evento(self, evento: EventoGerador) -> None:
        """Atualiza a UI com base no tipo de evento recebido da thread."""
        tipo = evento["tipo"]

        if tipo == "progresso":
            atual = evento["atual"]  # type: ignore
            total = evento["total"]  # type: ignore
            pct = atual / total if total > 0 else 0
            self._barra_prog.set(pct)
            self._lbl_contador.configure(text=f"{atual} / {total}")

        elif tipo == "sucesso":
            arquivo = evento["arquivo"]  # type: ignore
            self._log.append(arquivo, "sucesso")

        elif tipo == "erro":
            arquivo = evento["arquivo"]  # type: ignore
            motivo = evento["motivo"]  # type: ignore
            self._log.append(f"{arquivo} — {motivo}", "erro")
            # Força a exibição do console em caso de erro
            if not self._terminal_visivel:
                self._alternar_terminal()

        elif tipo == "concluido":
            total_ok = evento["total_sucesso"]  # type: ignore
            total_err = evento["total_erro"]  # type: ignore
            self._gerando = False
            self._validar_e_atualizar_botao()
            self._barra_prog.set(1.0)
            resumo = f"✓ Concluído: {total_ok} gerado(s)" + (
                f", {total_err} erro(s)" if total_err else ""
            )
            self._status_bar.definir("")
            self._log.append(resumo, "sucesso" if not total_err else "aviso")

    # ------------------------------------------------------------------
    # Restauração de sessão e fechamento
    # ------------------------------------------------------------------

    def _restaurar_sessao(self) -> None:
        """Restaura o estado da última sessão carregando template e planilha."""
        if self._config.ultimo_template:
            caminho = Path(self._config.ultimo_template)
            if caminho.is_file():
                self._ao_selecionar_template(caminho)

        if self._config.ultima_planilha:
            caminho = Path(self._config.ultima_planilha)
            if caminho.is_file():
                self._ao_selecionar_planilha(caminho)

        if self._config.ultima_pasta_saida:
            caminho = Path(self._config.ultima_pasta_saida)
            if caminho.is_dir():
                self._picker_saida.definir_caminho(caminho)

        self._validar_e_atualizar_botao()

    def _ao_fechar(self) -> None:
        """Salva configurações e encerra a aplicação."""
        self._config.salvar()
        log.info("Aplicação encerrada pelo usuário.")
        self.destroy()
