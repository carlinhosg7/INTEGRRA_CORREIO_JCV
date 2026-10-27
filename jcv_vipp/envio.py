"""Conversão das linhas do CSV em envios (um por etiqueta) e validação dos endereços."""
import re
import unicodedata
from dataclasses import dataclass, field

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# Tamanhos máximos aceitos na etiqueta dos Correios.
LIMITES = {"nome": 50, "endereco": 50, "numero": 6, "complemento": 30, "bairro": 30, "cidade": 30}


@dataclass
class Envio:
    cod_cliente: str
    nome: str
    segunda_linha: str
    cpf_cnpj: str
    endereco: str
    numero: str
    complemento: str
    bairro: str
    cidade: str
    uf: str
    cep: str
    telefone: str
    celular: str
    email: str
    imoveis: list[str] = field(default_factory=list)
    linhas_csv: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def valido(self) -> bool:
        return not self.erros

    @property
    def observacao(self) -> str:
        """Texto impresso na etiqueta para conferência interna (cliente e imóveis)."""
        texto = f"CLI {self.cod_cliente}"
        if self.imoveis:
            texto += " IMV " + ",".join(self.imoveis)
        return texto[:50]


def _limpar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto or "")
    return re.sub(r"\s+", " ", texto).strip().upper()


def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _cortar(envio: Envio, campo: str, valor: str) -> str:
    limite = LIMITES[campo]
    if len(valor) > limite:
        envio.avisos.append(f"{campo} cortado em {limite} caracteres")
        return valor[:limite].rstrip()
    return valor


def _dividir_nome(nome: str) -> tuple[str, str]:
    """Nomes longos vão para a segunda linha do destinatário, quebrando entre palavras."""
    limite = LIMITES["nome"]
    if len(nome) <= limite:
        return nome, ""
    corte = nome.rfind(" ", 0, limite + 1)
    if corte <= 0:
        corte = limite
    return nome[:corte].rstrip(), nome[corte:].strip()[:limite]


def _imovel(linha: dict[str, str]) -> str:
    area, imovel = linha.get("COD_AREA", ""), linha.get("COD_IMOVEL", "")
    return f"{area}-{imovel}" if area or imovel else ""


def criar_envio(linha: dict[str, str]) -> Envio:
    nome, segunda = _dividir_nome(_limpar(linha["NOME"]))
    envio = Envio(
        cod_cliente=linha["COD_CLIENTE"],
        nome=nome,
        segunda_linha=segunda,
        cpf_cnpj=_digitos(linha["CNPJ_CPF"]),
        endereco=_limpar(linha["ENDERECO"]),
        numero=_limpar(linha["ENDERECO_NUMERO"]),
        complemento=_limpar(linha["ENDERECO_COMPLEMENTO"]),
        bairro=_limpar(linha["BAIRRO"]),
        cidade=_limpar(linha["CIDADE"]),
        uf=_limpar(linha["ESTADO"]),
        cep=_digitos(linha["CEP"]),
        telefone=_digitos(linha.get("TELEFONE", "")),
        celular=_digitos(linha.get("CELULAR", "")),
        email=linha.get("E_MAIL", "").strip().lower(),
    )
    imovel = _imovel(linha)
    if imovel:
        envio.imoveis.append(imovel)
    envio.linhas_csv.append(linha["_linha"])
    validar(envio)
    return envio


def _separar_numero(envio: Envio) -> None:
    """O sistema às vezes traz o complemento junto do número ("42 LJ 1", "AP 1102").

    O que passar do limite do número vai para o início do complemento.
    """
    if len(envio.numero) <= LIMITES["numero"]:
        return
    m = re.match(r"^(\d+[A-Z]?)\b[\s,-]*(.*)$", envio.numero)
    numero, resto = (m.group(1), m.group(2)) if m else ("", envio.numero)
    envio.complemento = " ".join(p for p in (resto, envio.complemento) if p)
    envio.numero = numero
    envio.avisos.append("parte do número movida para o complemento")


def validar(envio: Envio) -> None:
    if not envio.cod_cliente:
        envio.erros.append("código do cliente vazio")
    if not envio.nome:
        envio.erros.append("nome vazio")
    if not envio.endereco:
        envio.erros.append("endereço vazio")
    if not envio.cidade:
        envio.erros.append("cidade vazia")
    if envio.uf not in UFS:
        envio.erros.append(f"UF inválida: '{envio.uf}'")

    if len(envio.cep) == 5:
        envio.cep += "000"
        envio.avisos.append("CEP com 5 dígitos completado com 000")
    if len(envio.cep) != 8:
        envio.erros.append(f"CEP inválido: '{envio.cep}'")

    _separar_numero(envio)
    if not envio.numero:
        envio.numero = "S/N"
        envio.avisos.append("número vazio, usado S/N")
    if not envio.bairro:
        envio.avisos.append("bairro vazio")

    envio.endereco = _cortar(envio, "endereco", envio.endereco)
    envio.numero = _cortar(envio, "numero", envio.numero)
    envio.complemento = _cortar(envio, "complemento", envio.complemento)
    envio.bairro = _cortar(envio, "bairro", envio.bairro)
    envio.cidade = _cortar(envio, "cidade", envio.cidade)


def agrupar(linhas: list[dict[str, str]], por: str = "cliente") -> list[Envio]:
    """Junta as linhas repetidas do relatório em envios.

    O relatório repete o cliente uma vez por sócio e por imóvel.
    - por="cliente": uma etiqueta por cliente e endereço, listando os imóveis na observação.
    - por="imovel": uma etiqueta por cliente e imóvel.
    """
    if por not in ("cliente", "imovel"):
        raise ValueError("agrupamento deve ser 'cliente' ou 'imovel'")
    envios: dict[tuple, Envio] = {}
    for linha in linhas:
        envio = criar_envio(linha)
        chave = (envio.cod_cliente, envio.cep, envio.endereco, envio.numero, envio.complemento)
        if por == "imovel":
            chave += (_imovel(linha),)
        existente = envios.get(chave)
        if existente is None:
            envios[chave] = envio
            continue
        existente.linhas_csv.extend(envio.linhas_csv)
        for imovel in envio.imoveis:
            if imovel not in existente.imoveis:
                existente.imoveis.append(imovel)
    return list(envios.values())
