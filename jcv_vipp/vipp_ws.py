"""Cliente do Web Service PostagemVipp (SOAP), operação PostarObjeto."""
import os
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .envio import Envio

URL = "https://vpsrv.visualset.com.br/PostagemVipp.asmx"
NS = "http://www.visualset.inf.br/"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"


@dataclass
class ConfigVipp:
    usuario: str
    token: str
    id_perfil: str
    servico: str
    peso_g: str = "20"

    @classmethod
    def do_ambiente(cls) -> "ConfigVipp":
        faltando = [v for v in ("VIPP_USUARIO", "VIPP_TOKEN", "VIPP_PERFIL", "VIPP_SERVICO")
                    if not os.environ.get(v)]
        if faltando:
            raise RuntimeError(f"Defina as variáveis de ambiente: {', '.join(faltando)}")
        return cls(
            usuario=os.environ["VIPP_USUARIO"],
            token=os.environ["VIPP_TOKEN"],
            id_perfil=os.environ["VIPP_PERFIL"],
            servico=os.environ["VIPP_SERVICO"],
            peso_g=os.environ.get("VIPP_PESO_G", "20"),
        )


@dataclass
class Resultado:
    etiqueta: str
    erros: list[str]
    xml: str


def _filho(pai: ET.Element, nome: str, texto: str | None = None) -> ET.Element:
    el = ET.SubElement(pai, f"{{{NS}}}{nome}")
    if texto is not None:
        el.text = texto
    return el


def montar_requisicao(envio: Envio, cfg: ConfigVipp) -> bytes:
    """Monta o envelope SOAP. Remetente e contrato vêm do perfil cadastrado no VIPP."""
    ET.register_namespace("soap", SOAP_NS)
    env = ET.Element(f"{{{SOAP_NS}}}Envelope")
    body = ET.SubElement(env, f"{{{SOAP_NS}}}Body")
    postagem = _filho(_filho(body, "PostarObjeto"), "PostagemVipp")

    perfil = _filho(postagem, "PerfilVipp")
    _filho(perfil, "Usuario", cfg.usuario)
    _filho(perfil, "Token", cfg.token)
    _filho(perfil, "IdPerfil", cfg.id_perfil)

    dest = _filho(postagem, "Destinatario")
    for tag, valor in (
        ("CnpjCpf", envio.cpf_cnpj), ("Nome", envio.nome),
        ("SegundaLinhaDestinatario", envio.segunda_linha), ("Endereco", envio.endereco),
        ("Numero", envio.numero), ("Complemento", envio.complemento),
        ("Bairro", envio.bairro), ("Cidade", envio.cidade), ("UF", envio.uf),
        ("Cep", envio.cep), ("Telefone", envio.telefone), ("Celular", envio.celular),
        ("Email", envio.email),
    ):
        _filho(dest, tag, valor)

    _filho(_filho(postagem, "Servico"), "ServicoECT", cfg.servico)

    volume = _filho(_filho(postagem, "Volumes"), "VolumeObjeto")
    _filho(volume, "Peso", cfg.peso_g)
    _filho(volume, "ObservacaoVisual", envio.observacao)
    _filho(volume, "CodigoBarraCliente", envio.cod_cliente)

    return ET.tostring(env, encoding="utf-8", xml_declaration=True)


def interpretar_resposta(xml_resposta: str) -> Resultado:
    """Extrai a etiqueta e os erros do PostarObjetoResult.

    O conteúdo do resultado é um XML próprio do VIPP; os nomes das tags abaixo
    precisam ser confirmados com uma resposta real.
    """
    raiz = ET.fromstring(xml_resposta)
    resultado = raiz.find(f".//{{{NS}}}PostarObjetoResult")
    interno = resultado.text if resultado is not None and resultado.text else ""
    etiqueta, erros = "", []
    if interno.strip():
        doc = ET.fromstring(interno)
        for el in doc.iter():
            tag = el.tag.split("}")[-1]
            texto = (el.text or "").strip()
            if not texto:
                continue
            if tag in ("Etiqueta", "NrEtiqueta", "NrEtiquetaPostagem") and not etiqueta:
                etiqueta = texto
            elif tag in ("Descricao", "Mensagem", "Erro"):
                erros.append(texto)
    return Resultado(etiqueta=etiqueta, erros=erros, xml=interno)


def postar(envio: Envio, cfg: ConfigVipp, timeout: int = 60) -> Resultado:
    req = urllib.request.Request(
        URL,
        data=montar_requisicao(envio, cfg),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{NS}PostarObjeto"',
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return interpretar_resposta(resp.read().decode("utf-8"))
