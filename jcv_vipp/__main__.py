"""Linha de comando: python -m jcv_vipp RELATORIO.CSV [opções]"""
import argparse
from datetime import date
from pathlib import Path

from . import exportar, leitor_csv
from .controle import Controle
from .envio import agrupar


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Gera os envios do VIPP a partir do relatório de clientes.")
    p.add_argument("csv", type=Path, help="relatório diário (RELATORIO.CSV)")
    p.add_argument("--saida", type=Path, default=Path("saida"), help="pasta dos arquivos gerados")
    p.add_argument("--agrupar", choices=("cliente", "imovel"), default="cliente",
                   help="uma etiqueta por cliente (padrão) ou por imóvel")
    p.add_argument("--servico", default="", help="código do serviço ECT para o arquivo de importação")
    p.add_argument("--peso", default="20", help="peso em gramas para o arquivo de importação")
    p.add_argument("--postar", action="store_true",
                   help="registra cada envio no Web Service do VIPP (usa as variáveis VIPP_*)")
    a = p.parse_args(argv)

    linhas = leitor_csv.ler(a.csv)
    envios = agrupar(linhas, por=a.agrupar)
    a.saida.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")

    validos = exportar.gravar_importacao_vipp(
        envios, a.saida / f"importacao_vipp_{hoje}.csv", a.servico, a.peso)
    problemas = exportar.gravar_relatorio(envios, a.saida / f"relatorio_erros_{hoje}.csv")
    invalidos = sum(1 for e in envios if not e.valido)

    print(f"{len(linhas)} linhas lidas, {len(envios)} envios ({a.agrupar}).")
    print(f"{validos} prontos para o VIPP, {invalidos} com erro, {problemas} no relatório de erros/avisos.")

    if a.postar:
        _postar([e for e in envios if e.valido], a.saida, a.agrupar)


def _postar(envios, saida: Path, agrupamento: str) -> None:
    from .vipp_ws import ConfigVipp, postar

    cfg = ConfigVipp.do_ambiente()
    controle = Controle(saida / "controle_envios.sqlite")
    novos = repetidos = falhas = 0
    for e in envios:
        chave = f"{agrupamento}:{e.cod_cliente}:{e.cep}:{e.endereco}:{e.numero}:{','.join(e.imoveis)}"
        if controle.etiqueta(chave):
            repetidos += 1
            continue
        r = postar(e, cfg)
        if r.etiqueta and not r.erros:
            controle.registrar(chave, e.cod_cliente, r.etiqueta)
            novos += 1
        else:
            falhas += 1
            print(f"Falha cliente {e.cod_cliente}: {' | '.join(r.erros) or r.xml[:200]}")
    print(f"Postados: {novos}, já postados antes: {repetidos}, falhas: {falhas}.")


if __name__ == "__main__":
    main()
