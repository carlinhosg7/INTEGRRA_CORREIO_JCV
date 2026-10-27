# Integração JCV × Correios (VIPP)

Gera os envios de boletos no VIPP (Visualset) a partir do relatório diário de clientes
(`RELATORIO.CSV`, separador `;`, codificação Latin-1).

Arquitetura e levantamento do VIPP: [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## Uso

```bash
# valida o relatório e gera o arquivo de importação + relatório de erros em ./saida
python -m jcv_vipp RELATORIO.CSV --servico <codigo_servico_ect> --peso 20

# uma etiqueta por imóvel em vez de uma por cliente
python -m jcv_vipp RELATORIO.CSV --agrupar imovel

# registra cada envio direto no Web Service do VIPP
export VIPP_USUARIO=... VIPP_TOKEN=... VIPP_PERFIL=... VIPP_SERVICO=...
python -m jcv_vipp RELATORIO.CSV --postar
```

Arquivos gerados em `saida/`:

- `importacao_vipp_AAAAMMDD.csv`: envios válidos, para importar no VIPP.
- `relatorio_erros_AAAAMMDD.csv`: envios não enviados (erro) ou enviados com ajuste (aviso).
- `controle_envios.sqlite`: histórico do `--postar`; um envio já postado não é postado de novo.

## Regras aplicadas ao relatório

- O relatório repete o cliente uma vez por sócio e por imóvel; as linhas são juntadas em um envio
  por cliente e endereço (ou por imóvel, com `--agrupar imovel`). Os imóveis vão na observação da etiqueta.
- Erro (não envia): CEP sem 8 dígitos, UF inválida, cidade, endereço, nome ou código vazios.
- Aviso (envia com ajuste): CEP de 5 dígitos completado com `000`, número vazio vira `S/N`,
  complemento digitado no campo número vai para o complemento, textos longos cortados no limite da etiqueta.

## Perfil de importação no VIPP

Em *Cadastros > Perfil (Modelo) de Importação*, layout **Personalizado**, separador `;`,
ignorar cabeçalho, com as colunas na ordem de `COLUNAS_VIPP` em `jcv_vipp/exportar.py`.
Marque *Etiquetar* e *Liberar registro após etiquetar*.

## Testes

```bash
pip install pytest
python -m pytest
```

Os dados reais de clientes não são versionados (veja `.gitignore`).
