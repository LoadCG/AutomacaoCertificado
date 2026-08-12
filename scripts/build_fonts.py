"""
Gera instâncias estáticas do Montserrat (variable font) para uso no CustomTkinter.

O Tkinter/GDI no Windows não seleciona eixos de fontes variáveis, então cada
peso precisa existir como uma família estática própria (ex: "Montserrat ExtraBold").

Uso (uma vez, offline após gerado — os .ttf resultantes ficam versionados em assets/fonts):
    python scripts/build_fonts.py
"""

import urllib.request
from pathlib import Path

from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.ttLib import TTFont

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "scripts" / ".cache"
FONTE_VARIAVEL = CACHE / "Montserrat-VF.ttf"
URL_FONTE_VARIAVEL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
)
SAIDA = RAIZ / "assets" / "fonts"


def _garantir_fonte_variavel() -> None:
    if FONTE_VARIAVEL.exists():
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"Baixando fonte variável de {URL_FONTE_VARIAVEL} ...")
    urllib.request.urlretrieve(URL_FONTE_VARIAVEL, FONTE_VARIAVEL)

# (sufixo de família, peso wght, usWeightClass)
INSTANCIAS = [
    ("", 400, 400),               # Montserrat (Regular)
    (" Medium", 500, 500),
    (" SemiBold", 600, 600),
    (" Bold", 700, 700),
    (" ExtraBold", 800, 800),
]


def _renomear_familia(font: TTFont, sufixo: str, peso_classe: int) -> None:
    nome_base = "Montserrat" + sufixo
    name_table = font["name"]
    for name_id in (1, 16):
        name_table.setName(nome_base, name_id, 3, 1, 0x409)
    for name_id in (2, 17):
        name_table.setName("Regular", name_id, 3, 1, 0x409)
    name_table.setName(nome_base, 4, 3, 1, 0x409)
    name_table.setName(nome_base.replace(" ", "-"), 6, 3, 1, 0x409)
    if "OS/2" in font:
        font["OS/2"].usWeightClass = peso_classe
    if "head" in font:
        font["head"].macStyle = 0


def main() -> None:
    _garantir_fonte_variavel()
    SAIDA.mkdir(parents=True, exist_ok=True)
    for sufixo, wght, peso_classe in INSTANCIAS:
        font = TTFont(str(FONTE_VARIAVEL))
        instantiateVariableFont(font, {"wght": wght}, inplace=True)
        _renomear_familia(font, sufixo, peso_classe)
        nome_arquivo = f"Montserrat{sufixo.replace(' ', '')}.ttf"
        destino = SAIDA / nome_arquivo
        font.save(str(destino))
        print(f"Gerado: {destino}")


if __name__ == "__main__":
    main()
