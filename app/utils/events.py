"""
Contrato de dados para comunicação entre a thread de geração e a UI.

Define TypedDicts formais para cada tipo de evento publicado na
queue.Queue, eliminando bugs silenciosos de typo em chaves de dicionário
e tornando o código auto-documentado.

Uso:
    from queue import Queue
    from app.utils.events import EventoGerador, EventoProgresso

    fila: Queue[EventoGerador] = Queue()
    fila.put(EventoProgresso(tipo="progresso", atual=1, total=100))
"""

from typing import Literal, Union
from typing_extensions import TypedDict


class EventoProgresso(TypedDict):
    """
    Publicado a cada certificado processado (com sucesso ou erro).

    Attributes:
        tipo: Identificador literal do evento.
        atual: Número de certificados já processados (inclui erros).
        total: Número total de certificados a processar.
    """

    tipo: Literal["progresso"]
    atual: int
    total: int


class EventoSucesso(TypedDict):
    """
    Publicado quando um certificado é gerado com sucesso.

    Attributes:
        tipo: Identificador literal do evento.
        arquivo: Nome do arquivo gerado (sem o caminho completo).
    """

    tipo: Literal["sucesso"]
    arquivo: str


class EventoErro(TypedDict):
    """
    Publicado quando a geração de um certificado falha.

    O lote continua — este evento apenas registra a falha individual.

    Attributes:
        tipo: Identificador literal do evento.
        arquivo: Nome do arquivo que deveria ter sido gerado.
        motivo: Descrição legível do erro ocorrido.
    """

    tipo: Literal["erro"]
    arquivo: str
    motivo: str


class EventoConcluido(TypedDict):
    """
    Publicado quando o lote inteiro termina (com ou sem erros).

    Attributes:
        tipo: Identificador literal do evento.
        total_sucesso: Quantidade de certificados gerados com sucesso.
        total_erro: Quantidade de certificados que falharam.
    """

    tipo: Literal["concluido"]
    total_sucesso: int
    total_erro: int


# Union type para tipagem da Queue e do handler da UI
# Uso: fila: Queue[EventoGerador] = Queue()
EventoGerador = Union[EventoProgresso, EventoSucesso, EventoErro, EventoConcluido]
