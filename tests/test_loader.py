"""Testes unitários do módulo data_loader."""

import pytest
from pathlib import Path
import pandas as pd

from app.core.data_loader import (
    carregar_planilha,
    obter_colunas,
    ArquivoInvalidoError,
    FormatoNaoSuportadoError,
    PlanilhaVaziaError,
)


class TestCarregarPlanilha:
    def test_xlsx_valido(self, xlsx_simples: Path):
        df = carregar_planilha(xlsx_simples)
        assert len(df) == 2
        assert "Nome" in df.columns
        assert "RG" in df.columns

    def test_csv_utf8(self, csv_utf8: Path):
        df = carregar_planilha(csv_utf8)
        assert len(df) == 2
        assert df["Nome"].iloc[0] == "Alice"

    def test_arquivo_inexistente(self, tmp_path: Path):
        with pytest.raises(ArquivoInvalidoError, match="não encontrado"):
            carregar_planilha(tmp_path / "nao_existe.xlsx")

    def test_extensao_invalida(self, tmp_path: Path):
        arquivo = tmp_path / "dados.txt"
        arquivo.write_text("dados")
        with pytest.raises(FormatoNaoSuportadoError, match=".txt"):
            carregar_planilha(arquivo)

    def test_planilha_vazia(self, tmp_path: Path):
        df_vazio = pd.DataFrame()
        caminho = tmp_path / "vazio.xlsx"
        df_vazio.to_excel(caminho, index=False)
        with pytest.raises(PlanilhaVaziaError):
            carregar_planilha(caminho)

    def test_normaliza_colunas_com_espacos(self, tmp_path: Path):
        df = pd.DataFrame({"  Nome  ": ["Alice"], " RG ": ["111"]})
        caminho = tmp_path / "espacos.xlsx"
        df.to_excel(caminho, index=False)
        resultado = carregar_planilha(caminho)
        assert "Nome" in resultado.columns
        assert "RG" in resultado.columns

    def test_csv_semicolon_separator(self, tmp_path: Path):
        conteudo = "Nome;RG\nAlice;111\nBob;222\n"
        caminho = tmp_path / "ponto_virgula.csv"
        caminho.write_text(conteudo, encoding="utf-8")
        df = carregar_planilha(caminho)
        assert "Nome" in df.columns
        assert len(df) == 2


class TestObterColunas:
    def test_retorna_lista_strings(self, xlsx_simples: Path):
        df = carregar_planilha(xlsx_simples)
        colunas = obter_colunas(df)
        assert isinstance(colunas, list)
        assert all(isinstance(c, str) for c in colunas)
        assert "Nome" in colunas
