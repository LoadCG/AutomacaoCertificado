"""
Constantes visuais, tema e paleta de cores do Gerador de Certificados.

Centraliza todas as decisões de design em um único local para facilitar
manutenção e consistência visual entre todos os componentes.

Uso:
    from app.ui.styles import Cores, Fontes, Espacamentos, aplicar_tema
    aplicar_tema()
"""

from dataclasses import dataclass
from typing import Tuple

import customtkinter as ctk


# ---------------------------------------------------------------------------
# Paleta de cores
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cores:
    """Paleta de cores premium adaptativa (Light / Dark)."""

    # Cor primária — Azul 'Electric' vibrante
    PRIMARIA: Tuple[str, str] = ("#2563EB", "#3B82F6")
    PRIMARIA_HOVER: Tuple[str, str] = ("#1D4ED8", "#60A5FA")
    PRIMARIA_ESCURA: Tuple[str, str] = ("#1E40AF", "#1D4ED8")

    # Fundos
    FUNDO_PRINCIPAL: Tuple[str, str] = ("#F1F5F9", "#0F172A")  # Slate 100 / Deep Slate
    FUNDO_PAINEL: Tuple[str, str] = ("#FFFFFF", "#1E293B")     # White / Slate 800
    FUNDO_CARD: Tuple[str, str] = ("#F8FAFC", "#334155")       # Slate 50 / Slate 700
    FUNDO_INPUT: Tuple[str, str] = ("#FFFFFF", "#0F172A")      # White / Slate 900

    # Bordas e Divisores
    BORDA_SUTIL: Tuple[str, str] = ("#E2E8F0", "#334155")      # Slate 200 / Slate 700
    BORDA_DESTAQUE: Tuple[str, str] = ("#3B82F6", "#3B82F6")
    DIVISOR: Tuple[str, str] = ("#E2E8F0", "#1E293B")

    # Texto
    TEXTO_PRINCIPAL: Tuple[str, str] = ("#1E293B", "#F8FAFC")   # Slate 800 / Slate 50
    TEXTO_SECUNDARIO: Tuple[str, str] = ("#64748B", "#94A3B8")  # Slate 500 / Slate 400
    TEXTO_DESABILITADO: Tuple[str, str] = ("#94A3B8", "#475569") # Slate 400 / Slate 600
    TEXTO_LINK: Tuple[str, str] = ("#2563EB", "#60A5FA")

    # Status
    SUCESSO: Tuple[str, str] = ("#059669", "#10B981")
    ERRO: Tuple[str, str] = ("#DC2626", "#EF4444")
    AVISO: Tuple[str, str] = ("#D97706", "#F59E0B")
    INFO: Tuple[str, str] = ("#0284C7", "#0EA5E9")

    # Ações
    BOTAO_DESABILITADO: Tuple[str, str] = ("#E2E8F0", "#1E293B")
    BOTAO_DESABILITADO_TEXTO: Tuple[str, str] = ("#94A3B8", "#475569")

    # Gradients (Simulação via HEX para botões premium)
    GRADIENTE_INICIO: str = "#3B82F6"
    GRADIENTE_FIM: str = "#2563EB"


@dataclass(frozen=True)
class Fontes:
    """Configurações de fonte inspiradas em interfaces modernas."""

    # Inter é a fonte padrão de interfaces modernas (Stripe, Figma, Linear)
    FAMILIA: str = "Inter, Segoe UI, Roboto, sans-serif"
    FAMILIA_MONO: str = "JetBrains Mono, Fira Code, Consolas, monospace"

    TAMANHO_TITULO: int = 24
    TAMANHO_SUBTITULO: int = 16
    TAMANHO_SECAO: int = 13
    TAMANHO_NORMAL: int = 12
    TAMANHO_PEQUENO: int = 11
    TAMANHO_LOG: int = 11


@dataclass(frozen=True)
class Espacamentos:
    """Espaçamentos generosos para 'respiro' visual."""

    PADDING_GRANDE: int = 24
    PADDING_MEDIO: int = 16
    PADDING_PEQUENO: int = 8
    PADDING_MINIMO: int = 4

    LARGURA_PAINEL_ESQUERDO: int = 340
    LARGURA_PAINEL_CENTRAL: int = 520
    ALTURA_MINIMA_JANELA: int = 800
    LARGURA_MINIMA_JANELA: int = 1280


# ---------------------------------------------------------------------------
# Instâncias globais — importar e usar diretamente
# ---------------------------------------------------------------------------

cores = Cores()
fontes = Fontes()
esp = Espacamentos()


# ---------------------------------------------------------------------------
# Funções de configuração de tema
# ---------------------------------------------------------------------------


def aplicar_tema(modo: str = "dark") -> None:
    """
    Configura o tema global do CustomTkinter.
    """
    ctk.set_appearance_mode(modo)
    # Customizamos o tema padrão para alinhar com nossa paleta
    ctk.set_default_color_theme("blue")


def fonte_ctk(
    tamanho: int = 12,
    peso: str = "normal",
    familia: str = None,
) -> ctk.CTkFont:
    """
    Cria um objeto CTkFont com os parâmetros fornecidos.
    Trata 'italic' de forma segura para evitar erros do Tkinter.
    """
    slant = "italic" if peso == "italic" else "roman"
    weight = "normal" if peso == "italic" else peso

    return ctk.CTkFont(
        family=familia or fontes.FAMILIA,
        size=tamanho,
        weight=weight,
        slant=slant
    )


def fonte_mono(tamanho: int = 11) -> ctk.CTkFont:
    """
    Retorna uma fonte monoespaçada.
    """
    return ctk.CTkFont(family=fontes.FAMILIA_MONO, size=tamanho)
