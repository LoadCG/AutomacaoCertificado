"""
Auditoria automatizada de contraste WCAG para a paleta de cores da UI.

Percorre os pares texto/fundo realmente usados juntos em app/ui/*.py
(levantados manualmente a partir do código) e falha se o contraste ficar
abaixo do mínimo AA — evita reintroduzir silenciosamente um bug como o do
botão "GERAR CERTIFICADOS" com texto ilegível quando desabilitado.

Uso:
    pytest tests/test_contraste.py -v
"""

import pytest

from app.ui.styles import Cores

cores = Cores()

_MODOS = {"claro": 0, "escuro": 1}

# Mínimo AA do WCAG 2.1: 4.5:1 para texto normal, 3:1 para texto grande
# (>= 18pt ou >= 14pt bold) e para elementos decorativos/ícones.
_MIN_TEXTO_NORMAL = 4.5
_MIN_TEXTO_GRANDE = 3.0

# (nome, cor_texto, cor_fundo, mínimo, descrição de onde é usado)
_PARES: list[tuple[str, tuple, tuple, float, str]] = [
    ("texto_principal/fundo_principal", cores.TEXTO_PRINCIPAL, cores.FUNDO_PRINCIPAL, _MIN_TEXTO_NORMAL, "labels no painel principal"),
    ("texto_principal/fundo_painel", cores.TEXTO_PRINCIPAL, cores.FUNDO_PAINEL, _MIN_TEXTO_NORMAL, "cards e painéis"),
    ("texto_principal/fundo_card", cores.TEXTO_PRINCIPAL, cores.FUNDO_CARD, _MIN_TEXTO_NORMAL, "botão Gerar desabilitado, checkboxes"),
    ("texto_principal/fundo_input", cores.TEXTO_PRINCIPAL, cores.FUNDO_INPUT, _MIN_TEXTO_NORMAL, "entries preenchidas, log"),
    ("texto_secundario/fundo_principal", cores.TEXTO_SECUNDARIO, cores.FUNDO_PRINCIPAL, _MIN_TEXTO_NORMAL, "labels secundários"),
    ("texto_secundario/fundo_painel", cores.TEXTO_SECUNDARIO, cores.FUNDO_PAINEL, _MIN_TEXTO_NORMAL, "rótulos em cards"),
    ("texto_secundario/fundo_card", cores.TEXTO_SECUNDARIO, cores.FUNDO_CARD, _MIN_TEXTO_NORMAL, "tabela zebra"),
    ("texto_secundario/fundo_input", cores.TEXTO_SECUNDARIO, cores.FUNDO_INPUT, _MIN_TEXTO_NORMAL, "placeholders, log normal"),
    ("texto_desabilitado/fundo_principal", cores.TEXTO_DESABILITADO, cores.FUNDO_PRINCIPAL, _MIN_TEXTO_NORMAL, "dicas desabilitadas"),
    ("texto_desabilitado/fundo_card", cores.TEXTO_DESABILITADO, cores.FUNDO_CARD, _MIN_TEXTO_NORMAL, "botão Gerar desabilitado"),
    ("texto_desabilitado/fundo_input", cores.TEXTO_DESABILITADO, cores.FUNDO_INPUT, _MIN_TEXTO_NORMAL, "placeholder de mapeamento vazio"),
    ("texto_sobre_primaria/primaria", cores.TEXTO_SOBRE_PRIMARIA, cores.PRIMARIA, _MIN_TEXTO_NORMAL, "botão Gerar habilitado, hover do AUTO-LINK"),
    ("primaria/fundo_painel", cores.PRIMARIA, cores.FUNDO_PAINEL, _MIN_TEXTO_GRANDE, "ícones e links em destaque"),
    ("primaria/fundo_input", cores.PRIMARIA, cores.FUNDO_INPUT, _MIN_TEXTO_GRANDE, "preview de nome de arquivo"),
    ("primaria/fundo_principal", cores.PRIMARIA, cores.FUNDO_PRINCIPAL, _MIN_TEXTO_GRANDE, "botão de config ativo"),
    ("sucesso/fundo_principal", cores.SUCESSO, cores.FUNDO_PRINCIPAL, _MIN_TEXTO_GRANDE, "status 'Pronto para gerar'"),
    ("sucesso/fundo_input", cores.SUCESSO, cores.FUNDO_INPUT, _MIN_TEXTO_GRANDE, "log de sucesso, indicador ✓"),
    ("erro/fundo_input", cores.ERRO, cores.FUNDO_INPUT, _MIN_TEXTO_GRANDE, "log de erro, indicador de mapeamento vazio"),
    ("aviso/fundo_principal", cores.AVISO, cores.FUNDO_PRINCIPAL, _MIN_TEXTO_GRANDE, "validação pendente"),
    ("info/fundo_principal", cores.INFO, cores.FUNDO_PRINCIPAL, _MIN_TEXTO_GRANDE, "status 'Gerando...'"),
]


def _luminancia_relativa(hex_cor: str) -> float:
    """Calcula a luminância relativa de uma cor hex conforme WCAG 2.1."""
    hex_cor = hex_cor.lstrip("#")
    r, g, b = (int(hex_cor[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def _linearizar(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _linearizar(r), _linearizar(g), _linearizar(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _razao_contraste(cor_a: str, cor_b: str) -> float:
    """Razão de contraste WCAG entre duas cores hex (1:1 a 21:1)."""
    lum_a, lum_b = _luminancia_relativa(cor_a), _luminancia_relativa(cor_b)
    mais_clara, mais_escura = max(lum_a, lum_b), min(lum_a, lum_b)
    return (mais_clara + 0.05) / (mais_escura + 0.05)


@pytest.mark.parametrize("nome,cor_texto,cor_fundo,minimo,onde", _PARES)
@pytest.mark.parametrize("modo", ["claro", "escuro"])
def test_par_atende_contraste_minimo(modo, nome, cor_texto, cor_fundo, minimo, onde):
    idx = _MODOS[modo]
    razao = _razao_contraste(cor_texto[idx], cor_fundo[idx])
    assert razao >= minimo, (
        f"[{modo}] '{nome}' ({onde}): contraste {razao:.2f}:1 abaixo do mínimo "
        f"{minimo}:1 — texto={cor_texto[idx]} fundo={cor_fundo[idx]}"
    )
