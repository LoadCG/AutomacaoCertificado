"""
Módulo de logging centralizado do Gerador de Certificados.

Fornece um logger singleton com dois handlers:
- Console (StreamHandler) para desenvolvimento
- Arquivo rotativo (~/.gerador_certificados/app.log) para produção

Uso:
    from app.utils.logger import obter_logger
    log = obter_logger(__name__)
    log.info("Operação iniciada")
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Diretório de dados do aplicativo no perfil do usuário
DIRETORIO_DADOS: Path = Path.home() / ".gerador_certificados"
ARQUIVO_LOG: Path = DIRETORIO_DADOS / "app.log"

# Tamanho máximo do arquivo de log antes de rotacionar (5 MB)
TAMANHO_MAX_BYTES: int = 5 * 1024 * 1024
BACKUP_COUNT: int = 3

# Formato de data e mensagem
FORMATO_LOG: str = "[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s"
FORMATO_DATA: str = "%Y-%m-%d %H:%M:%S"

# Nome do logger raiz da aplicação
NOME_LOGGER_RAIZ: str = "gerador_certificados"

_logger_configurado: bool = False


def _configurar_logger() -> None:
    """
    Configura o logger raiz da aplicação uma única vez (padrão singleton).

    Cria o diretório de dados se não existir e adiciona handlers de console
    e arquivo rotativo. Chamada automaticamente por `obter_logger`.
    """
    global _logger_configurado
    if _logger_configurado:
        return

    # Garantir que o diretório de dados existe
    DIRETORIO_DADOS.mkdir(parents=True, exist_ok=True)

    logger_raiz = logging.getLogger(NOME_LOGGER_RAIZ)
    logger_raiz.setLevel(logging.DEBUG)

    formatador = logging.Formatter(fmt=FORMATO_LOG, datefmt=FORMATO_DATA)

    # Handler de console — exibe INFO e acima
    handler_console = logging.StreamHandler(stream=sys.stdout)
    handler_console.setLevel(logging.INFO)
    handler_console.setFormatter(formatador)

    # Handler de arquivo rotativo — captura DEBUG e acima
    try:
        handler_arquivo = RotatingFileHandler(
            filename=ARQUIVO_LOG,
            maxBytes=TAMANHO_MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler_arquivo.setLevel(logging.DEBUG)
        handler_arquivo.setFormatter(formatador)
        logger_raiz.addHandler(handler_arquivo)
    except OSError as e:
        # Se não conseguir criar o arquivo de log, continua apenas com console
        print(f"[AVISO] Não foi possível criar arquivo de log: {e}", file=sys.stderr)

    logger_raiz.addHandler(handler_console)
    logger_raiz.propagate = False

    _logger_configurado = True


def obter_logger(nome: str) -> logging.Logger:
    """
    Retorna um logger filho do logger raiz da aplicação.

    Args:
        nome: Nome do módulo, geralmente `__name__`.

    Returns:
        Logger configurado e pronto para uso.

    Example:
        log = obter_logger(__name__)
        log.debug("Iniciando processamento")
        log.error("Falha ao abrir arquivo: %s", caminho)
    """
    _configurar_logger()
    return logging.getLogger(f"{NOME_LOGGER_RAIZ}.{nome}")
