"""
Janela principal do Gerador de Certificados.

Fluxo em coluna única, centralizado:
- Cards de Template e Planilha → Mapeamento de Variáveis → Configurações
  de Saída → CTA "Gerar Certificados".
- A tabela de dados vive numa tela cheia própria (aberta via "Ver Tabela
  Completa"), com busca, ordenação por coluna e ativação/desativação de
  linhas individuais ou em massa.
- Drawer inferior retrátil com progresso e log de eventos da geração.
"""

from app.ui import styles
from app.ui.styles import fontes
import os
import threading
import tkinter as tk
import unicodedata
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

import customtkinter as ctk
import pandas as pd

from app.core import certificate_engine, data_loader, template_parser
from app.ui.components import (
    FilePickerCard,
    FolderPickerRow,
    LogArea,
    MappingCard,
    PreviewPlanilha,
    SectionHeader,
    StatusBar,
    TutorialCard,
    VariavelMapRow,
    adicionar_tooltip,
)
from tkinterdnd2.TkinterDnD import DnDWrapper, _require
from app.ui.styles import cores, esp, fonte_ctk, fonte_medium, fonte_titulo
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
        self._erros_lote: list = []
        self._pasta_saida_atual: Optional[Path] = None
        self._caminho_relatorio_erros: Optional[Path] = None

        self._vista_atual: str = "principal"

        # Estado da tabela de dados: linhas desativadas não entram na geração
        self._indices_excluidos: set = set()
        self._busca_tabela: str = ""
        self._ordenar_coluna: Optional[str] = None
        self._ordenar_asc: bool = True
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
        # Tamanho inicial com folga extra para a tabela de dados aparecer sem scroll
        self.geometry("1280x860")
        
        # Aplica o tema salvo antes de mostrar a janela
        styles.aplicar_tema(self._config.tema_aparencia)
        self.configure(fg_color=cores.FUNDO_PRINCIPAL)

        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Layout de coluna única — fluxo vertical de cima para baixo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)     # Header fixo
        self.grid_rowconfigure(1, weight=1)     # Conteúdo principal elástico
        self.grid_rowconfigure(2, weight=0)     # Drawer de log (oculto por padrão)
        self.grid_rowconfigure(3, weight=0)     # StatusBar fixa

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self._configurar_atalhos_teclado()

    def _configurar_atalhos_teclado(self) -> None:
        """
        Atalhos globais da janela:
        - Ctrl+O: abrir diálogo do template
        - Ctrl+Shift+O: abrir diálogo da planilha
        - Enter: dispara "Gerar Certificados" quando habilitado
        - Esc: volta da tela de tabela/configurações para o fluxo principal
        """
        self.bind("<Control-o>", lambda e: self._picker_template._abrir_dialogo())
        self.bind("<Control-O>", lambda e: self._picker_template._abrir_dialogo())
        self.bind("<Control-Shift-o>", lambda e: self._picker_planilha._abrir_dialogo())
        self.bind("<Control-Shift-O>", lambda e: self._picker_planilha._abrir_dialogo())
        self.bind("<Return>", self._ao_pressionar_enter)
        self.bind("<Escape>", self._ao_pressionar_esc)

    def _ao_pressionar_enter(self, _event=None) -> None:
        # Não dispara enquanto o usuário está digitando num campo de texto
        foco = self.focus_get()
        if isinstance(foco, (tk.Entry, ctk.CTkEntry)):
            return
        if str(self._btn_gerar.cget("state")) == "normal":
            self._iniciar_geracao()

    def _ao_pressionar_esc(self, _event=None) -> None:
        if self._vista_atual != "principal":
            self._ir_para("principal")

    # ------------------------------------------------------------------
    # Construção do layout
    # ------------------------------------------------------------------

    def _construir_layout(self) -> None:
        """Constrói todos os painéis da janela."""
        self._construir_header()
        self._construir_painel_principal()
        self._construir_painel_inferior()

        # O terminal inicia escondido (não chamamos .grid() no painel_inferior por padrão)
        self._terminal_visivel = False

        self._status_bar = StatusBar(self, ao_clicar_console=self._alternar_terminal)
        self._status_bar.grid(row=3, column=0, sticky="ew")

    def _construir_header(self) -> None:
        """Cabeçalho superior com design compacto e minimalista."""
        header = ctk.CTkFrame(
            self, fg_color=cores.FUNDO_PRINCIPAL, height=64, corner_radius=0
        )
        header.grid(row=0, column=0, sticky="ew")
        header.pack_propagate(False)

        # Título principal
        ctk.CTkLabel(
            header,
            text=self.TITULO_APP,
            font=fonte_titulo(fontes.TAMANHO_SUBTITULO),
            text_color=cores.TEXTO_PRINCIPAL,
        ).pack(side="left", padx=esp.PADDING_GRANDE)

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
        self._btn_config.pack(side="right", padx=(0, esp.PADDING_GRANDE))
        adicionar_tooltip(self._btn_config, "Configurações do aplicativo (tema claro/escuro).")

        # Botão de Ajuda / Tutorial
        self._btn_ajuda = ctk.CTkButton(
            header,
            text="?",
            width=32,
            height=32,
            font=fonte_titulo(14),
            fg_color="transparent",
            text_color=cores.TEXTO_SECUNDARIO,
            hover_color=cores.FUNDO_PAINEL,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
            corner_radius=16,
            command=self._alternar_ajuda,
        )
        self._btn_ajuda.pack(side="right", padx=(0, esp.PADDING_PEQUENO))
        adicionar_tooltip(self._btn_ajuda, "Tutorial: como usar o app passo a passo.")

        # Divisor sutil
        ctk.CTkFrame(header, fg_color=cores.DIVISOR, height=2).pack(
            fill="x", side="bottom"
        )

    # Largura máxima do conteúdo central — evita que inputs/botões estiquem
    # até a borda da janela em monitores largos.
    LARGURA_MAX_CONTEUDO = 760

    def _construir_painel_principal(self) -> None:
        """
        Fluxo principal em coluna única, centralizado e com largura limitada:
        2 cards de arquivo → mapeamento → configurações de saída → CTA.

        A tabela de dados NÃO fica mais embutida aqui — ela vive numa tela
        cheia própria (ver `_construir_painel_tabela`), aberta a partir do
        resumo "Ver Tabela Completa". Isso evita que os dois disputem
        espaço vertical na mesma tela.
        """
        self._painel_principal = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=cores.PRIMARIA,
        )
        self._painel_principal.grid(row=1, column=0, sticky="nsew")

        # Colunas-espaçadoras nas laterais centralizam o conteúdo e limitam sua largura
        self._painel_principal.grid_columnconfigure(0, weight=1)
        self._painel_principal.grid_columnconfigure(1, weight=0, minsize=self.LARGURA_MAX_CONTEUDO)
        self._painel_principal.grid_columnconfigure(2, weight=1)

        conteudo = ctk.CTkFrame(self._painel_principal, fg_color="transparent")
        conteudo.grid(row=0, column=1, sticky="ew", pady=esp.PADDING_MEDIO)
        conteudo.grid_columnconfigure(0, weight=1)

        self._construir_cards_origem(conteudo)
        self._construir_secao_mapeamento(conteudo)
        self._construir_config_saida(conteudo)
        self._construir_resumo_dados(conteudo)
        self._construir_cta_gerar(conteudo)

    def _construir_cards_origem(self, master) -> None:
        """Banner de boas-vindas (só no 1º uso) + 2 cards: Template e Planilha."""
        cards = ctk.CTkFrame(master, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        cards.grid_columnconfigure((0, 1), weight=1, uniform="cards")
        cards.grid_rowconfigure(1, minsize=88)

        self._banner_boasvindas = ctk.CTkLabel(
            cards,
            text="👋  Comece arrastando um template .pptx/.docx e uma planilha de dados nos cards abaixo — ou clique neles para procurar o arquivo.",
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
            fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_PEQUENO,
            anchor="w",
            justify="left",
            wraplength=self.LARGURA_MAX_CONTEUDO - 32,
            height=34,
        )
        self._banner_boasvindas.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10), ipady=6, padx=2)

        self._picker_template = FilePickerCard(
            cards,
            icone="📄",
            titulo="Template",
            subtitulo=".pptx ou .docx",
            tipos_arquivo=[
                ("Templates compatíveis", "*.pptx *.docx"),
                ("PowerPoint", "*.pptx"),
                ("Word", "*.docx"),
            ],
            callback_selecao=self._ao_selecionar_template,
            valor_inicial=self._config.ultimo_template,
        )
        self._picker_template.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self._picker_planilha = FilePickerCard(
            cards,
            icone="📊",
            titulo="Planilha de Dados",
            subtitulo=".xlsx, .ods ou .csv",
            tipos_arquivo=[
                ("Planilhas", "*.xlsx *.xls *.ods *.csv"),
                ("Excel", "*.xlsx *.xls"),
                ("OpenDocument", "*.ods"),
                ("CSV", "*.csv"),
            ],
            callback_selecao=self._ao_selecionar_planilha,
            valor_inicial=self._config.ultima_planilha,
        )
        self._picker_planilha.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

        # Se já houver sessão restaurada, não faz sentido mostrar o banner de 1º uso
        if self._picker_template.caminho or self._picker_planilha.caminho:
            self._banner_boasvindas.grid_remove()

    def _construir_secao_mapeamento(self, master) -> None:
        """
        Mapeamento de variáveis em largura total.

        Só ocupa espaço na tela depois que o template é carregado — evita
        poluir a tela com uma seção vazia antes de haver algo a mapear.
        """
        self._mapping_card = MappingCard(
            master,
            acao_callback=self._atualizar_mapeamento,
        )
        # Ainda não exibido — _atualizar_mapeamento chama grid()/grid_remove()

        # Aliases usados pelo restante da classe (mesmo papel do antigo _frame_vars)
        self._frame_vars = self._mapping_card.container
        self._lbl_sem_vars = self._mapping_card.placeholder

    def _construir_config_saida(self, master) -> None:
        """
        Configurações de saída agrupadas num card com título próprio —
        deixa claro que "pasta de destino" e "nome do arquivo" são
        opções de configuração, não parte do botão Gerar logo abaixo.
        """
        card = ctk.CTkFrame(
            master,
            fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_GRANDE,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
        )
        card.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text="Configurações de Saída",
            font=fonte_titulo(fontes.TAMANHO_NORMAL),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=esp.PADDING_MEDIO, pady=(esp.PADDING_MEDIO, esp.PADDING_PEQUENO))

        self._picker_saida = FolderPickerRow(
            card,
            rotulo="Pasta de Destino",
            callback_selecao=self._ao_selecionar_pasta_saida,
            valor_inicial=self._config.ultima_pasta_saida,
        )
        self._picker_saida.grid(row=1, column=0, sticky="new", padx=(esp.PADDING_MEDIO, esp.PADDING_PEQUENO), pady=(0, esp.PADDING_MEDIO))

        opcoes = ctk.CTkFrame(card, fg_color="transparent")
        opcoes.grid(row=1, column=1, sticky="new", padx=(esp.PADDING_PEQUENO, esp.PADDING_MEDIO), pady=(0, esp.PADDING_MEDIO))

        lbl_padrao = ctk.CTkLabel(
            opcoes,
            text="NOME DOS ARQUIVOS",
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
        )
        lbl_padrao.pack(fill="x", pady=(0, 4))

        frame_padrao = ctk.CTkFrame(
            opcoes,
            fg_color=cores.FUNDO_INPUT,
            corner_radius=esp.RAIO_MEDIO,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
        )
        frame_padrao.pack(fill="x")

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

        self._entry_padrao.bind("<KeyRelease>", lambda e: self._atualizar_preview_nome())
        self._entry_padrao.bind("<FocusOut>", self._ao_mudar_padrao_nome)
        adicionar_tooltip(
            self._entry_padrao,
            "Use as variáveis do template (ex: {{NOME}}) e as tags do sistema:\n"
            "{DATA} = data atual, {HORA} = hora atual, {INDICE} = número sequencial (0001, 0002...).",
        )

        self._lbl_preview_nome = ctk.CTkLabel(
            opcoes,
            text="PREVIEW: ...",
            font=fonte_medium(10),
            text_color=cores.PRIMARIA,
            anchor="w",
            wraplength=320,
            justify="left",
        )
        self._lbl_preview_nome.pack(fill="x", pady=(6, 0))

        self._lbl_dica_vars = ctk.CTkLabel(
            opcoes,
            text="Variáveis disponíveis: (carregue um template)",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_DESABILITADO,
            anchor="w",
            wraplength=320,
            justify="left",
        )
        self._lbl_dica_vars.pack(fill="x", pady=(0, 6))

        self._var_pdf = ctk.BooleanVar(value=self._config.exportar_pdf)
        self._chk_pdf = ctk.CTkCheckBox(
            opcoes,
            text="Gerar exportação em PDF",
            variable=self._var_pdf,
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            command=self._ao_mudar_pdf,
            fg_color=cores.PRIMARIA,
            hover_color=cores.PRIMARIA_HOVER,
            border_color=cores.BORDA_SUTIL,
            corner_radius=esp.RAIO_PEQUENO - 4,
        )
        self._chk_pdf.pack(fill="x")
        adicionar_tooltip(
            self._chk_pdf,
            "Gera um .pdf de cada certificado além do arquivo editável (.pptx/.docx).\n"
            "Requer PowerPoint ou LibreOffice instalado.",
        )

        if not certificate_engine.pdf_disponivel():
            self._chk_pdf.configure(state="disabled", text="PDF (PowerPoint/LibreOffice não enc.)")

    def _construir_resumo_dados(self, master) -> None:
        """
        Resumo compacto da planilha carregada + acesso à tabela completa.

        A tabela em si vive numa tela cheia própria (`_alternar_tabela`) —
        aqui só mostramos a contagem de linhas/colunas e um botão de acesso,
        pra não competir por espaço vertical com o resto do formulário.
        """
        faixa = ctk.CTkFrame(
            master,
            fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_MEDIO,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
        )
        faixa.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        faixa.grid_columnconfigure(0, weight=1)

        self._lbl_resumo_dados = ctk.CTkLabel(
            faixa,
            text="📊  Carregue uma planilha para ver os dados",
            font=fonte_medium(fontes.TAMANHO_NORMAL),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
        )
        self._lbl_resumo_dados.grid(
            row=0, column=0, sticky="ew", padx=(esp.PADDING_MEDIO, esp.PADDING_PEQUENO), pady=esp.PADDING_PEQUENO
        )

        self._btn_ver_tabela = ctk.CTkButton(
            faixa,
            text="Ver Tabela Completa  →",
            width=180,
            height=34,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=esp.RAIO_PEQUENO - 4,
            command=self._alternar_tabela,
            state="disabled",
        )
        self._btn_ver_tabela.grid(row=0, column=1, padx=(esp.PADDING_PEQUENO, esp.PADDING_MEDIO), pady=esp.PADDING_PEQUENO)
        adicionar_tooltip(
            self._btn_ver_tabela,
            "Veja todos os participantes, busque, ordene e desative linhas que não devem gerar certificado.",
        )

    def _construir_cta_gerar(self, master) -> None:
        """CTA principal — destaque de cor, mas em escala com o resto da UI."""
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=4, column=0, sticky="ew", pady=(0, 16))
        bloco.grid_columnconfigure(0, weight=1)

        self._btn_gerar = ctk.CTkButton(
            bloco,
            text="GERAR CERTIFICADOS",
            height=44,
            font=fonte_titulo(fontes.TAMANHO_NORMAL),
            corner_radius=esp.RAIO_PEQUENO,
            command=self._iniciar_geracao,
            state="disabled",
        )
        self._btn_gerar.grid(row=0, column=0, sticky="ew")
        self._estilizar_btn_gerar(habilitado=False)

        self._lbl_validacao = ctk.CTkLabel(
            bloco,
            text="Preencha os campos para iniciar",
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.AVISO,
            anchor="center",
        )
        self._lbl_validacao.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        # Só aparece após um lote com erros — abre o CSV do relatório
        self._btn_ver_relatorio = ctk.CTkButton(
            bloco,
            text="📄  Ver Relatório de Erros",
            height=30,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            fg_color="transparent",
            hover_color=cores.FUNDO_CARD,
            text_color=cores.ERRO,
            border_width=1,
            border_color=cores.ERRO,
            corner_radius=esp.RAIO_PEQUENO - 4,
            command=self._abrir_relatorio_erros,
        )
        self._btn_ver_relatorio.grid(row=2, column=0, pady=(8, 0))
        self._btn_ver_relatorio.grid_remove()

    def _estilizar_btn_gerar(self, habilitado: bool) -> None:
        """
        Aplica um visual de "contorno" claramente distinto quando desabilitado —
        evitar depender do dimming automático do CTk, que deixava o texto quase
        invisível sobre o fundo laranja sólido.
        """
        if habilitado:
            self._btn_gerar.configure(
                fg_color=cores.PRIMARIA,
                hover_color=cores.PRIMARIA_HOVER,
                text_color=cores.TEXTO_SOBRE_PRIMARIA,
                border_width=0,
            )
        else:
            self._btn_gerar.configure(
                fg_color=cores.FUNDO_CARD,
                hover_color=cores.FUNDO_CARD,
                text_color=cores.TEXTO_DESABILITADO,
                border_width=2,
                border_color=cores.BORDA_SUTIL,
            )

    def _abrir_relatorio_erros(self) -> None:
        """Abre o CSV do relatório de erros no aplicativo padrão do sistema."""
        if self._caminho_relatorio_erros is None or not self._caminho_relatorio_erros.is_file():
            return
        try:
            os.startfile(str(self._caminho_relatorio_erros))  # nosec — arquivo gerado pelo próprio app
        except Exception as e:
            log.error("Não foi possível abrir o relatório de erros: %s", e)
            self._status_bar.definir(f"✗ Não foi possível abrir o relatório: {e}", cores.ERRO)

    def _construir_painel_tabela(self) -> None:
        """
        Tela cheia dedicada à tabela de dados — aberta a partir do botão
        "Ver Tabela Completa". Fica com a altura inteira da janela só para
        si, sem disputar espaço com o formulário de configuração.

        Permite desativar linhas individualmente (não entram na geração),
        buscar/filtrar, ordenar por coluna e aplicar ações em massa.
        """
        self._painel_tabela = ctk.CTkFrame(self, fg_color="transparent")
        self._painel_tabela.grid_columnconfigure(0, weight=1)
        self._painel_tabela.grid_rowconfigure(2, weight=1)

        cabecalho = ctk.CTkFrame(self._painel_tabela, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew", padx=esp.PADDING_GRANDE, pady=(esp.PADDING_MEDIO, esp.PADDING_PEQUENO))

        ctk.CTkButton(
            cabecalho,
            text="←  Voltar",
            width=100,
            height=32,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=esp.RAIO_PEQUENO - 4,
            command=self._alternar_tabela,
        ).pack(side="left")

        ctk.CTkLabel(
            cabecalho,
            text="Visualização dos Dados",
            font=fonte_titulo(fontes.TAMANHO_SUBTITULO),
            text_color=cores.TEXTO_PRINCIPAL,
        ).pack(side="left", padx=esp.PADDING_MEDIO)

        self._lbl_contagem_ativos = ctk.CTkLabel(
            cabecalho,
            text="",
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
        )
        self._lbl_contagem_ativos.pack(side="right")

        # Barra de busca + ações em massa
        barra = ctk.CTkFrame(self._painel_tabela, fg_color="transparent")
        barra.grid(row=1, column=0, sticky="ew", padx=esp.PADDING_GRANDE, pady=(0, esp.PADDING_PEQUENO))

        self._entry_busca_tabela = ctk.CTkEntry(
            barra,
            placeholder_text="🔍  Buscar em qualquer coluna...",
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            fg_color=cores.FUNDO_INPUT,
            border_color=cores.BORDA_SUTIL,
            corner_radius=esp.RAIO_PEQUENO,
            height=34,
            width=280,
        )
        self._entry_busca_tabela.pack(side="left")
        self._entry_busca_tabela.bind("<KeyRelease>", self._ao_buscar_tabela)

        btn_ativar_todos = ctk.CTkButton(
            barra,
            text="Ativar Todos",
            width=110,
            height=34,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=esp.RAIO_PEQUENO - 4,
            command=lambda: self._alternar_linhas_em_massa(ativar=True),
        )
        btn_ativar_todos.pack(side="left", padx=(esp.PADDING_MEDIO, esp.PADDING_MINIMO))
        adicionar_tooltip(btn_ativar_todos, "Ativa todas as linhas visíveis no momento (respeitando a busca atual).")

        btn_desativar_todos = ctk.CTkButton(
            barra,
            text="Desativar Todos",
            width=130,
            height=34,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=esp.RAIO_PEQUENO - 4,
            command=lambda: self._alternar_linhas_em_massa(ativar=False),
        )
        btn_desativar_todos.pack(side="left", padx=esp.PADDING_MINIMO)
        adicionar_tooltip(btn_desativar_todos, "Desativa todas as linhas visíveis no momento (respeitando a busca atual).")

        self._preview = PreviewPlanilha(self._painel_tabela)
        self._preview.grid(
            row=2, column=0, sticky="nsew", padx=esp.PADDING_GRANDE, pady=(0, esp.PADDING_GRANDE)
        )

    def _alternar_tabela(self) -> None:
        """Alterna entre a tela de geração e a tela cheia da tabela de dados."""
        self._ir_para("tabela")

    # ------------------------------------------------------------------
    # Tabela de dados: busca, ordenação, ativação de linhas e ações em massa
    # ------------------------------------------------------------------

    def _obter_visao_tabela(self) -> pd.DataFrame:
        """Aplica busca e ordenação atuais sobre `self._df` para exibição."""
        if self._df is None:
            return pd.DataFrame()

        visao = self._df
        if self._busca_tabela:
            termo = self._busca_tabela.lower()
            mascara = visao.apply(
                lambda linha: linha.astype(str).str.lower().str.contains(termo, regex=False).any(),
                axis=1,
            )
            visao = visao[mascara]

        if self._ordenar_coluna is not None and self._ordenar_coluna in visao.columns:
            visao = visao.sort_values(
                by=self._ordenar_coluna, ascending=self._ordenar_asc, kind="stable"
            )

        return visao

    def _renderizar_tabela(self) -> None:
        """Redesenha a tabela com o estado atual de busca/ordenação/ativação."""
        if not hasattr(self, "_preview") or self._df is None:
            return
        visao = self._obter_visao_tabela()
        self._preview.renderizar(
            visao,
            indices_excluidos=self._indices_excluidos,
            callback_alternar=self._ao_alternar_linha_ativa,
            callback_ordenar=self._ao_ordenar_coluna,
            coluna_ordenada=self._ordenar_coluna,
            ordem_crescente=self._ordenar_asc,
        )
        self._atualizar_contagem_ativos()

    def _atualizar_contagem_ativos(self) -> None:
        if self._df is None:
            return
        total = len(self._df)
        ativos = total - len(self._indices_excluidos)
        if hasattr(self, "_lbl_contagem_ativos"):
            self._lbl_contagem_ativos.configure(text=f"{ativos} de {total} ativos para geração")

    def _ao_buscar_tabela(self, _event=None) -> None:
        self._busca_tabela = self._entry_busca_tabela.get().strip()
        self._renderizar_tabela()

    def _ao_ordenar_coluna(self, coluna: str) -> None:
        if self._ordenar_coluna == coluna:
            self._ordenar_asc = not self._ordenar_asc
        else:
            self._ordenar_coluna = coluna
            self._ordenar_asc = True
        self._renderizar_tabela()

    def _ao_alternar_linha_ativa(self, indice: object, ativo: bool) -> None:
        if ativo:
            self._indices_excluidos.discard(indice)
        else:
            self._indices_excluidos.add(indice)
        self._atualizar_contagem_ativos()
        self._atualizar_resumo_dados()
        self._validar_e_atualizar_botao()

    def _alternar_linhas_em_massa(self, ativar: bool) -> None:
        """Ativa/desativa todas as linhas atualmente visíveis (respeitando a busca)."""
        if self._df is None:
            return
        indices_visiveis = set(self._obter_visao_tabela().index)
        if ativar:
            self._indices_excluidos -= indices_visiveis
        else:
            self._indices_excluidos |= indices_visiveis
        self._renderizar_tabela()
        self._atualizar_resumo_dados()
        self._validar_e_atualizar_botao()

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
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
        ).pack(side="left")

        self._lbl_contador = ctk.CTkLabel(
            header_prog,
            text="0 / 0",
            font=fonte_medium(fontes.TAMANHO_NORMAL),
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
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
        ).pack(side="left")

        ctk.CTkButton(
            terminal_header,
            text="LIMPAR",
            width=60,
            height=20,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
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
        
        content = ctk.CTkFrame(self._painel_config, fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_GRANDE)
        content.pack(expand=True, padx=100, pady=50)
        
        SectionHeader(content, "Preferências do Aplicativo", "⚙️").pack(fill="x", padx=40, pady=(40, 20))
        
        # Opção de Tema
        frame_tema = ctk.CTkFrame(content, fg_color="transparent")
        frame_tema.pack(fill="x", padx=40, pady=20)
        
        ctk.CTkLabel(
            frame_tema, 
            text="TEMA DA INTERFACE", 
            font=fonte_medium(fontes.TAMANHO_NORMAL),
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
        self._ir_para("config")

    def _alternar_ajuda(self) -> None:
        """Alterna entre a tela de geração e o tutorial de ajuda."""
        self._ir_para("ajuda")

    def _ir_para(self, vista: str) -> None:
        """
        Mostra uma das telas da aplicação, escondendo as demais.

        `vista` é um de "principal", "config", "tabela" ou "ajuda". Chamar
        de novo com a vista já ativa volta para "principal" (toggle) — é
        assim que os botões de cabeçalho e os "← Voltar" funcionam.
        Centraliza a troca de painéis num só lugar para não perder o
        estado de qual tela o usuário estava vendo antes de outra abrir
        por cima (bug do modo antigo: fechar Configurações sempre voltava
        para o formulário, mesmo se você estivesse na tabela).
        """
        if vista == self._vista_atual:
            vista = "principal"

        # Esconde tudo
        self._painel_principal.grid_forget()
        if hasattr(self, "_painel_config"):
            self._painel_config.grid_forget()
        if hasattr(self, "_painel_tabela"):
            self._painel_tabela.grid_forget()
        if hasattr(self, "_painel_ajuda"):
            self._painel_ajuda.grid_forget()
        self._painel_inferior.grid_forget()

        self._vista_atual = vista

        if vista == "config":
            if not hasattr(self, "_painel_config"):
                self._construir_painel_configuracoes()
            self._painel_config.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
            self._btn_config.configure(text="🏠", text_color=cores.PRIMARIA)
            self._status_bar.definir("CONFIGURAÇÕES DO SISTEMA", cores.INFO)
        elif vista == "tabela":
            if not hasattr(self, "_painel_tabela"):
                self._construir_painel_tabela()
            self._renderizar_tabela()
            self._painel_tabela.grid(row=1, column=0, sticky="nsew")
            self._btn_config.configure(text="⚙️", text_color=cores.TEXTO_SECUNDARIO)
            self._status_bar.definir("VISUALIZAÇÃO DE DADOS", cores.INFO)
        elif vista == "ajuda":
            if not hasattr(self, "_painel_ajuda"):
                self._construir_painel_ajuda()
            self._painel_ajuda.grid(row=1, column=0, sticky="nsew")
            self._btn_config.configure(text="⚙️", text_color=cores.TEXTO_SECUNDARIO)
            self._status_bar.definir("AJUDA E TUTORIAL", cores.INFO)
        else:
            self._painel_principal.grid(row=1, column=0, sticky="nsew")
            if self._terminal_visivel:
                self._painel_inferior.grid(row=2, column=0, sticky="ew")
            self._btn_config.configure(text="⚙️", text_color=cores.TEXTO_SECUNDARIO)
            self._status_bar.definir("SISTEMA PRONTO", cores.SUCESSO)

    def _construir_painel_ajuda(self) -> None:
        """
        Tela cheia de ajuda/tutorial — passo a passo do fluxo completo,
        cada passo com uma reprodução em miniatura do elemento real da
        interface (não uma imagem estática) ao lado do texto explicativo.
        """
        self._painel_ajuda = ctk.CTkFrame(self, fg_color="transparent")
        self._painel_ajuda.grid_columnconfigure(0, weight=1)
        self._painel_ajuda.grid_rowconfigure(1, weight=1)

        cabecalho = ctk.CTkFrame(self._painel_ajuda, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew", padx=esp.PADDING_GRANDE, pady=(esp.PADDING_MEDIO, esp.PADDING_PEQUENO))

        ctk.CTkButton(
            cabecalho,
            text="←  Voltar",
            width=100,
            height=32,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=esp.RAIO_PEQUENO - 4,
            command=self._alternar_ajuda,
        ).pack(side="left")

        ctk.CTkLabel(
            cabecalho,
            text="Como Usar o Gerador de Certificados",
            font=fonte_titulo(fontes.TAMANHO_SUBTITULO),
            text_color=cores.TEXTO_PRINCIPAL,
        ).pack(side="left", padx=esp.PADDING_MEDIO)

        scroll = ctk.CTkScrollableFrame(
            self._painel_ajuda, fg_color="transparent", scrollbar_button_color=cores.PRIMARIA,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=esp.PADDING_GRANDE, pady=(0, esp.PADDING_GRANDE))

        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=0, minsize=self.LARGURA_MAX_CONTEUDO)
        scroll.grid_columnconfigure(2, weight=1)

        coluna = ctk.CTkFrame(scroll, fg_color="transparent")
        coluna.grid(row=0, column=1, sticky="ew")
        coluna.grid_columnconfigure(0, weight=1)

        for i, (icone, titulo, descricao, construir_preview) in enumerate(self._passos_tutorial()):
            TutorialCard(coluna, icone, titulo, descricao, construir_preview).grid(
                row=i, column=0, sticky="ew", pady=(0, esp.PADDING_MEDIO)
            )

    def _passos_tutorial(self) -> list:
        """Conteúdo do tutorial: (ícone, título, texto, construtor do mini-preview)."""

        def preview_arquivos(frame) -> None:
            for icone, rotulo in (("📄", "Template"), ("📊", "Planilha de Dados")):
                mini = ctk.CTkFrame(
                    frame, fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_PEQUENO,
                    border_width=1, border_color=cores.BORDA_DESTAQUE, width=140, height=56,
                )
                mini.pack(side="left", padx=(0, esp.PADDING_PEQUENO))
                mini.pack_propagate(False)
                ctk.CTkLabel(mini, text=icone, font=ctk.CTkFont(size=18), text_color=cores.PRIMARIA).pack(pady=(8, 0))
                ctk.CTkLabel(
                    mini, text=rotulo, font=fonte_medium(fontes.TAMANHO_PEQUENO), text_color=cores.TEXTO_SECUNDARIO,
                ).pack()

        def preview_mapeamento(frame) -> None:
            linha = ctk.CTkFrame(frame, fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_PEQUENO)
            linha.pack()
            ctk.CTkLabel(
                linha, text="{{NOME}}", font=fonte_medium(fontes.TAMANHO_NORMAL), text_color=cores.TEXTO_PRINCIPAL,
            ).pack(side="left", padx=(12, 16), pady=10)
            ctk.CTkSegmentedButton(
                linha, values=["Planilha", "Texto"], height=26, width=90,
                fg_color=cores.FUNDO_PRINCIPAL, selected_color=cores.PRIMARIA,
                unselected_color=cores.FUNDO_INPUT,
            ).pack(side="left", padx=(0, 12))
            ctk.CTkOptionMenu(
                linha, values=["Nome Completo"], width=140, height=26,
                fg_color=cores.FUNDO_INPUT, button_color=cores.FUNDO_CARD,
                font=fonte_ctk(fontes.TAMANHO_PEQUENO),
            ).pack(side="left", padx=(0, 12))

        def preview_saida(frame) -> None:
            linha = ctk.CTkFrame(frame, fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_PEQUENO)
            linha.pack()
            ctk.CTkLabel(
                linha, text="📁  C:\\Certificados\\Turma-2026",
                font=fonte_ctk(fontes.TAMANHO_PEQUENO), text_color=cores.TEXTO_SECUNDARIO,
            ).pack(side="left", padx=(12, 16), pady=10)
            ctk.CTkButton(
                linha, text="Alterar", width=80, height=26, font=fonte_medium(fontes.TAMANHO_PEQUENO),
                fg_color=cores.FUNDO_CARD, hover_color=cores.BORDA_SUTIL, text_color=cores.TEXTO_PRINCIPAL,
                corner_radius=esp.RAIO_PEQUENO - 4,
            ).pack(side="left", padx=(0, 12))

        def preview_tabela(frame) -> None:
            linha = ctk.CTkFrame(frame, fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_PEQUENO)
            linha.pack()
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(
                linha, text="", variable=var, width=20, checkbox_width=18, checkbox_height=18,
                fg_color=cores.PRIMARIA,
            ).pack(side="left", padx=(12, 8), pady=10)
            ctk.CTkLabel(
                linha, text="Ana Silva", font=fonte_ctk(fontes.TAMANHO_NORMAL), text_color=cores.TEXTO_PRINCIPAL,
            ).pack(side="left", padx=(0, 16))
            ctk.CTkLabel(
                linha, text="🔍  Buscar...", font=fonte_ctk(fontes.TAMANHO_PEQUENO), text_color=cores.TEXTO_SECUNDARIO,
                fg_color=cores.FUNDO_INPUT, corner_radius=esp.RAIO_PEQUENO - 4,
            ).pack(side="left", padx=(0, 12), pady=6, ipady=4, ipadx=8)

        def preview_gerar(frame) -> None:
            ctk.CTkButton(
                frame, text="GERAR CERTIFICADOS", height=44, width=260,
                font=fonte_titulo(fontes.TAMANHO_NORMAL), corner_radius=esp.RAIO_PEQUENO,
                fg_color=cores.PRIMARIA, hover_color=cores.PRIMARIA_HOVER,
                text_color=cores.TEXTO_SOBRE_PRIMARIA,
            ).pack()

        def preview_atalhos(frame) -> None:
            atalhos = [
                ("Ctrl+O", "Abrir template"),
                ("Ctrl+Shift+O", "Abrir planilha"),
                ("Enter", "Gerar certificados"),
                ("Esc", "Voltar ao início"),
            ]
            for i, (tecla, acao) in enumerate(atalhos):
                linha = ctk.CTkFrame(frame, fg_color="transparent")
                linha.grid(row=i, column=0, sticky="w", pady=2)
                ctk.CTkLabel(
                    linha, text=tecla, font=fonte_medium(fontes.TAMANHO_PEQUENO), text_color=cores.PRIMARIA,
                    fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_PEQUENO - 4, width=110,
                ).pack(side="left", ipady=4)
                ctk.CTkLabel(
                    linha, text=acao, font=fonte_ctk(fontes.TAMANHO_PEQUENO), text_color=cores.TEXTO_SECUNDARIO,
                ).pack(side="left", padx=(10, 0))

        return [
            (
                "1️⃣",
                "Escolha o Template e a Planilha",
                "Arraste um arquivo .pptx ou .docx sobre o card de Template — ou clique nele para procurar "
                "pelo explorador de arquivos. Faça o mesmo com sua planilha (.xlsx, .ods ou .csv) no card ao lado. "
                "O app detecta sozinho as variáveis {{VARIAVEL}} presentes no seu certificado.",
                preview_arquivos,
            ),
            (
                "2️⃣",
                "Vincule as Variáveis às Colunas",
                "Assim que os dois arquivos estiverem carregados, aparece a seção de Mapeamento. O app já tenta "
                "adivinhar sozinho qual coluna da planilha corresponde a cada variável do template. Se errar, "
                "escolha manualmente no menu — ou use o modo \"Texto\" para preencher com um valor fixo, igual em "
                "todos os certificados (ex: nome do curso).",
                preview_mapeamento,
            ),
            (
                "3️⃣",
                "Configure a Pasta de Saída",
                "Escolha onde os certificados gerados serão salvos e, se quiser, personalize o padrão de nome dos "
                "arquivos (ex: \"{{NOME}} - {DATA}\"). Marque \"Gerar exportação em PDF\" se também precisar de "
                "uma versão em PDF de cada certificado, além do arquivo editável.",
                preview_saida,
            ),
            (
                "4️⃣",
                "Revise os Dados na Tabela",
                "Clique em \"Ver Tabela Completa\" para conferir todos os participantes antes de gerar. Você pode "
                "buscar por nome, ordenar clicando no cabeçalho da coluna, e desmarcar a caixinha de uma linha para "
                "excluir aquele participante da geração — sem precisar editar a planilha original. Os botões "
                "\"Ativar/Desativar Todos\" agem sobre as linhas visíveis no momento (respeitando sua busca).",
                preview_tabela,
            ),
            (
                "5️⃣",
                "Gere os Certificados",
                "Com tudo pronto, o botão fica laranja e habilitado. Clique para iniciar — acompanhe o progresso "
                "pela barra e pelo contador. Se algum participante der erro (ex: campo vazio), o lote continua "
                "normalmente e um botão \"Ver Relatório de Erros\" aparece ao final, com um CSV detalhando cada falha.",
                preview_gerar,
            ),
            (
                "⌨️",
                "Atalhos de Teclado",
                "Pra quem prefere não tirar a mão do teclado:",
                preview_atalhos,
            ),
        ]

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
            self._painel_inferior.grid(row=2, column=0, sticky="ew")
            self._terminal_visivel = True
            self._status_bar._btn_terminal.configure(fg_color=cores.PRIMARIA)

    # ------------------------------------------------------------------
    # Callbacks de seleção de arquivo
    # ------------------------------------------------------------------

    def _esconder_banner_boasvindas(self) -> None:
        """Esconde o banner de 1º uso assim que o usuário carrega algum arquivo."""
        if hasattr(self, "_banner_boasvindas"):
            self._banner_boasvindas.grid_remove()

    def _ao_selecionar_template(self, caminho: Path) -> None:
        """Detecta variáveis do template e atualiza o painel central."""
        self._status_bar.definir("⏳ Analisando template...", cores.INFO)
        try:
            self._variaveis = template_parser.extrair_variaveis(caminho)
            self._config.ultimo_template = str(caminho)
            self._config.salvar()
            self._atualizar_mapeamento()
            if not self._variaveis:
                self._picker_template.definir_erro(
                    "nenhuma variável {{VAR}} encontrada no template"
                )
            else:
                self._picker_template.limpar_erro()
            self._esconder_banner_boasvindas()
            self._status_bar.definir("")
        except Exception as e:
            self._picker_template.definir_erro(str(e))
            self._status_bar.definir(f"✗ Erro ao analisar template: {e}", cores.ERRO)
            log.error("Erro ao analisar template '%s': %s", caminho, e)
        finally:
            self._validar_e_atualizar_botao()

    def _ao_selecionar_planilha(self, caminho: Path) -> None:
        """Carrega a planilha e atualiza o resumo, preview (se aberto) e dropdowns."""
        self._status_bar.definir("⏳ Carregando planilha...", cores.INFO)
        try:
            self._df = data_loader.carregar_planilha(caminho)
            self._config.ultima_planilha = str(caminho)
            self._config.salvar()
            # Nova planilha: reseta seleção, busca e ordenação da tabela
            self._indices_excluidos = set()
            self._busca_tabela = ""
            self._ordenar_coluna = None
            self._ordenar_asc = True
            if hasattr(self, "_entry_busca_tabela"):
                self._entry_busca_tabela.delete(0, "end")
            self._atualizar_resumo_dados()
            # A tabela em tela cheia é construída sob demanda — só renderiza se já existir
            if hasattr(self, "_preview"):
                self._renderizar_tabela()
            self._atualizar_colunas_nos_dropdowns()
            self._picker_planilha.limpar_erro()
            self._esconder_banner_boasvindas()
            self._status_bar.definir("")
        except Exception as e:
            self._picker_planilha.definir_erro(str(e))
            self._status_bar.definir(f"✗ Erro ao carregar planilha: {e}", cores.ERRO)
            log.error("Erro ao carregar planilha '%s': %s", caminho, e)
        finally:
            self._atualizar_preview_nome()
            self._validar_e_atualizar_botao()

    def _atualizar_resumo_dados(self) -> None:
        """Atualiza a faixa de resumo com a contagem de linhas/colunas carregadas."""
        if self._df is None:
            self._lbl_resumo_dados.configure(
                text="📊  Carregue uma planilha para ver os dados",
                text_color=cores.TEXTO_SECUNDARIO,
            )
            self._btn_ver_tabela.configure(state="disabled")
            return

        total, colunas = len(self._df), len(self._df.columns)
        ativos = total - len(self._indices_excluidos)
        sufixo = f" · {len(self._indices_excluidos)} desativada(s)" if self._indices_excluidos else ""
        self._lbl_resumo_dados.configure(
            text=f"📊  {ativos} de {total} linha(s) ativas · {colunas} coluna(s){sufixo}",
            text_color=cores.TEXTO_PRINCIPAL,
        )
        self._btn_ver_tabela.configure(state="normal")

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
            self._mapping_card.grid_remove()
            self._lbl_sem_vars.pack(pady=24)
            if hasattr(self, "_lbl_dica_vars"):
                self._lbl_dica_vars.configure(text="Disponíveis: (carregue um template)")
            return

        self._mapping_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
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
        linhas_ativas_ok = self._df is not None and len(self._indices_excluidos) < len(self._df)
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

        tudo_ok = template_ok and planilha_ok and linhas_ativas_ok and saida_ok and mapeamento_ok

        if tudo_ok and not self._gerando:
            self._btn_gerar.configure(state="normal")
            self._estilizar_btn_gerar(habilitado=True)
            self._lbl_validacao.configure(
                text="✓ Pronto para gerar", text_color=cores.SUCESSO
            )
        elif self._gerando:
            self._btn_gerar.configure(state="disabled")
            self._estilizar_btn_gerar(habilitado=False)
            self._lbl_validacao.configure(
                text="⏳ Gerando certificados...", text_color=cores.INFO
            )
        else:
            self._btn_gerar.configure(state="disabled")
            self._estilizar_btn_gerar(habilitado=False)
            pendentes = []
            if not template_ok:
                pendentes.append("template")
            if not planilha_ok:
                pendentes.append("planilha")
            elif not linhas_ativas_ok:
                pendentes.append("ao menos 1 linha ativa na tabela")
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

        # Só as linhas ativas (não desmarcadas na tabela) entram na geração
        dados_ativos = self._df.drop(index=self._indices_excluidos, errors="ignore")
        if dados_ativos.empty:
            return

        self._gerando = True
        self._erros_lote = []
        self._pasta_saida_atual = pasta_saida
        self._caminho_relatorio_erros = None
        self._btn_ver_relatorio.grid_remove()
        self._validar_e_atualizar_botao()
        self._btn_gerar.configure(text="GERANDO...")
        self._log.limpar()
        self._barra_prog.set(0)
        self._barra_prog.configure(progress_color=cores.PRIMARIA)
        self._lbl_contador.configure(text=f"0 / {len(dados_ativos)}")
        self._status_bar.definir("⏳ Gerando certificados...", cores.INFO)
        if self._indices_excluidos:
            self._log.append(
                f"{len(self._indices_excluidos)} linha(s) desativada(s) na tabela — não entram na geração.",
                "aviso",
            )
        self._log.append(
            f"Iniciando geração de {len(dados_ativos)} certificado(s)...", "info"
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
                dados_ativos,
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
            linha = evento["linha"]  # type: ignore
            arquivo = evento["arquivo"]  # type: ignore
            motivo = evento["motivo"]  # type: ignore
            self._erros_lote.append(evento)
            self._log.append(f"Linha {linha} — {arquivo} — {motivo}", "erro")
            # Força a exibição do console em caso de erro
            if not self._terminal_visivel:
                self._alternar_terminal()

        elif tipo == "concluido":
            total_ok = evento["total_sucesso"]  # type: ignore
            total_err = evento["total_erro"]  # type: ignore
            self._gerando = False
            self._btn_gerar.configure(text="GERAR CERTIFICADOS")
            self._validar_e_atualizar_botao()
            self._barra_prog.set(1.0)
            self._barra_prog.configure(
                progress_color=cores.ERRO if total_err and not total_ok else cores.SUCESSO
            )
            resumo = f"✓ Concluído: {total_ok} gerado(s)" + (
                f", {total_err} erro(s)" if total_err else ""
            )
            self._status_bar.definir("")
            self._log.append(resumo, "sucesso" if not total_err else "aviso")

            if total_err and self._pasta_saida_atual is not None:
                caminho_relatorio = certificate_engine.escrever_relatorio_erros(
                    self._pasta_saida_atual, self._erros_lote
                )
                if caminho_relatorio is not None:
                    self._caminho_relatorio_erros = caminho_relatorio
                    self._btn_ver_relatorio.grid()
                    self._log.append(
                        f"Relatório de erros salvo em: {caminho_relatorio.name}",
                        "aviso",
                    )

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
