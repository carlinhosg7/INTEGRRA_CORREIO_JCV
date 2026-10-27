import csv
import xml.etree.ElementTree as ET

import pytest

from jcv_vipp import exportar, leitor_csv
from jcv_vipp.envio import agrupar
from jcv_vipp.vipp_ws import NS, ConfigVipp, interpretar_resposta, montar_requisicao

CABECALHO = (
    "QTD_SOCIOS;COD_CLIENTE;NOME;E_MAIL;DATA_CADASTRO;TELEFONE;CELULAR;CNPJ_CPF;INSCRICAO_RG;"
    "PJ_INSC_MUNICIPAL;TIPO_PESSOA;PF_DATA_NASCIMENTO;PF_PROFISSAO;PF_TRABALHO_LOCAL;"
    "PF_TRABALHO_FONE;ENDERECO_NUMERO;ENDERECO_COMPLEMENTO;BAIRRO;CIDADE;ENDERECO;ESTADO;CEP;"
    "PF_CONJUGE;PF_CONJUGE_CPF;PF_CONJUGE_RG;PF_REGIME_COMUNHAO;PJ_RESP_LEGAL;PJ_RESP_LEGAL_CPF;"
    "PJ_RESP_LEGAL_RG;PF_RESP_LEGAL;PF_RENDA_MENSAL;FAX;DESC_ESTADO_CIVIL;RESP_NOME;RESP_CPF;"
    "RESP_RG;DIA_NASCIMENTO;MES_NASCIMENTO;MES_DESC_NASC;COD_AREA;COD_IMOVEL;SOCIOS"
).split(";")


def linha(**campos):
    base = dict.fromkeys(CABECALHO, "")
    base.update(COD_CLIENTE="1", NOME="FULANO DE TAL", CNPJ_CPF="12345678909",
                ENDERECO="RUA DAS FLORES", ENDERECO_NUMERO="10", BAIRRO="CENTRO",
                CIDADE="BIRIGUI", ESTADO="SP", CEP="16200000", COD_AREA="A", COD_IMOVEL="1")
    base.update(campos)
    return base


@pytest.fixture
def relatorio(tmp_path):
    def gravar(*linhas):
        caminho = tmp_path / "RELATORIO.CSV"
        with open(caminho, "w", encoding="latin-1", newline="") as f:
            w = csv.DictWriter(f, CABECALHO, delimiter=";", lineterminator="\r\n")
            w.writeheader()
            w.writerows(linhas)
        return leitor_csv.ler(caminho)
    return gravar


def test_linhas_repetidas_por_socio_viram_um_envio(relatorio):
    linhas = relatorio(linha(SOCIOS="SOCIO A"), linha(SOCIOS="SOCIO A"), linha(COD_CLIENTE="2"))
    envios = agrupar(linhas)
    assert [e.cod_cliente for e in envios] == ["1", "2"]
    assert envios[0].linhas_csv == ["2", "3"]


def test_agrupamento_por_cliente_ou_por_imovel(relatorio):
    linhas = relatorio(linha(COD_IMOVEL="1"), linha(COD_IMOVEL="2"))
    por_cliente = agrupar(linhas, por="cliente")
    assert len(por_cliente) == 1
    assert por_cliente[0].imoveis == ["A-1", "A-2"]
    assert por_cliente[0].observacao == "CLI 1 IMV A-1,A-2"
    assert len(agrupar(linhas, por="imovel")) == 2


def test_validacao_de_endereco(relatorio):
    linhas = relatorio(
        linha(COD_CLIENTE="1", CEP="15290", ENDERECO_NUMERO=""),
        linha(COD_CLIENTE="2", CEP="123"),
        linha(COD_CLIENTE="3", ESTADO=""),
        linha(COD_CLIENTE="4", NOME="MARIA " + "SOBRENOME " * 7),
    )
    e1, e2, e3, e4 = agrupar(linhas)
    assert e1.valido and e1.cep == "15290000" and e1.numero == "S/N"
    assert not e2.valido and "CEP inválido" in e2.erros[0]
    assert not e3.valido
    assert len(e4.nome) <= 50 and e4.segunda_linha.startswith("SOBRENOME")
    assert not e4.nome.endswith(" ")


@pytest.mark.parametrize("numero, complemento, esperado", [
    ("42 LJ 1", "", ("42", "LJ 1")),
    ("1114/1118", "", ("1114", "/1118")),
    ("888-SILVAR", "", ("888", "SILVAR")),
    ("AP 1102", "BLOCO 2", ("S/N", "AP 1102 BLOCO 2")),
])
def test_complemento_dentro_do_numero(relatorio, numero, complemento, esperado):
    e = agrupar(relatorio(linha(ENDERECO_NUMERO=numero, ENDERECO_COMPLEMENTO=complemento)))[0]
    assert (e.numero, e.complemento) == esperado


def test_arquivos_gerados(relatorio, tmp_path):
    envios = agrupar(relatorio(linha(NOME="JOSÉ AÇAÍ"), linha(COD_CLIENTE="2", CEP="")))
    arq = tmp_path / "imp.csv"
    assert exportar.gravar_importacao_vipp(envios, arq, "80160", "20") == 1
    linhas = arq.read_text(encoding="latin-1").splitlines()
    assert linhas[0].startswith("CNPJ_CPF;NOME")
    assert "JOSÉ AÇAÍ" in linhas[1] and ";80160;20;" in linhas[1]
    rel = tmp_path / "rel.csv"
    assert exportar.gravar_relatorio(envios, rel) == 1
    assert "NAO ENVIADO" in rel.read_text(encoding="utf-8-sig")


def test_requisicao_soap(relatorio):
    envio = agrupar(relatorio(linha()))[0]
    cfg = ConfigVipp(usuario="u", token="t", id_perfil="99", servico="80160")
    xml = ET.fromstring(montar_requisicao(envio, cfg))
    ns = {"v": NS}
    assert xml.find(".//v:PerfilVipp/v:IdPerfil", ns).text == "99"
    assert xml.find(".//v:Destinatario/v:Cep", ns).text == "16200000"
    assert xml.find(".//v:Servico/v:ServicoECT", ns).text == "80160"
    assert xml.find(".//v:VolumeObjeto/v:ObservacaoVisual", ns).text == "CLI 1 IMV A-1"


def test_interpretar_resposta():
    interno = "<Retorno><Volumes><Volume><Etiqueta>BR123456789BR</Etiqueta></Volume></Volumes></Retorno>"
    soap = (
        f'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
        f'<PostarObjetoResponse xmlns="{NS}"><PostarObjetoResult>'
        f'{interno.replace("<", "&lt;").replace(">", "&gt;")}'
        f"</PostarObjetoResult></PostarObjetoResponse></soap:Body></soap:Envelope>"
    )
    r = interpretar_resposta(soap)
    assert r.etiqueta == "BR123456789BR" and r.erros == []
