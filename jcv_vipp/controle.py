"""Histórico dos envios já postados, para o mesmo cliente não ser postado duas vezes."""
import sqlite3
from datetime import datetime
from pathlib import Path


class Controle:
    def __init__(self, caminho: Path):
        self.db = sqlite3.connect(caminho)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS envios (
                   chave TEXT PRIMARY KEY,
                   cod_cliente TEXT NOT NULL,
                   etiqueta TEXT NOT NULL,
                   postado_em TEXT NOT NULL
               )"""
        )

    def etiqueta(self, chave: str) -> str | None:
        linha = self.db.execute("SELECT etiqueta FROM envios WHERE chave = ?", (chave,)).fetchone()
        return linha[0] if linha else None

    def registrar(self, chave: str, cod_cliente: str, etiqueta: str) -> None:
        self.db.execute(
            "INSERT INTO envios (chave, cod_cliente, etiqueta, postado_em) VALUES (?, ?, ?, ?)",
            (chave, cod_cliente, etiqueta, datetime.now().isoformat(timespec="seconds")),
        )
        self.db.commit()
