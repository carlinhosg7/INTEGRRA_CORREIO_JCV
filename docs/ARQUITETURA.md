# Integração JCV × Correios (VIPP) — Etiquetas para envio de boletos

## 1. O que foi levantado sobre o VIPP

- A página `https://vipp-novo.visualset.com.br/vipp/entradadados/FrmImportarArquivos.php` exige
  **login com usuário/senha e captcha**. Por isso não dá para automatizar o upload pela tela;
  ela serve só para importação manual.
- O VIPP aceita importação por **perfis de importação** (menu *Cadastros > Perfil (Modelo) de Importação*),
  nos layouts **Visual Set (XML padrão), Correios, EDI e Personalizado**, por tela ou por **FTP**.
  No perfil se define remetente, contrato/cartão, serviço, se ignora cabeçalho e se já
  **etiqueta e libera** os registros na importação.
- Existe um **Web Service SOAP público** (`https://vpsrv.visualset.com.br/PostagemVipp.asmx`)
  com as operações `PostarObjeto`, `PostarObjetoObject`, `SituacaoPostagem`,
  `ListarRastreioObjeto`, `BloquearObjetoCorreios`, entre outras. A autenticação é por
  `PerfilVipp` (`Usuario`, `Token`, `IdPerfil`) — sem captcha.

### Estrutura de `PostarObjeto` (resumo)

| Bloco | Campos principais |
|---|---|
| PerfilVipp | Usuario, Token, IdPerfil |
| ContratoEct | NrContrato, CodigoAdministrativo, NrCartao (opcional se o perfil já define) |
| Remetente | CnpjCpf, Nome, Endereco, Numero, Complemento, Bairro, Cidade, UF, CEP, Telefone, Email |
| Destinatario | CnpjCpf, Nome, SegundaLinhaDestinatario, Endereco, Numero, Complemento, Bairro, Cidade, UF, Cep, Telefone, Celular, Email |
| Servico | ServicoECT (código do serviço dos Correios, ex.: carta registrada) |
| NotasFiscais | opcional |
| Volumes/VolumeObjeto | Peso, TipoEmbalagem, Altura, Largura, Comprimento, ObservacaoVisual, CodigoBarraCliente, Conteudo, ValorDeclarado, Etiqueta… |

A resposta (`PostarObjetoResult`) é um XML com o número da etiqueta (objeto) ou a lista de erros.

## 2. Arquitetura proposta

```
 CSV diário (clientes/boletos)
          │
          ▼
 [1] Leitor + validação ──► relatório de erros (CEP, UF, campos vazios, duplicados)
          │
          ▼
 [2] Mapeador CSV → modelo "Envio" (configurável em mapeamento.yaml)
          │
          ├──► [3a] Web Service VIPP (PostarObjeto)  ← caminho principal
          │         registra o envio e recebe o nº da etiqueta
          │
          └──► [3b] Gerador de arquivo de importação (XML padrão VIPP / CSV personalizado)
                    ← caminho alternativo: upload manual na tela ou via FTP
          │
          ▼
 [4] Controle de envios (SQLite): linha do CSV, nº boleto, etiqueta, status, data
     → evita postar o mesmo cliente duas vezes se o CSV for reprocessado
          │
          ▼
 [5] Impressão: PDF de etiquetas (A4 Pimaco ou térmica 10×15) ou impressão pela tela do VIPP
          │
          ▼
 [6] Rastreio/conferência (SituacaoPostagem / ListarRastreioObjeto) — fase 2
```

### Tecnologia sugerida

- **Python 3.12**: `csv` (leitura), `zeep` (SOAP do VIPP), `reportlab` + código de barras/DataMatrix
  (PDF das etiquetas), `sqlite3` (controle).
- Interface: primeiro uma **linha de comando** (`python -m jcv_vipp processar clientes.csv`);
  depois, se for útil, uma tela simples (Streamlit/Flask) para subir o CSV e baixar o PDF.
- Credenciais (`VIPP_USUARIO`, `VIPP_TOKEN`, `VIPP_PERFIL`) em variáveis de ambiente / `.env`
  fora do Git.

### Estrutura do repositório

```
jcv_vipp/
  leitor_csv.py      # lê e valida o CSV diário
  mapeamento.py      # CSV → Envio (usa config/mapeamento.yaml)
  vipp_ws.py         # cliente SOAP PostarObjeto / SituacaoPostagem
  arquivo_vipp.py    # gera arquivo de importação (caminho alternativo)
  etiquetas_pdf.py   # monta o PDF de impressão
  controle.py        # SQLite com histórico de envios
  cli.py
config/mapeamento.yaml
tests/
```

## 3. O que precisamos do JCV

1. **Exemplo do CSV diário** (pode ser com dados fictícios, mas com o mesmo cabeçalho, separador e codificação).
2. **Dados do VIPP**: confirmar se há acesso ao Web Service (usuário + token + Id do perfil de
   importação). Não enviar senha pelo chat; vamos configurar como segredo do ambiente.
3. **Serviço dos Correios** usado para os boletos (ex.: Carta Comercial Registrada, Impresso, PAC) e
   se há contrato/cartão de postagem.
4. **Remetente** (dados da JCV que saem na etiqueta).
5. **Formato de impressão**: folha A4 de etiquetas (qual modelo Pimaco?) ou impressora térmica.
