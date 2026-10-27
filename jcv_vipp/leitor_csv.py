"""Leitura do relatório diário de clientes exportado pelo sistema da JCV."""
import csv
from pathlib import Path

ENCODING = "latin-1"
SEPARADOR = ";"

COLUNAS_OBRIGATORIAS = (
    "COD_CLIENTE", "NOME", "CNPJ_CPF", "ENDERECO", "ENDERECO_NUMERO",
    "ENDERECO_COMPLEMENTO", "BAIRRO", "CIDADE", "ESTADO", "CEP",
)


def ler(caminho: str | Path) -> list[dict[str, str]]:
    """Lê o CSV e devolve as linhas com todos os valores como texto sem espaços nas pontas."""
    with open(caminho, encoding=ENCODING, newline="") as f:
        leitor = csv.DictReader(f, delimiter=SEPARADOR)
        faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in (leitor.fieldnames or [])]
        if faltando:
            raise ValueError(f"Colunas ausentes no CSV: {', '.join(faltando)}")
        linhas = []
        for n, linha in enumerate(leitor, start=2):
            registro = {k: (v or "").strip() for k, v in linha.items() if k is not None}
            registro["_linha"] = str(n)
            linhas.append(registro)
    return linhas
