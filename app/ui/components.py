"""
Componentes reutilizáveis da interface do Gerador de Certificados.

Cada componente encapsula um conjunto de widgets CustomTkinter com
comportamento e estilo padronizados, seguindo o princípio de
responsabilidade única.

Uso:
    from app.ui.components import FilePickerCard, LogArea, VariavelMapRow, Tooltip, adicionar_tooltip
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
from app.ui.styles import cores, esp, fonte_ctk, fonte_mono, fonte_medium, fonte_titulo


# ---------------------------------------------------------------------------
# Tooltip — balão flutuante de ajuda contextual
# ---------------------------------------------------------------------------


class Tooltip:
    """
    Balão flutuante de ajuda contextual: aparece ao pairar o mouse sobre
    um widget (com um pequeno atraso, pra não piscar em passagens rápidas)
    e some ao sair ou clicar. Funciona com qualquer widget CTk/Tk.

    Uso:
        adicionar_tooltip(botao, "Explica o que esse botão faz.")
    """

    _ATRASO_MS = 450

    def __init__(self, widget, texto: str) -> None:
        self._widget = widget
        self._texto = texto
        self._janela: Optional[tk.Toplevel] = None
        self._id_atraso: Optional[str] = None
        widget.bind("<Enter>", self._ao_entrar, add="+")
        widget.bind("<Leave>", self._ao_sair, add="+")
        widget.bind("<Button-1>", self._ao_sair, add="+")

    def _ao_entrar(self, _event=None) -> None:
        self._cancelar_atraso()
        self._id_atraso = self._widget.after(self._ATRASO_MS, self._mostrar)

    def _ao_sair(self, _event=None) -> None:
        self._cancelar_atraso()
        self._esconder()

    def _cancelar_atraso(self) -> None:
        if self._id_atraso is not None:
            self._widget.after_cancel(self._id_atraso)
            self._id_atraso = None

    def _mostrar(self) -> None:
        if self._janela is not None or not self._widget.winfo_exists():
            return

        x = self._widget.winfo_rootx() + 12
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 6

        self._janela = tk.Toplevel(self._widget)
        self._janela.wm_overrideredirect(True)
        self._janela.wm_geometry(f"+{x}+{y}")
        try:
            self._janela.attributes("-topmost", True)
        except Exception:
            pass

        moldura = ctk.CTkFrame(
            self._janela,
            fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_PEQUENO,
            border_width=1,
            border_color=cores.BORDA_DESTAQUE,
        )
        moldura.pack()
        ctk.CTkLabel(
            moldura,
            text=self._texto,
            font=fonte_ctk(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_PRINCIPAL,
            justify="left",
            wraplength=260,
        ).pack(padx=10, pady=6)

    def _esconder(self) -> None:
        if self._janela is not None:
            self._janela.destroy()
            self._janela = None


def adicionar_tooltip(widget, texto: str) -> Tooltip:
    """Atalho para anexar um `Tooltip` a qualquer widget — descarta a instância com segurança (o bind mantém a referência viva)."""
    return Tooltip(widget, texto)


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
            font=fonte_medium(esp.PADDING_PEQUENO + 2),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
        )
        lbl.pack(fill="x", pady=(0, 4))

        self._frame_linha = ctk.CTkFrame(
            self,
            fg_color=cores.FUNDO_INPUT,
            corner_radius=esp.RAIO_MEDIO,
            border_width=2,
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
        self._entry.grid(row=0, column=0, sticky="ew", padx=(14, 4), pady=12)

        ctk.CTkButton(
            self._frame_linha,
            text="Alterar",
            width=90,
            height=32,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            fg_color=cores.FUNDO_CARD,
            hover_color=cores.BORDA_SUTIL,
            text_color=cores.TEXTO_PRINCIPAL,
            corner_radius=esp.RAIO_PEQUENO,
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
# FilePickerCard — Card de seleção de arquivo (fluxo minimalista)
# ---------------------------------------------------------------------------


class FilePickerCard(ctk.CTkFrame):
    """
    Card grande e convidativo para seleção de um único arquivo por vez.

    Todo o corpo do card é clicável e aceita arraste-e-solte. Mostra
    ícone, título, tipos aceitos e o caminho do arquivo carregado com
    indicador de sucesso — pensado para compor uma fileira de 2-3 cards.
    """

    def __init__(
        self,
        master,
        icone: str,
        titulo: str,
        subtitulo: str,
        tipos_arquivo: list[tuple[str, str]],
        callback_selecao: Callable[[Path], None],
        valor_inicial: Optional[str] = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_GRANDE,
            border_width=2,
            border_color=cores.BORDA_SUTIL,
        )

        self._callback = callback_selecao
        self._tipos_arquivo = tipos_arquivo
        self._caminho_atual: Optional[Path] = None

        self._extensoes = []
        for _, padrao in tipos_arquivo:
            ext = padrao.replace("*", "")
            if ext:
                self._extensoes.append(ext)

        self._construir(icone, titulo, subtitulo, valor_inicial)

    def _construir(
        self, icone: str, titulo: str, subtitulo: str, valor_inicial: Optional[str]
    ) -> None:
        # Layout horizontal e compacto: ícone à esquerda, texto à direita
        self.grid_columnconfigure(1, weight=1)

        self._lbl_icone = ctk.CTkLabel(
            self,
            text=icone,
            font=ctk.CTkFont(size=26),
            text_color=cores.PRIMARIA,
            width=44,
        )
        self._lbl_icone.grid(row=0, column=0, rowspan=2, padx=(esp.PADDING_MEDIO, esp.PADDING_PEQUENO), pady=esp.PADDING_MEDIO)

        # Título + tipos aceitos na mesma linha de cabeçalho
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.grid(row=0, column=1, sticky="ew", padx=(0, esp.PADDING_MEDIO), pady=(esp.PADDING_PEQUENO, 0))

        self._lbl_titulo = ctk.CTkLabel(
            cabecalho,
            text=titulo,
            font=fonte_titulo(fontes.TAMANHO_NORMAL),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        )
        self._lbl_titulo.pack(side="left")

        self._lbl_subtitulo = ctk.CTkLabel(
            cabecalho,
            text=f"  ·  {subtitulo}",
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
        )
        self._lbl_subtitulo.pack(side="left")

        # Caminho / status — muda para "✓ arquivo.pptx" quando carregado
        self._var_status = tk.StringVar(value="Arraste aqui ou clique para procurar")
        self._lbl_status = ctk.CTkLabel(
            self,
            textvariable=self._var_status,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self._lbl_status.grid(
            row=1, column=1, sticky="ew", padx=(0, esp.PADDING_MEDIO), pady=(2, esp.PADDING_PEQUENO)
        )

        # Clique em qualquer parte do card abre o diálogo de seleção
        for widget in (self, cabecalho, self._lbl_icone, self._lbl_titulo, self._lbl_subtitulo, self._lbl_status):
            widget.bind("<Button-1>", lambda e: self._abrir_dialogo())
            widget.configure(cursor="hand2")

        if valor_inicial:
            self.definir_caminho(Path(valor_inicial))

        # Drag & Drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._ao_soltar_arquivo)
        self.dnd_bind("<<DragEnter>>", self._ao_entrar_drag)
        self.dnd_bind("<<DragLeave>>", self._ao_sair_drag)

    def _ao_entrar_drag(self, event) -> None:
        self.configure(border_color=cores.PRIMARIA)

    def _ao_sair_drag(self, event) -> None:
        cor = cores.BORDA_DESTAQUE if self._caminho_atual else cores.BORDA_SUTIL
        self.configure(border_color=cor)

    def _ao_soltar_arquivo(self, event) -> None:
        self._ao_sair_drag(event)
        caminho_str = event.data

        if caminho_str.startswith("{") and caminho_str.endswith("}"):
            caminho_str = caminho_str[1:-1]
        elif caminho_str.startswith('"') and caminho_str.endswith('"'):
            caminho_str = caminho_str[1:-1]

        caminho = Path(caminho_str)

        if self._extensoes:
            extensoes_validas = [ext.lower() for ext in self._extensoes]
            if caminho.suffix.lower() not in extensoes_validas:
                return

        self.definir_caminho(caminho)
        if self._callback:
            self._callback(caminho)

    def _abrir_dialogo(self) -> None:
        caminho_str = filedialog.askopenfilename(filetypes=self._tipos_arquivo)
        if caminho_str:
            self.definir_caminho(Path(caminho_str))
            self._callback(self._caminho_atual)

    @property
    def caminho(self) -> Optional[Path]:
        return self._caminho_atual

    def definir_caminho(self, caminho: Path) -> None:
        self._caminho_atual = caminho
        self._var_status.set(f"✓  {caminho.name}")
        self._lbl_status.configure(text_color=cores.SUCESSO)
        self.configure(border_color=cores.BORDA_DESTAQUE)

    def definir_erro(self, mensagem: str) -> None:
        """
        Marca o card com um estado de erro visível — borda vermelha e
        mensagem curta no lugar do status, sem depender do usuário notar
        a status bar ou abrir o console de log.
        """
        nome = f"{self._caminho_atual.name} — " if self._caminho_atual else ""
        self._var_status.set(f"⚠ {nome}{mensagem}")
        self._lbl_status.configure(text_color=cores.ERRO)
        self.configure(border_color=cores.ERRO)

    def limpar_erro(self) -> None:
        """Restaura o visual normal (sucesso ou vazio) após corrigir o erro."""
        if self._caminho_atual:
            self.definir_caminho(self._caminho_atual)
        else:
            self._var_status.set("Arraste aqui ou clique para procurar")
            self._lbl_status.configure(text_color=cores.TEXTO_SECUNDARIO)
            self.configure(border_color=cores.BORDA_SUTIL)


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
        super().__init__(master, fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_MEDIO)

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
        adicionar_tooltip(
            self._indicador,
            "Verde: variável já vinculada.\nAmarelo: falta escolher uma coluna.\nVermelho: texto fixo está vazio.",
        )

        # Nome da variável em destaque
        ctk.CTkLabel(
            self,
            text=self._variavel,
            font=fonte_medium(fontes.TAMANHO_NORMAL),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=4, pady=12)

        # Seletor de modo (Design Segmentado Moderno)
        # Envolvido num frame porque CTkSegmentedButton não suporta .bind() diretamente
        # (levanta NotImplementedError) — o tooltip é anexado ao frame ao redor.
        self._seg_button_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self._seg_button_wrapper.grid(row=0, column=2, padx=12)

        self._seg_button = ctk.CTkSegmentedButton(
            self._seg_button_wrapper,
            values=["Planilha", "Texto"],
            command=self._alternar_modo,
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            height=28,
            width=100,
            fg_color=cores.FUNDO_PRINCIPAL,
            selected_color=cores.PRIMARIA,
            selected_hover_color=cores.PRIMARIA_HOVER,
            unselected_color=cores.FUNDO_INPUT,
            unselected_hover_color=cores.FUNDO_CARD,
        )
        self._seg_button.set("Planilha")
        self._seg_button.pack()
        adicionar_tooltip(
            self._seg_button_wrapper,
            "Planilha: usa o valor de uma coluna, diferente por participante.\n"
            "Texto: usa um valor fixo, igual em todos os certificados.",
        )

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
            corner_radius=esp.RAIO_PEQUENO,
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
            corner_radius=esp.RAIO_PEQUENO,
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
# MappingCard — Card com o mapeamento de variáveis (3º card do fluxo)
# ---------------------------------------------------------------------------


class MappingCard(ctk.CTkFrame):
    """
    Card que hospeda o mapeamento de variáveis ↔ colunas.

    Fica vazio (placeholder) até que template e planilha estejam
    carregados. `container` é onde o chamador deve empacotar as
    `VariavelMapRow`; `placeholder` é o label de estado vazio.
    """

    def __init__(self, master, acao_callback: Callable, tooltip: str = "") -> None:
        super().__init__(
            master,
            fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_GRANDE,
            border_width=2,
            border_color=cores.BORDA_SUTIL,
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="🔗", font=ctk.CTkFont(size=22), text_color=cores.PRIMARIA
        ).grid(row=0, column=0)

        ctk.CTkLabel(
            header,
            text="Mapeamento de Variáveis",
            font=fonte_titulo(fontes.TAMANHO_SUBTITULO),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=10)

        self._btn_autolink = ctk.CTkButton(
            header,
            text="🔄",
            width=32,
            height=32,
            font=fonte_medium(15),
            fg_color=cores.FUNDO_INPUT,
            text_color=cores.PRIMARIA,
            hover_color=cores.FUNDO_CARD,
            corner_radius=esp.RAIO_PEQUENO - 4,
            command=acao_callback,
        )
        self._btn_autolink.grid(row=0, column=2)

        self.container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=cores.PRIMARIA,
            height=170,
        )
        self.container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 16))

        self.placeholder = ctk.CTkLabel(
            self.container,
            text="Carregue o template e a planilha\npara vincular as variáveis",
            font=fonte_ctk(fontes.TAMANHO_PEQUENO, "italic"),
            text_color=cores.TEXTO_DESABILITADO,
            justify="center",
        )
        self.placeholder.pack(pady=40)


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
            corner_radius=esp.RAIO_MEDIO,
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
            font=fonte_medium(fontes.TAMANHO_PEQUENO),
            text_color=cores.TEXTO_SECUNDARIO,
        )
        self._lbl.pack(side="left", padx=20)

        # Botão sutil de Terminal (o "quadradinho")
        self._btn_terminal = ctk.CTkButton(
            self,
            text="CONSOLE",
            width=60,
            height=20,
            font=fonte_medium(9),
            fg_color=cores.FUNDO_PAINEL,
            text_color=cores.TEXTO_SECUNDARIO,
            hover_color=cores.PRIMARIA,
            corner_radius=esp.RAIO_PEQUENO - 4,
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
            font=fonte_titulo(fontes.TAMANHO_SUBTITULO),
            text_color=cores.PRIMARIA,
            width=24,
        ).grid(row=0, column=0, sticky="w")

        # Título — peso ExtraBold do design system
        ctk.CTkLabel(
            self,
            text=titulo.upper(),
            font=fonte_titulo(fontes.TAMANHO_SECAO),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=8)

        # Botão de Ação Premium (ex: Auto-link)
        if acao_callback:
            # Glifo \uE72C é o ícone de Sync/Refresh no Segoe MDL2 Assets (Win 10/11)
            # Se não for windows, o fallback é o caractere padrão
            font_icon = "Segoe MDL2 Assets" if "win" in sys.platform else fontes.FAMILIA_MEDIUM

            self._btn_acao = ctk.CTkFrame(self, fg_color="transparent")
            self._btn_acao.grid(row=0, column=2, sticky="e", pady=(0, 4))

            self._inner_btn = ctk.CTkButton(
                self._btn_acao,
                text=" \uE72C  AUTO-LINK ",
                width=110,
                height=28,
                font=ctk.CTkFont(family=font_icon, size=11, weight="bold") if "win" in sys.platform else fonte_medium(fontes.TAMANHO_PEQUENO),
                fg_color=cores.FUNDO_INPUT,
                text_color=cores.PRIMARIA, # Texto na cor de destaque
                hover_color=cores.FUNDO_CARD,
                border_width=1,
                border_color=cores.BORDA_SUTIL,
                corner_radius=esp.RAIO_PEQUENO - 4,
                command=acao_callback,
            )
            self._inner_btn.pack()
            
            if tooltip:
                def ao_entrar(e):
                    self._inner_btn.configure(fg_color=cores.PRIMARIA, text_color=cores.TEXTO_SOBRE_PRIMARIA)

                def ao_sair(e):
                    self._inner_btn.configure(fg_color=cores.FUNDO_INPUT, text_color=cores.PRIMARIA)

                self._inner_btn.bind("<Enter>", ao_entrar, add="+")
                self._inner_btn.bind("<Leave>", ao_sair, add="+")
                adicionar_tooltip(self._inner_btn, tooltip)

        # Linha decorativa (Stripe style)
        ctk.CTkFrame(
            self,
            fg_color=cores.DIVISOR,
            height=2,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 16))


# ---------------------------------------------------------------------------
# TutorialCard — Passo do tutorial de ajuda, com mini-preview do elemento
# ---------------------------------------------------------------------------


class TutorialCard(ctk.CTkFrame):
    """
    Um "passo" do tutorial: ícone + título + texto didático + uma
    reprodução em miniatura (não-clicável) do elemento real da interface
    a que o texto se refere — em vez de um screenshot estático, é o
    próprio widget do CustomTkinter renderizado, então ele já nasce
    coerente com o tema claro/escuro atual.
    """

    def __init__(
        self,
        master,
        icone: str,
        titulo: str,
        descricao: str,
        construir_preview: Optional[Callable[["ctk.CTkFrame"], None]] = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_GRANDE,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
        )
        self.grid_columnconfigure(0, weight=1)

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew", padx=esp.PADDING_MEDIO, pady=(esp.PADDING_MEDIO, esp.PADDING_PEQUENO))

        ctk.CTkLabel(
            cabecalho, text=icone, font=ctk.CTkFont(size=20), text_color=cores.PRIMARIA, width=28,
        ).pack(side="left")

        ctk.CTkLabel(
            cabecalho,
            text=titulo,
            font=fonte_titulo(fontes.TAMANHO_NORMAL),
            text_color=cores.TEXTO_PRINCIPAL,
            anchor="w",
        ).pack(side="left", padx=(esp.PADDING_PEQUENO, 0))

        ctk.CTkLabel(
            self,
            text=descricao,
            font=fonte_ctk(fontes.TAMANHO_NORMAL),
            text_color=cores.TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=560,
        ).grid(row=1, column=0, sticky="ew", padx=esp.PADDING_MEDIO, pady=(0, esp.PADDING_PEQUENO))

        if construir_preview is not None:
            moldura = ctk.CTkFrame(
                self,
                fg_color=cores.FUNDO_INPUT,
                corner_radius=esp.RAIO_MEDIO,
                border_width=1,
                border_color=cores.BORDA_SUTIL,
            )
            moldura.grid(row=2, column=0, sticky="ew", padx=esp.PADDING_MEDIO, pady=(0, esp.PADDING_MEDIO))
            preview = ctk.CTkFrame(moldura, fg_color="transparent")
            preview.pack(padx=esp.PADDING_MEDIO, pady=esp.PADDING_PEQUENO, anchor="w")
            construir_preview(preview)
        else:
            # Espaço final quando não há preview, pro card não ficar apertado
            ctk.CTkFrame(self, fg_color="transparent", height=4).grid(row=2, column=0)


# ---------------------------------------------------------------------------
# PreviewPlanilha — Tabela moderna
# ---------------------------------------------------------------------------


class PreviewPlanilha(ctk.CTkScrollableFrame):
    """
    Tabela de preview com checkbox de ativação por linha e cabeçalhos
    clicáveis para ordenação.

    Puramente de exibição: quem decide o que é "ativo", a ordenação e a
    busca é o chamador (MainWindow) — este componente só desenha o que
    recebe em `renderizar()` e notifica cliques via callbacks.
    """

    _MAX_CHARS_CELULA = 30
    _MAX_LINHAS_EXIBIDAS = 300

    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=cores.FUNDO_INPUT,
            scrollbar_button_color=cores.PRIMARIA,
            corner_radius=esp.RAIO_MEDIO,
            border_width=1,
            border_color=cores.BORDA_SUTIL,
            **kwargs,
        )
        self._widgets: list[ctk.CTkBaseClass] = []

    def renderizar(
        self,
        df: pd.DataFrame,
        indices_excluidos: set,
        callback_alternar: Callable[[object, bool], None],
        callback_ordenar: Optional[Callable[[str], None]] = None,
        coluna_ordenada: Optional[str] = None,
        ordem_crescente: bool = True,
    ) -> None:
        self._limpar()
        preview = df.head(self._MAX_LINHAS_EXIBIDAS)

        self.grid_columnconfigure(0, weight=0)
        for col_idx in range(1, len(preview.columns) + 1):
            self.grid_columnconfigure(col_idx, weight=1)

        # Cabeçalho: checkbox "cabeçalho" vazio + colunas clicáveis para ordenar
        lbl_check_header = ctk.CTkLabel(
            self, text="", fg_color=cores.FUNDO_PAINEL,
            corner_radius=esp.RAIO_PEQUENO - 4, height=38, width=40,
        )
        lbl_check_header.grid(row=0, column=0, padx=(4, 4), pady=(4, 8), sticky="ew")
        adicionar_tooltip(lbl_check_header, "Desmarque a caixinha da linha para excluí-la da geração de certificados.")
        self._widgets.append(lbl_check_header)

        for col_idx, nome_col in enumerate(preview.columns, start=1):
            seta = ""
            if callback_ordenar is not None and nome_col == coluna_ordenada:
                seta = "  ▲" if ordem_crescente else "  ▼"
            texto = str(nome_col).upper() + seta

            if callback_ordenar is not None:
                header = ctk.CTkButton(
                    self,
                    text=texto,
                    font=fonte_titulo(fontes.TAMANHO_PEQUENO),
                    text_color=cores.TEXTO_SECUNDARIO,
                    fg_color=cores.FUNDO_PAINEL,
                    hover_color=cores.FUNDO_CARD,
                    corner_radius=esp.RAIO_PEQUENO - 4,
                    height=38,
                    anchor="w",
                    command=lambda c=nome_col: callback_ordenar(c),
                )
            else:
                header = ctk.CTkLabel(
                    self, text=texto, font=fonte_titulo(fontes.TAMANHO_PEQUENO),
                    text_color=cores.TEXTO_SECUNDARIO, anchor="w",
                    fg_color=cores.FUNDO_PAINEL, corner_radius=esp.RAIO_PEQUENO - 4, height=38,
                )
            header.grid(row=0, column=col_idx, padx=(4, 4), pady=(4, 8), sticky="ew", ipadx=8)
            if callback_ordenar is not None:
                adicionar_tooltip(header, "Clique para ordenar por esta coluna.")
            self._widgets.append(header)

        # Dados com zebra striping — linhas desativadas ficam esmaecidas
        for row_idx, (indice_original, row) in enumerate(preview.iterrows(), start=1):
            ativo = indice_original not in indices_excluidos
            cor_linha = cores.FUNDO_INPUT if row_idx % 2 else cores.FUNDO_CARD
            cor_texto = cores.TEXTO_PRINCIPAL if ativo else cores.TEXTO_DESABILITADO

            var_ativo = ctk.BooleanVar(value=ativo)
            chk = ctk.CTkCheckBox(
                self,
                text="",
                variable=var_ativo,
                width=24,
                checkbox_width=20,
                checkbox_height=20,
                fg_color=cores.PRIMARIA,
                hover_color=cores.PRIMARIA_HOVER,
                border_color=cores.BORDA_SUTIL,
                corner_radius=esp.RAIO_PEQUENO - 6,
                command=lambda idx=indice_original, v=var_ativo: callback_alternar(idx, v.get()),
            )
            chk.grid(row=row_idx, column=0, padx=(10, 4), pady=1, sticky="w")
            self._widgets.append(chk)

            for col_idx, valor in enumerate(row, start=1):
                lbl = ctk.CTkLabel(
                    self,
                    text=str(valor)[:self._MAX_CHARS_CELULA],
                    font=fonte_ctk(fontes.TAMANHO_NORMAL, "italic" if not ativo else "normal"),
                    text_color=cor_texto,
                    anchor="w",
                    fg_color=cor_linha,
                    corner_radius=esp.RAIO_PEQUENO - 6,
                    height=34,
                )
                lbl.grid(row=row_idx, column=col_idx, padx=(4, 4), pady=1, sticky="ew", ipadx=8)
                self._widgets.append(lbl)

    def _limpar(self) -> None:
        for widget in self._widgets:
            widget.destroy()
        self._widgets.clear()
