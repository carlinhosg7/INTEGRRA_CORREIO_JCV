"""Arquivos gerados a partir dos envios: importação para o VIPP e relatório de erros."""
import csv
from pathlib import Path

from .envio import Envio

# Ordem das colunas do arquivo de importação. O perfil "Personalizado" do VIPP
# deve ser configurado com esta mesma ordem, separador ";" e ignorando o cabeçalho.
COLUNAS_VIPP = (
    "CNPJ_CPF", "NOME", "SEGUNDA_LINHA", "ENDERECO", "NUMERO", "COMPLEMENTO", "BAIRRO",
    "CIDADE", "UF", "CEP", "TELEFONE", "CELULAR", "EMAIL", "SERVICO_ECT", "PESO_G",
    "OBSERVACAO", "COD_CLIENTE",
)


def gravar_importacao_vipp(envios: list[Envio], destino: Path, servico: str, peso_g: str) -> int:
    validos = [e for e in envios if e.valido]
    with open(destino, "w", encoding="latin-1", errors="replace", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(COLUNAS_VIPP)
        for e in validos:
            w.writerow([
                e.cpf_cnpj, e.nome, e.segunda_linha, e.endereco, e.numero, e.complemento,
                e.bairro, e.cidade, e.uf, e.cep, e.telefone, e.celular, e.email, servico,
                peso_g, e.observacao, e.cod_cliente,
            ])
    return len(validos)


def gravar_relatorio(envios: list[Envio], destino: Path) -> int:
    """Lista os envios com erro (não postados) ou aviso (postados com ajuste)."""
    com_problema = [e for e in envios if e.erros or e.avisos]
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["SITUACAO", "COD_CLIENTE", "NOME", "LINHAS_CSV", "ERROS", "AVISOS"])
        for e in com_problema:
            w.writerow([
                "NAO ENVIADO" if e.erros else "ENVIADO COM AJUSTE", e.cod_cliente,
                e.nome, ",".join(e.linhas_csv), " | ".join(e.erros), " | ".join(e.avisos),
            ])
    return len(com_problema)
