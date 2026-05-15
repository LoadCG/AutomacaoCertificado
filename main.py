"""
Entry point do Gerador de Certificados.

Inicializa o tema, gera o ícone se ausente, e abre a janela principal.
Captura exceções não tratadas via sys.excepthook para logar antes de crashar.
"""

import sys
import traceback
from pathlib import Path

from app.ui.styles import aplicar_tema
from app.utils.logger import obter_logger

log = obter_logger(__name__)

ASSETS_DIR = Path(__file__).parent / "assets"


def _excepthook_global(tipo, valor, tb) -> None:
    """Captura exceções não tratadas, loga e exibe mensagem ao usuário."""
    mensagem = "".join(traceback.format_exception(tipo, valor, tb))
    log.critical("Exceção não tratada:\n%s", mensagem)

    try:
        import tkinter.messagebox as mb
        mb.showerror(
            "Erro Inesperado",
            f"Ocorreu um erro inesperado:\n\n{valor}\n\n"
            "Detalhes foram registrados no arquivo de log.\n"
            "Caminho: ~/.gerador_certificados/app.log",
        )
    except Exception:
        print(mensagem, file=sys.stderr)


def _garantir_icone() -> None:
    """Gera o ícone da aplicação se ele não existir."""
    icone = ASSETS_DIR / "icon.ico"
    if not icone.is_file():
        try:
            from scripts.gerar_icone import gerar_icone
            gerar_icone(icone)
        except Exception as e:
            log.warning("Não foi possível gerar o ícone: %s", e)


def main() -> None:
    """Inicializa e executa a janela principal da aplicação."""
    sys.excepthook = _excepthook_global

    log.info("Iniciando Gerador de Certificados")

    aplicar_tema()
    _garantir_icone()

    from app.ui.main_window import MainWindow

    janela = MainWindow()
    janela.mainloop()

    log.info("Aplicação encerrada normalmente.")


if __name__ == "__main__":
    main()
