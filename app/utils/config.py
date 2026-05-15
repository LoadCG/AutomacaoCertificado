"""
Módulo de persistência de configurações do Gerador de Certificados.

Salva e recarrega automaticamente as últimas seleções do usuário em
~/.gerador_certificados/config.json, permitindo que o app retome do ponto
onde o usuário parou na sessão anterior.

Uso:
    from app.utils.config import Config
    config = Config()
    config.ultimo_template = "/caminho/template.pptx"
    config.salvar()
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from app.utils.logger import obter_logger

log = obter_logger(__name__)

# Localização do arquivo de configuração
DIRETORIO_DADOS: Path = Path.home() / ".gerador_certificados"
ARQUIVO_CONFIG: Path = DIRETORIO_DADOS / "config.json"


@dataclass
class Config:
    """
    Configurações persistentes da aplicação.

    Todos os campos são opcionais — representam o último estado conhecido
    da sessão do usuário. O método `salvar()` persiste para disco e
    `carregar()` recarrega do disco, retornando uma nova instância.
    """

    ultimo_template: Optional[str] = field(default=None)
    """Caminho absoluto do último template .pptx selecionado."""

    ultima_planilha: Optional[str] = field(default=None)
    """Caminho absoluto da última planilha .xlsx/.csv selecionada."""

    ultima_pasta_saida: Optional[str] = field(default=None)
    """Caminho absoluto da última pasta de saída selecionada."""

    exportar_pdf: bool = field(default=False)
    """Se True, exporta também em PDF via COM interop."""

    padrao_nome: Optional[str] = field(default=None)
    """Padrão de nome de arquivo, ex: '{{NOME}} - {DATA}'. None usa o padrão do sistema."""

    tema_aparencia: str = field(default="dark")
    """Modo de aparência do sistema: 'light' ou 'dark'."""


    def salvar(self) -> None:
        """
        Persiste as configurações atuais em disco (JSON).

        Cria o diretório ~/.gerador_certificados se não existir.
        Falhas de escrita são logadas mas não propagadas — o app
        continua funcionando mesmo sem persistência.
        """
        try:
            DIRETORIO_DADOS.mkdir(parents=True, exist_ok=True)
            dados = asdict(self)
            with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            log.debug("Configurações salvas em: %s", ARQUIVO_CONFIG)
        except OSError as e:
            log.warning("Não foi possível salvar configurações: %s", e)

    @classmethod
    def carregar(cls) -> "Config":
        """
        Carrega configurações do disco, retornando valores padrão se
        o arquivo não existir ou estiver corrompido.

        Returns:
            Instância de Config com os dados da sessão anterior,
            ou uma instância com valores padrão (todos None/False).
        """
        if not ARQUIVO_CONFIG.exists():
            log.debug("Arquivo de configuração não encontrado. Usando padrões.")
            return cls()

        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                dados: dict = json.load(f)

            # Filtra apenas as chaves conhecidas para evitar erros com
            # campos obsoletos de versões anteriores do arquivo
            campos_validos = {
                campo for campo in cls.__dataclass_fields__
            }
            dados_filtrados = {
                k: v for k, v in dados.items() if k in campos_validos
            }

            config = cls(**dados_filtrados)
            log.debug("Configurações carregadas de: %s", ARQUIVO_CONFIG)
            return config

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            log.warning(
                "Arquivo de configuração corrompido, usando padrões: %s", e
            )
            return cls()

    def validar_caminhos(self) -> "Config":
        """
        Retorna uma cópia da config com caminhos inválidos zerados.

        Útil ao iniciar a aplicação — evita que caminhos de sessões
        antigas (arquivos deletados ou movidos) causem erros silenciosos.

        Returns:
            Nova instância de Config com caminhos verificados.
        """
        copia = Config(
            ultimo_template=self.ultimo_template,
            ultima_planilha=self.ultima_planilha,
            ultima_pasta_saida=self.ultima_pasta_saida,
            exportar_pdf=self.exportar_pdf,
        )

        if copia.ultimo_template and not Path(copia.ultimo_template).is_file():
            log.debug("Template anterior não encontrado, zerando: %s", copia.ultimo_template)
            copia.ultimo_template = None

        if copia.ultima_planilha and not Path(copia.ultima_planilha).is_file():
            log.debug("Planilha anterior não encontrada, zerando: %s", copia.ultima_planilha)
            copia.ultima_planilha = None

        if copia.ultima_pasta_saida and not Path(copia.ultima_pasta_saida).is_dir():
            log.debug("Pasta de saída anterior não encontrada, zerando: %s", copia.ultima_pasta_saida)
            copia.ultima_pasta_saida = None

        return copia
