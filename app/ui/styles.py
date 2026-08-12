"""
Constantes visuais, tema e paleta de cores do Gerador de Certificados.

Centraliza todas as decisões de design em um único local para facilitar
manutenção e consistência visual entre todos os componentes.

Design system:
- Tipografia: Montserrat (ExtraBold em títulos/CTAs, pesos normais no resto).
- Formas: cantos arredondados em inputs, botões, modais e containers.
- Cores: off-white minimalista no modo claro; off-black com subtom marrom
  sofisticado no modo escuro.

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
    """Paleta de cores adaptativa (Light / Dark)."""

    # Cor primária — Âmbar quente, combina com o subtom marrom do modo escuro
    PRIMARIA: Tuple[str, str] = ("#B45309", "#E8A33D")
    PRIMARIA_HOVER: Tuple[str, str] = ("#92400E", "#F2B75C")
    PRIMARIA_ESCURA: Tuple[str, str] = ("#78350F", "#B45309")

    # Fundos — Off-white minimalista / Off-black com subtom marrom sofisticado
    FUNDO_PRINCIPAL: Tuple[str, str] = ("#FAF8F5", "#1A1512")
    FUNDO_PAINEL: Tuple[str, str] = ("#FFFFFF", "#231D18")
    FUNDO_CARD: Tuple[str, str] = ("#F3EFE9", "#2C241E")
    FUNDO_INPUT: Tuple[str, str] = ("#FFFFFF", "#171310")

    # Bordas e Divisores
    BORDA_SUTIL: Tuple[str, str] = ("#E7E1D8", "#3A2F27")
    BORDA_DESTAQUE: Tuple[str, str] = ("#B45309", "#E8A33D")
    DIVISOR: Tuple[str, str] = ("#EDE8E0", "#2C241E")

    # Texto
    TEXTO_PRINCIPAL: Tuple[str, str] = ("#1F1B16", "#F5EFE6")
    TEXTO_SECUNDARIO: Tuple[str, str] = ("#75695C", "#A99A8A")
    TEXTO_DESABILITADO: Tuple[str, str] = ("#726757", "#A2937F")
    TEXTO_LINK: Tuple[str, str] = ("#B45309", "#E8A33D")

    # Status — AVISO é distinta de PRIMARIA para não perder o significado semântico
    SUCESSO: Tuple[str, str] = ("#15803D", "#4ADE80")
    ERRO: Tuple[str, str] = ("#DC2626", "#F87171")
    AVISO: Tuple[str, str] = ("#C2410C", "#FBBF24")
    INFO: Tuple[str, str] = ("#0369A1", "#38BDF8")

    # Texto sobre a cor primária (CTA principal)
    TEXTO_SOBRE_PRIMARIA: Tuple[str, str] = ("#FFFFFF", "#1A1512")


@dataclass(frozen=True)
class Fontes:
    """
    Famílias Montserrat pré-instanciadas por peso (ver scripts/build_fonts.py).

    O Tkinter/GDI não seleciona eixos de fontes variáveis, então cada peso
    é uma família própria — use FAMILIA_* diretamente ao invés do parâmetro
    `peso` de fonte_ctk() quando precisar de Medium/SemiBold/ExtraBold.
    """

    FAMILIA: str = "Montserrat"
    FAMILIA_MEDIUM: str = "Montserrat Medium"
    FAMILIA_SEMIBOLD: str = "Montserrat SemiBold"
    FAMILIA_BOLD: str = "Montserrat Bold"
    FAMILIA_EXTRABOLD: str = "Montserrat ExtraBold"
    FAMILIA_MONO: str = "Consolas, JetBrains Mono, Fira Code, monospace"

    TAMANHO_CTA: int = 19
    TAMANHO_TITULO: int = 26
    TAMANHO_SUBTITULO: int = 19
    TAMANHO_SECAO: int = 15
    TAMANHO_NORMAL: int = 13
    TAMANHO_PEQUENO: int = 12
    TAMANHO_LOG: int = 12


@dataclass(frozen=True)
class Espacamentos:
    """Espaçamentos generosos para 'respiro' visual."""

    PADDING_GRANDE: int = 32
    PADDING_MEDIO: int = 20
    PADDING_PEQUENO: int = 10
    PADDING_MINIMO: int = 6

    ALTURA_MINIMA_JANELA: int = 800
    LARGURA_MINIMA_JANELA: int = 1280

    # Raio de canto padrão do design system — usar em inputs/botões/cards
    RAIO_PEQUENO: int = 10
    RAIO_MEDIO: int = 14
    RAIO_GRANDE: int = 18


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
    ctk.set_default_color_theme("blue")


def fonte_ctk(
    tamanho: int = 12,
    peso: str = "normal",
    familia: str = None,
) -> ctk.CTkFont:
    """
    Cria um objeto CTkFont com os parâmetros fornecidos.

    Para pesos Medium/SemiBold/ExtraBold, prefira passar `familia` com a
    respectiva constante `fontes.FAMILIA_*` — o Tkinter só distingue
    normal/bold nativamente, não os pesos intermediários.
    """
    slant = "italic" if peso == "italic" else "roman"
    weight = "normal" if peso == "italic" else peso

    return ctk.CTkFont(
        family=familia or fontes.FAMILIA,
        size=tamanho,
        weight=weight,
        slant=slant
    )


def fonte_titulo(tamanho: int = fontes.TAMANHO_TITULO) -> ctk.CTkFont:
    """Fonte ExtraBold para títulos, cabeçalhos e CTAs principais."""
    return ctk.CTkFont(family=fontes.FAMILIA_EXTRABOLD, size=tamanho, weight="normal")


def fonte_semibold(tamanho: int = fontes.TAMANHO_NORMAL) -> ctk.CTkFont:
    """Fonte SemiBold para subtítulos e destaques secundários."""
    return ctk.CTkFont(family=fontes.FAMILIA_SEMIBOLD, size=tamanho, weight="normal")


def fonte_medium(tamanho: int = fontes.TAMANHO_NORMAL) -> ctk.CTkFont:
    """Fonte Medium para texto de apoio com leve ênfase."""
    return ctk.CTkFont(family=fontes.FAMILIA_MEDIUM, size=tamanho, weight="normal")


def fonte_mono(tamanho: int = 11) -> ctk.CTkFont:
    """
    Retorna uma fonte monoespaçada.
    """
    return ctk.CTkFont(family=fontes.FAMILIA_MONO, size=tamanho)
