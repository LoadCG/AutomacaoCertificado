"""
Módulo de carregamento e validação de planilhas de participantes.

Aceita arquivos .xlsx, .xls e .csv via pandas, normaliza nomes de colunas
e levanta exceções tipadas e descritivas em caso de dados inválidos.

Uso:
    from app.core.data_loader import carregar_planilha
    df = carregar_planilha(Path("participantes.xlsx"))
"""

from pathlib import Path
from typing import Set

import pandas as pd

from app.utils.logger import obter_logger

log = obter_logger(__name__)

# Extensões suportadas mapeadas para o engine de leitura do pandas
_EXTENSOES_SUPORTADAS: dict[str, str] = {
    ".xlsx": "openpyxl",
    ".xls": "xlrd",
    ".csv": "csv",  # valor especial — tratado separadamente
}


# ---------------------------------------------------------------------------
# Exceções tipadas
# ---------------------------------------------------------------------------


class ArquivoInvalidoError(Exception):
    """
    Levantada quando o arquivo não existe, não pode ser lido ou está corrompido.
    """


class FormatoNaoSuportadoError(Exception):
    """
    Levantada quando a extensão do arquivo não é suportada pelo carregador.
    """


class PlanilhaVaziaError(Exception):
    """
    Levantada quando o arquivo é válido mas não contém linhas de dados
    (apenas cabeçalho ou completamente vazio).
    """


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------


def carregar_planilha(caminho: Path) -> pd.DataFrame:
    """
    Carrega uma planilha de participantes a partir de um arquivo.

    Normaliza nomes de colunas (remove espaços nas bordas), valida que
    o arquivo não está vazio e retorna um DataFrame pronto para uso.

    Args:
        caminho: Caminho para o arquivo .xlsx, .xls ou .csv.

    Returns:
        DataFrame com colunas normalizadas e tipos inferidos pelo pandas.

    Raises:
        ArquivoInvalidoError: Se o arquivo não existir ou não puder ser lido.
        FormatoNaoSuportadoError: Se a extensão não for suportada.
        PlanilhaVaziaError: Se o arquivo não contiver linhas de dados.
    """
    caminho = Path(caminho)  # garantir que é um Path mesmo se string for passada

    log.info("Carregando planilha: %s", caminho)

    _validar_existencia(caminho)
    extensao = _validar_extensao(caminho)

    df = _ler_arquivo(caminho, extensao)
    df = _normalizar_colunas(df)
    _validar_dados(df, caminho)

    log.info(
        "Planilha carregada: %d linhas, %d colunas — %s",
        len(df),
        len(df.columns),
        list(df.columns),
    )
    return df


def obter_colunas(df: pd.DataFrame) -> list[str]:
    """
    Retorna a lista de nomes de colunas do DataFrame.

    Args:
        df: DataFrame carregado por `carregar_planilha`.

    Returns:
        Lista de strings com os nomes das colunas, em ordem.
    """
    return list(df.columns)


# ---------------------------------------------------------------------------
# Funções auxiliares privadas
# ---------------------------------------------------------------------------


def _validar_existencia(caminho: Path) -> None:
    """
    Verifica se o arquivo existe e é legível.

    Raises:
        ArquivoInvalidoError: Se o arquivo não existir ou não for um arquivo.
    """
    if not caminho.exists():
        raise ArquivoInvalidoError(
            f"Arquivo não encontrado: '{caminho}'"
        )
    if not caminho.is_file():
        raise ArquivoInvalidoError(
            f"O caminho '{caminho}' não aponta para um arquivo."
        )


def _validar_extensao(caminho: Path) -> str:
    """
    Verifica se a extensão do arquivo é suportada.

    Returns:
        Extensão em minúsculas (ex: '.xlsx').

    Raises:
        FormatoNaoSuportadoError: Se a extensão não estiver na lista de suporte.
    """
    extensao = caminho.suffix.lower()
    if extensao not in _EXTENSOES_SUPORTADAS:
        suportadas = ", ".join(_EXTENSOES_SUPORTADAS.keys())
        raise FormatoNaoSuportadoError(
            f"Formato '{extensao}' não suportado. "
            f"Formatos aceitos: {suportadas}"
        )
    return extensao


def _ler_arquivo(caminho: Path, extensao: str) -> pd.DataFrame:
    """
    Lê o arquivo com o engine correto para a extensão.

    Trata encoding UTF-8 com BOM para CSVs e fallback para latin-1
    em caso de erro de decodificação.

    Raises:
        ArquivoInvalidoError: Se o pandas não conseguir ler o arquivo.
    """
    try:
        if extensao == ".csv":
            return _ler_csv(caminho)
        else:
            engine = _EXTENSOES_SUPORTADAS[extensao]
            return pd.read_excel(caminho, engine=engine)
    except (ValueError, Exception) as e:
        raise ArquivoInvalidoError(
            f"Não foi possível ler o arquivo '{caminho.name}': {e}"
        ) from e


def _ler_csv(caminho: Path) -> pd.DataFrame:
    """
    Lê arquivo CSV com detecção automática de encoding e separador.

    Tenta UTF-8-BOM primeiro (comum em arquivos exportados do Excel),
    depois UTF-8 puro, depois latin-1 como último recurso.

    Returns:
        DataFrame com os dados do CSV.

    Raises:
        ArquivoInvalidoError: Se nenhum encoding conseguir ler o arquivo.
    """
    separadores = [",", ";", "\t"]
    encodings = ["utf-8-sig", "utf-8", "latin-1"]

    for encoding in encodings:
        for sep in separadores:
            try:
                df = pd.read_csv(caminho, sep=sep, encoding=encoding)
                # Verifica se a leitura produziu mais de uma coluna (separador correto)
                if len(df.columns) > 1 or len(df) == 0:
                    log.debug(
                        "CSV lido com encoding='%s', sep='%s'", encoding, sep
                    )
                    return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue

    raise ArquivoInvalidoError(
        f"Não foi possível determinar o encoding ou separador do arquivo '{caminho.name}'. "
        "Salve o arquivo como CSV UTF-8 ou XLSX e tente novamente."
    )


def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza os nomes das colunas removendo espaços nas bordas.

    Também remove colunas completamente vazias geradas pelo pandas ao
    ler planilhas com colunas em branco no Excel.

    Returns:
        DataFrame com colunas normalizadas.
    """
    # Remove espaços das bordas dos nomes
    df.columns = [str(col).strip() for col in df.columns]

    # Remove colunas sem nome (ex: "Unnamed: 3") geradas por colunas vazias
    colunas_sem_nome: Set[str] = {
        col for col in df.columns if col.startswith("Unnamed:")
    }
    if colunas_sem_nome:
        log.debug("Removendo colunas sem nome: %s", colunas_sem_nome)
        df = df.drop(columns=list(colunas_sem_nome))

    return df


def _validar_dados(df: pd.DataFrame, caminho: Path) -> None:
    """
    Valida que o DataFrame contém pelo menos uma linha de dados.

    Raises:
        PlanilhaVaziaError: Se o DataFrame não tiver linhas ou colunas.
    """
    if df.empty or len(df.columns) == 0:
        raise PlanilhaVaziaError(
            f"O arquivo '{caminho.name}' está vazio ou contém apenas cabeçalho. "
            "Verifique se a planilha possui ao menos uma linha de dados."
        )
