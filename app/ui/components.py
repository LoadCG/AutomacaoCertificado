"""
Componentes reutilizáveis da interface do Gerador de Certificados.

Cada componente encapsula um conjunto de widgets CustomTkinter com
comportamento e estilo padronizados, seguindo o princípio de
responsabilidade única.

Uso:
    from app.ui.components import FilePickerRow, LogArea, VariavelMapRow
"""

from app.ui.styles import fontes
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk
import pandas as pd
from tkinterdnd2 import DND_FILES
from app.ui.styles import cores, esp, fonte_ctk, fonte_mono


# ---------------------------------------------------------------------------
# FilePickerRow — Seletor de arquivo
# ---------------------------------------------------------------------------


class FilePickerRow(ctk.CTkFrame):
    """
    Componente de seleção de arquivo refinado.
    """

    def __init__(
        self,
        master,
        rotulo: str,
        tipos_arquivo: list[tuple[str, str]],
        callback_selecao: Callable[[Path], None],
        valor_inicial: Optional[str] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")

        self._callback = callback_selecao
        self._tipos_arquivo = tipos_arquivo
        self._caminho_atual: Optional[Path] = None

        # Extrai extensões para validação no Drag & Drop (ex: ['*.pptx'] -> ['.pptx'])
        self._extensoes = []
        for _, padrao in tipos_arquivo:
            ext = padrao.replace("*", "")
            if ext:
                self._extensoes.append(ext)

        self._construir(rotulo, valor_inicial)

    def _construir(self, rotulo: str, valor_inicial: Optional[str]) -> None:
        """Constrói os widgets internos do componente."""
        # Rótulo com estilo minimalista
        self._lbl_rotulo = ctk.CTkLabel(
            self,
            text=rotulo.upper(),
            font=fonte_ctk(esp.PADDING_PEQUENO + 2, "bold"),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
        )
        self._lbl_rotulo.pack(fill="x", pady=(0, 4))

        # Frame da linha com design de 'input' moderno
        self._frame_linha = ctk.CTkFrame(
            self,
            fg_color=cores.FUNDO_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
        )
        self._frame_linha.pack(fill="x")
        self._frame_linha.grid_columnconfigure(0, weight=1)

        # Entry somente-leitura
        self._var_caminho = tk.StringVar(value=valor_inicial or "Nenhum arquivo selecionado")
        self._entry = ctk.CTkEntry(
            self._frame_linha,
            textvariable=self._var_caminho,
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            fg_color="transparent",
            border_width=0,
            text_color=cores.TEXTO_SECUNDARIO if not valor_inicial else cores.TEXTO_PRINCIPAL,
            state="readonly",
        )
        self._entry.grid(row=0, column=0, sticky="ew", padx=(12, 4), pady=10)

        # Botão de ação premium
        self._btn = ctk.CTkButton(
            self._frame_linha,
            text="Explorar",
            width=90,
            height=32,
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=8,
            command=self._abrir_dialogo,
        )
        self._btn.grid(row=0, column=1, padx=(4, 8), pady=6)

        if valor_inicial:
            self._caminho_atual = Path(valor_inicial)
            self._frame_linha.configure(border_color=cores.BORDA_DESTAQUE)

        # Configuração de Drag & Drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._ao_soltar_arquivo)
        self.dnd_bind("<<DragEnter>>", self._ao_entrar_drag)
        self.dnd_bind("<<DragLeave>>", self._ao_sair_drag)

    def _ao_entrar_drag(self, event) -> None:
        """Efeito visual ao arrastar arquivo sobre o componente."""
        self._frame_linha.configure(border_color=cores.PRIMARIA)

    def _ao_sair_drag(self, event) -> None:
        """Restaura o visual original."""
        cor = cores.BORDA_DESTAQUE if self._caminho_atual else cores.BORDA_SUTIL
        self._frame_linha.configure(border_color=cor)

    def _ao_soltar_arquivo(self, event) -> None:
        """Processa o arquivo solto no componente."""
        self._ao_sair_drag(event)
        caminho_str = event.data
        
        # O Windows/TkinterDnD às vezes retorna caminhos entre chaves ou aspas
        if caminho_str.startswith("{") and caminho_str.endswith("}"):
            caminho_str = caminho_str[1:-1]
        elif caminho_str.startswith('"') and caminho_str.endswith('"'):
            caminho_str = caminho_str[1:-1]
            
        caminho = Path(caminho_str)
        
        # Verifica extensões permitidas
        if self._extensoes:
            extensoes_validas = [ext.lower() for ext in self._extensoes]
            if caminho.suffix.lower() not in extensoes_validas:
                return

        self.definir_caminho(caminho)
        if self._callback:
            self._callback(caminho)

    def _abrir_dialogo(self) -> None:
        """Abre o diálogo de seleção de arquivo."""
        caminho_str = filedialog.askopenfilename(filetypes=self._tipos_arquivo)
        if caminho_str:
            self._caminho_atual = Path(caminho_str)
            self._var_caminho.set(self._caminho_atual.name)
            self._entry.configure(text_color=cores.TEXTO_PRINCIPAL)
            self._frame_linha.configure(border_color=cores.BORDA_DESTAQUE)
            self._callback(self._caminho_atual)

    @property
    def caminho(self) -> Optional[Path]:
        return self._caminho_atual

    def definir_caminho(self, caminho: Path) -> None:
        self._caminho_atual = caminho
        self._var_caminho.set(caminho.name)
        self._entry.configure(text_color=cores.TEXTO_PRINCIPAL)
        self._frame_linha.configure(border_color=cores.BORDA_DESTAQUE)


# ---------------------------------------------------------------------------
# FolderPickerRow — Seletor de pasta
# ---------------------------------------------------------------------------


class FolderPickerRow(ctk.CTkFrame):
    """
    Componente de seleção de diretório refinado.
    """

    def __init__(
        self,
        master,
        rotulo: str,
        callback_selecao: Callable[[Path], None],
        valor_inicial: Optional[str] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")

        self._callback = callback_selecao
        self._caminho_atual: Optional[Path] = None

        self._construir(rotulo, valor_inicial)

    def _construir(self, rotulo: str, valor_inicial: Optional[str]) -> None:
        """Constrói os widgets internos do componente."""
        lbl = ctk.CTkLabel(
            self,
            text=rotulo.upper(),
            font=fonte_ctk(esp.PADDING_PEQUENO + 2, "bold"),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
        )
        lbl.pack(fill="x", pady=(0, 4))

        self._frame_linha = ctk.CTkFrame(
            self,
            fg_color=cores.FUNDO_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
        )
        self._frame_linha.pack(fill="x")
        self._frame_linha.grid_columnconfigure(0, weight=1)

        self._var_caminho = tk.StringVar(value=valor_inicial or "Nenhuma pasta selecionada")
        self._entry = ctk.CTkEntry(
            self._frame_linha,
            textvariable=self._var_caminho,
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            fg_color="transparent",
            border_width=0,
            text_color=cores.TEXTO_SECUNDARIO if not valor_inicial else cores.TEXTO_PRINCIPAL,
            state="readonly",
        )
        self._entry.grid(row=0, column=0, sticky="ew", padx=(12, 4), pady=10)

        ctk.CTkButton(
            self._frame_linha,
            text="Alterar",
            width=90,
            height=32,
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=8,
            command=self._abrir_dialogo,
        ).grid(row=0, column=1, padx=(4, 8), pady=6)

        if valor_inicial:
            self._caminho_atual = Path(valor_inicial)
            self._frame_linha.configure(border_color=cores.BORDA_DESTAQUE)

    def _abrir_dialogo(self) -> None:
        """Abre o diálogo de seleção de pasta."""
        caminho_str = filedialog.askdirectory()
        if caminho_str:
            self._caminho_atual = Path(caminho_str)
            self._var_caminho.set(str(self._caminho_atual))
            self._entry.configure(text_color=cores.TEXTO_PRINCIPAL)
            self._frame_linha.configure(border_color=cores.BORDA_DESTAQUE)
            self._callback(self._caminho_atual)

    @property
    def caminho(self) -> Optional[Path]:
        return self._caminho_atual

    def definir_caminho(self, caminho: Path) -> None:
        self._caminho_atual = caminho
        self._var_caminho.set(str(caminho))
        self._entry.configure(text_color=cores.TEXTO_PRINCIPAL)
        self._frame_linha.configure(border_color=cores.BORDA_DESTAQUE)


# ---------------------------------------------------------------------------
# VariavelMapRow — Linha de mapeamento variável ↔ coluna
# ---------------------------------------------------------------------------


class VariavelMapRow(ctk.CTkFrame):
    """
    Linha de mapeamento refinada com modo Coluna/Texto.
    """

    _COR_AVISO = cores.AVISO
    _COR_OK = cores.SUCESSO

    def __init__(
        self,
        master,
        variavel: str,
        colunas: list[str],
        callback_mudanca: Callable[[str, str], None],
    ) -> None:
        super().__init__(master, fg_color=cores.FUNDO_PAINEL, corner_radius=12)

        self._variavel = variavel
        self._callback = callback_mudanca
        self._colunas = colunas
        self._modo_fixo = False

        self._construir()

    def _construir(self) -> None:
        """Constrói a linha de mapeamento com foco em clareza."""
        self.grid_columnconfigure(1, weight=1)
        self.configure(border_width=1, border_color=cores.BORDA_SUTIL)

        # Indicador de status elegante
        self._indicador = ctk.CTkLabel(
            self,
            text="●",
            font=fonte_ctk(16),
            text_color=self._COR_AVISO,
            width=30,
        )
        self._indicador.grid(row=0, column=0, padx=(12, 4), pady=12)

        # Nome da variável em destaque
        ctk.CTkLabel(
            self,
            text=self._variavel,
            font=fonte_ctk(fontes.TAMANHO_NORMAL, "bold"),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=4, pady=12)

        # Seletor de modo (Design Segmentado Moderno)
        self._seg_button = ctk.CTkSegmentedButton(
            self,
            values=["Planilha", "Texto"],
            command=self._alternar_modo,
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            height=28,
            width=100,
            fg_color=cores.FUNDO_PRINCIPAL,
            selected_color=cores.PRIMARIA,
            selected_hover_color=cores.PRIMARIA_HOVER,
            unselected_color=cores.FUNDO_INPUT,
            unselected_hover_color=cores.FUNDO_CARD,
        )
        self._seg_button.set("Planilha")
        self._seg_button.grid(row=0, column=2, padx=12)

        # Container para os inputs
        self._container_input = ctk.CTkFrame(self, fg_color="transparent")
        self._container_input.grid(row=0, column=3, padx=(4, 16), pady=10)

        # Dropdown refinado
        opcoes = ["(selecione uma coluna)"] + self._colunas
        self._var_coluna = tk.StringVar(value=opcoes[0])
        self._dropdown = ctk.CTkOptionMenu(
            self._container_input,
            values=opcoes,
            variable=self._var_coluna,
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            fg_color=cores.FUNDO_INPUT,
            button_color=cores.FUNDO_CARD,
            button_hover_color=cores.BORDA_SUTIL,
            dropdown_fg_color=cores.FUNDO_PAINEL,
            dropdown_hover_color=cores.FUNDO_CARD,
            command=self._ao_mudar_dropdown,
            width=200,
            height=34,
            corner_radius=8,
        )
        self._dropdown.pack(fill="x")

        # Entry de texto fixo
        self._var_texto = tk.StringVar()
        self._entry_texto = ctk.CTkEntry(
            self._container_input,
            textvariable=self._var_texto,
            placeholder_text="Digite o valor fixo...",
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            fg_color=cores.FUNDO_INPUT,
            border_color=cores.BORDA_SUTIL,
            width=200,
            height=34,
            corner_radius=8,
        )
        self._var_texto.trace_add("write", lambda *args: self._ao_mudar_texto())

    def _alternar_modo(self, modo: str) -> None:
        """Alterna modos com animação visual (pack/forget)."""
        if modo == "Texto":
            self._modo_fixo = True
            self._dropdown.pack_forget()
            self._entry_texto.pack(fill="x")
            self._ao_mudar_texto()
        else:
            self._modo_fixo = False
            self._entry_texto.pack_forget()
            self._dropdown.pack(fill="x")
            self._ao_mudar_dropdown(self._var_coluna.get())

    def _ao_mudar_dropdown(self, valor: str) -> None:
        if valor == "(selecione uma coluna)":
            self._indicador.configure(text_color=self._COR_AVISO)
            self.configure(border_color=cores.BORDA_SUTIL)
        else:
            self._indicador.configure(text_color=self._COR_OK)
            self.configure(border_color=cores.BORDA_DESTAQUE)
        self._callback(self._variavel, valor)

    def _ao_mudar_texto(self) -> None:
        texto = self._var_texto.get().strip()
        if not texto:
            self._indicador.configure(text_color=cores.ERRO)
            self.configure(border_color=cores.BORDA_SUTIL)
            self._entry_texto.configure(border_color=cores.ERRO)
        else:
            self._indicador.configure(text_color=self._COR_OK)
            self.configure(border_color=cores.BORDA_DESTAQUE)
            self._entry_texto.configure(border_color=cores.BORDA_SUTIL)
        
        # Atualiza o mapeamento mesmo que vazio para que a validação global detecte
        self._callback(self._variavel, f"FIXED:{texto}")

    @property
    def valor_mapeado(self) -> Optional[str]:
        if self._modo_fixo:
            t = self._var_texto.get().strip()
            return f"FIXED:{t}" if t else None
        else:
            v = self._var_coluna.get()
            return v if v != "(selecione uma coluna)" else None

    def atualizar_colunas(self, colunas: list[str]) -> None:
        self._colunas = colunas
        opcoes = ["(selecione uma coluna)"] + colunas
        self._dropdown.configure(values=opcoes)
        if not self._modo_fixo:
            self._var_coluna.set(opcoes[0])
            self._indicador.configure(text_color=self._COR_AVISO)
            self.configure(border_color=cores.BORDA_SUTIL)


# ---------------------------------------------------------------------------
# LogArea — Área de log premium
# ---------------------------------------------------------------------------


class LogArea(ctk.CTkScrollableFrame):
    """
    Console de log com visual de terminal moderno.
    """

    _ESTILOS = {
        "sucesso":  ("●", cores.SUCESSO),
        "erro":     ("●", cores.ERRO),
        "aviso":    ("●", cores.AVISO),
        "info":     ("●", cores.INFO),
        "normal":   ("○", cores.TEXTO_SECUNDARIO),
    }

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=cores.FUNDO_INPUT,
            scrollbar_button_color=cores.PRIMARIA,
            scrollbar_button_hover_color=cores.PRIMARIA_HOVER,
            corner_radius=12,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
            **kwargs,
        )
        self._labels: list[ctk.CTkLabel] = []

    def append(self, mensagem: str, nivel: str = "normal") -> None:
        prefixo, cor = self._ESTILOS.get(nivel, self._ESTILOS["normal"])

        frame_msg = ctk.CTkFrame(self, fg_color="transparent")
        frame_msg.pack(fill="x", padx=12, pady=2)

        ctk.CTkLabel(
            frame_msg,
            text=prefixo,
            font=fonte_ctk(12),
            text_color=cor,
            width=20,
        ).pack(side="left")

        ctk.CTkLabel(
            frame_msg,
            text=mensagem,
            font=fonte_mono(fontes.TAMANHO_LOG),
            text_color=cores.TEXTO_PRINCIPAL if nivel != "normal" else cores.TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=700,
        ).pack(side="left", padx=8)

        self._labels.append(frame_msg)
        self._parent_canvas.yview_moveto(1.0)

    def limpar(self) -> None:
        for widget in self._labels:
            widget.destroy()
        self._labels.clear()


# ---------------------------------------------------------------------------
# StatusBar — Barra de status minimalista
# ---------------------------------------------------------------------------


class StatusBar(ctk.CTkFrame):
    def __init__(self, master, ao_clicar_console: Callable = None, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=cores.FUNDO_PRINCIPAL,
            height=36,
            corner_radius=0,
            **kwargs,
        )
        self.pack_propagate(False)

        # Divisor superior
        ctk.CTkFrame(self, fg_color=cores.DIVISOR, height=1).pack(fill="x", side="top")

        self._var_status = tk.StringVar(value="")
        self._lbl = ctk.CTkLabel(
            self,
            textvariable=self._var_status,
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
            text_color=cores.TEXTO_SECUNDARIO,
        )
        self._lbl.pack(side="left", padx=20)

        # Botão sutil de Terminal (o "quadradinho")
        self._btn_terminal = ctk.CTkButton(
            self,
            text="CONSOLE",
            width=60,
            height=20,
            font=fonte_ctk(9, "bold"),
            fg_color=cores.FUNDO_PAINEL,
            text_color=cores.TEXTO_SECUNDARIO,
            hover_color=cores.PRIMARIA,
            corner_radius=4,
            command=ao_clicar_console,
        )
        self._btn_terminal.pack(side="right", padx=20)

    def definir(self, mensagem: str, cor: str = None) -> None:
        self._var_status.set(mensagem.upper())
        self._lbl.configure(text_color=cor or cores.TEXTO_SECUNDARIO)


# ---------------------------------------------------------------------------
# SectionHeader — Cabeçalho elegante
# ---------------------------------------------------------------------------


class SectionHeader(ctk.CTkFrame):
    def __init__(self, master, titulo: str, icone: str = "→", acao_callback: Callable = None, acao_icone: str = None, tooltip: str = None) -> None:
        super().__init__(master, fg_color="transparent")

        self.grid_columnconfigure(1, weight=1)

        # Ícone sutil
        ctk.CTkLabel(
            self,
            text=icone,
            font=fonte_ctk(fontes.TAMANHO_SUBTITULO, "bold"),
            text_color=cores.PRIMARIA,
            width=24,
        ).grid(row=0, column=0, sticky="w")

        # Título
        ctk.CTkLabel(
            self,
            text=titulo.upper(),
            font=fonte_ctk(fontes.TAMANHO_SECAO, "bold"),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=8)

        # Botão de Ação Premium (ex: Auto-link)
        if acao_callback:
            # Glifo \uE72C é o ícone de Sync/Refresh no Segoe MDL2 Assets (Win 10/11)
            # Se não for windows, o fallback é o caractere padrão
            font_icon = "Segoe MDL2 Assets" if "win" in sys.platform else fontes.FAMILIA
            
            self._btn_acao = ctk.CTkFrame(self, fg_color="transparent")
            self._btn_acao.grid(row=0, column=2, sticky="e", pady=(0, 4))

            self._inner_btn = ctk.CTkButton(
                self._btn_acao,
                text=" \uE72C  AUTO-LINK ",
                width=110,
                height=28,
                font=ctk.CTkFont(family=font_icon, size=11, weight="bold") if "win" in sys.platform else fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
                fg_color=cores.FUNDO_INPUT,
                text_color=cores.PRIMARIA, # Texto na cor de destaque
                hover_color=cores.FUNDO_CARD,
                border_width=1,
                border_color=cores.BORDA_SUTIL,
                corner_radius=6,
                command=acao_callback,
            )
            self._inner_btn.pack()
            
            if tooltip:
                # Dica visual aprimorada buscando a janela principal
                def obter_main_window(widget):
                    curr = widget
                    while curr:
                        if hasattr(curr, "_status_bar"):
                            return curr
                        curr = curr.master
                    return None

                def ao_entrar(e):
                    self._inner_btn.configure(fg_color=cores.PRIMARIA, text_color=cores.TEXTO_PRINCIPAL)
                    main = obter_main_window(self)
                    if main:
                        main._status_bar.definir(tooltip, cores.INFO)

                def ao_sair(e):
                    self._inner_btn.configure(fg_color=cores.FUNDO_INPUT, text_color=cores.PRIMARIA)
                    main = obter_main_window(self)
                    if main:
                        main._status_bar.definir("")

                self._inner_btn.bind("<Enter>", ao_entrar)
                self._inner_btn.bind("<Leave>", ao_sair)

        # Linha decorativa (Stripe style)
        ctk.CTkFrame(
            self,
            fg_color=cores.DIVISOR,
            height=2,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 16))


# ---------------------------------------------------------------------------
# PreviewPlanilha — Tabela moderna
# ---------------------------------------------------------------------------


class PreviewPlanilha(ctk.CTkScrollableFrame):
    _MAX_CHARS_CELULA = 30

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=cores.FUNDO_INPUT,
            scrollbar_button_color=cores.PRIMARIA,
            corner_radius=12,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
            **kwargs,
        )
        self._widgets: list[ctk.CTkLabel] = []

    def renderizar(self, df: pd.DataFrame) -> None:
        self._limpar()
        preview = df.head(8)

        # Cabeçalho com fundo sólido
        for col_idx, nome_col in enumerate(preview.columns):
            lbl = ctk.CTkLabel(
                self,
                text=str(nome_col).upper(),
                font=fonte_ctk(fontes.TAMANHO_PEQUENO, "bold"),
                text_color=cores.TEXTO_SECUNDARIO,
                anchor="center",
                fg_color=cores.FUNDO_PAINEL,
                corner_radius=6,
                height=32,
            )
            lbl.grid(row=0, column=col_idx, padx=4, pady=4, sticky="ew")
            self._widgets.append(lbl)

        # Dados
        for row_idx, (_, row) in enumerate(preview.iterrows(), start=1):
            for col_idx, valor in enumerate(row):
                lbl = ctk.CTkLabel(
                    self,
                    text=str(valor)[:self._MAX_CHARS_CELULA],
                    font=fonte_ctk(fontes.TAMANHO_PEQUENO),
                    text_color=cores.TEXTO_PRINCIPAL,
                    anchor="w",
                    fg_color="transparent",
                    height=28,
                )
                lbl.grid(row=row_idx, column=col_idx, padx=12, pady=1, sticky="ew")
                self._widgets.append(lbl)

    def _limpar(self) -> None:
        for widget in self._widgets:
            widget.destroy()
        self._widgets.clear()
