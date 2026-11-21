# Executar e revisar o Streamlit

A versão atual está na branch `main`. O app usa, por padrão, os 50 arquivos
de referência publicados pela equipe. O quadro de resultados, o simulador
e a inteligência de mercado estão no mesmo aplicativo.

## Instalar

Na raiz do repositório, com Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make team-preview
```

Abra a URL local exibida pelo terminal. O endereço padrão é
`http://127.0.0.1:8501`. Esse endereço funciona no computador que está
executando o serviço.

## Atualizar uma cópia existente

Pare o Streamlit com Ctrl+C, entre na pasta do projeto e execute:

```bash
git switch main
git pull --ff-only origin main
python -m pip install -r requirements.txt
make team-preview
```

Ative o ambiente Python do projeto antes dos comandos. Caso
`TAX_PRICING_MARKET_DIR` esteja apontando para uma pasta antiga de teste,
remova essa configuração para usar o lote final versionado.

Na abertura, a versão atual mostra divisórias entre os campos e a opção
**Sugira um preço**. Após analisar, **Editar cenário** permite alterar os
valores e enviar a nova análise.

## Demo com Café Pilão

[Cenário, números, perguntas e validação](cafe_demo_2026-11-19.md).

O custo e o preço usados na demonstração são fictícios. A referência de
mercado é observada, datada e identificada na tela.

## Inteligência de mercado

As variáveis `OPENAI_API_KEY`, `TAX_PRICING_LLM_MODEL` e
`TAX_PRICING_LLM_URL` podem ser configuradas no ambiente ou na raiz dos
Secrets do Streamlit. A configuração do Gemini está no
[README](../README.md#optional-model-connection).
Credenciais devem ficar fora do Git.

O resumo usa textos do cenário e pode ter sua ordem priorizada pelo modelo.
Na seção de perguntas, a busca TF-IDF recupera fontes para o modelo gerar
uma resposta. Os números e as citações passam pela checagem antes da exibição.
Falhas do serviço usam o conteúdo de reserva do app.

## Tributos e dados

A margem usa o perfil demonstrativo de produto e regime.
O detalhe oficial de IBS/CBS depende do RTC em execução, normalmente em
`http://127.0.0.1:8080/api`. Quando ele está indisponível, o painel informa
essa condição. O detalhe do RTC permanece separado da dedução da margem.

A fonte principal usa mediana por loja e um ponto por rede no gráfico.
Em **Detalhes**, o histórico exploratório pode usar outro recorte, com fonte
e período próprios. Cada comparação deve ser lida dentro de sua amostra.

O app publicado está em
[https://tax-pricing-ai.streamlit.app/](https://tax-pricing-ai.streamlit.app/).
O app publicado é aberto: https://tax-pricing-ai.streamlit.app/

## Verificações

```bash
python -m pip install -r requirements-dev.txt
make test lint typecheck
```

Além dos testes automatizados, confira no projetor o gráfico de mercado,
a curva de margem, a composição do preço e uma resposta real com fonte.
A cópia local e as imagens do Café servem como reserva da apresentação.
