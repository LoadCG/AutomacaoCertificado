# build.spec — PyInstaller 6.x
# Executar: pyinstaller build.spec --clean
# Pré-requisitos: Python 3.11, pip install -r requirements-dev.txt

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Coleta automática dos assets do CustomTkinter (temas JSON e fontes)
ctk_datas = collect_data_files("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        *ctk_datas,                    # Temas e fontes do CustomTkinter
        ("assets", "assets"),          # Ícone e recursos visuais
    ],
    hiddenimports=[
        # pandas — alguns submodules não são detectados automaticamente
        "pandas",
        "pandas.core.arrays.masked",
        "pandas.core.arrays.integer",
        "pandas.io.formats.style",
        # Engines de leitura de planilhas
        "openpyxl",
        "openpyxl.styles.stylesheet",
        "xlrd",
        "odf",
        "odf.opendocument",
        "odf.table",
        "odf.text",
        "odf.namespaces",
        "defusedxml",
        "defusedxml.ElementTree",
        "defusedxml.minidom",
        # python-pptx
        "pptx",
        "pptx.util",
        "pptx.oxml",
        "pptx.oxml.ns",
        "pptx.enum.dml",
        "pptx.dml.color",
        # COM interop para exportação PDF (apenas Windows)
        "win32com",
        "win32com.client",
        "pythoncom",
        "pywintypes",
        # Pillow para geração do ícone
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        # typing_extensions para TypedDict
        "typing_extensions",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir bibliotecas científicas pesadas não utilizadas
        "matplotlib",
        "scipy",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Gerador_Certificados",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,            # Compressão UPX reduz ~30% do tamanho final
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # Sem janela de console (modo windowed)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)
