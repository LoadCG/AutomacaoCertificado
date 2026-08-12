"""
Carregamento de fontes privadas (Montserrat) sem exigir instalação no sistema.

No Windows, usa AddFontResourceExW com FR_PRIVATE para registrar os .ttf
apenas para o processo atual — a fonte fica disponível para o Tkinter/GDI
sem alterar o sistema do usuário e sem precisar de admin.

Uso:
    from app.utils.fonts import carregar_fontes_privadas
    carregar_fontes_privadas()  # chamar antes de criar qualquer widget Tk
"""

import sys
from pathlib import Path

from app.utils.logger import obter_logger

log = obter_logger(__name__)

ASSETS_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"

_FR_PRIVATE = 0x10


def carregar_fontes_privadas(pasta: Path = ASSETS_FONTS_DIR) -> None:
    """
    Registra todos os .ttf da pasta informada como fontes privadas do processo.

    Silenciosamente ignora se não estiver no Windows ou se a pasta não existir —
    o CustomTkinter cai de volta para a fonte padrão do sistema nesse caso.
    """
    if sys.platform != "win32":
        return
    if not pasta.is_dir():
        log.warning("Pasta de fontes não encontrada: %s", pasta)
        return

    import ctypes

    gdi32 = ctypes.windll.gdi32
    for arquivo in sorted(pasta.glob("*.ttf")):
        resultado = gdi32.AddFontResourceExW(str(arquivo), _FR_PRIVATE, 0)
        if resultado == 0:
            log.warning("Falha ao carregar fonte privada: %s", arquivo.name)
        else:
            log.debug("Fonte privada carregada: %s", arquivo.name)
