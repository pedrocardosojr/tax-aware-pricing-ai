# Piloto de extração de ofertas com LLM

**Decisão de negócio.** Ver se a oferta do concorrente é aplicável a uma
garrafa avulsa e se vale simular acompanhar o preço. O LLM estrutura o
anúncio. O cálculo de margem continua no motor do projeto.

## Desenho do teste

Dez anúncios de dois encartes oficiais do Condor foram transcritos e
conferidos visualmente. A entrada é texto, com link para a página original.
O gabarito foi preparado antes de executar o modelo e fica em arquivo
separado, fora do prompt. Há controles para combo, fidelidade, volume
equivalente, embalagem, variante e produtos de outra marca.

Cada resposta recebe dez checagens exatas. Um JSON inválido recebe zero.
A triagem final exige identidade explícita na descrição, preço unitário
explícito, validade, praça e oferta avulsa sem selo de clube. Confirmação
de EAN e de disponibilidade por loja entram na validação de uma oferta
real. Os dez anúncios são históricos em 10/11/2026. A amostra mede erros
de extração e rejeição de falsos comparáveis, com cobertura insuficiente
para medir a aceitação de ofertas válidas.

## Reprodução

Em um Mac com Apple Silicon e ambiente Python separado do Streamlit:

```bash
python -m pip install mlx-lm==0.32.2
python pesquisas/llm_ofertas_2026-11-10/rodar.py \
  --output /tmp/tax-pricing-llm-ofertas.json
```

Para repetir a rodada com três exemplos sintéticos no prompt, acrescente
`--examples` e escolha outro arquivo de saída.

O modelo padrão é [Qwen2.5-3B-Instruct 4-bit em MLX](https://huggingface.co/mlx-community/Qwen2.5-3B-Instruct-4bit).
O primeiro uso baixa os pesos públicos. O script também aceita uma pasta
local via `--model`. Os resultados do modelo são preservados por anúncio
para conferir cada diferença em relação ao gabarito.

## Resultado local em 10/11

| Medida | Instruções | Instruções + 3 exemplos |
|---|---:|---:|
| Campos exatos | 42/100 | 82/100 |
| Objetos JSON com os campos pedidos | 7/10 | 10/10 |
| Identidade do produto | 3/10 | 8/10 |
| Preço por unidade | 2/10 | 9/10 |
| Mecânica da oferta | 4/10 | 8/10 |
| Selo do clube | 6/10 | 10/10 |
| Ofertas admitidas na referência avulsa atual | 0/10 | 0/10 |

A comparação repete os mesmos dez casos. A métrica exige formato e valor
exatos. Na segunda rodada, todos os campos de praça trouxeram o texto
“Lojas Condor do Paraná” no lugar de “Paraná”. Houve ainda erros de
conteúdo. O modelo reconheceu que a oferta de Natal era combo e de clube,
mas omitiu o preço destacado de R$ 10,49 e retornou uma unidade como
mínimo. Também aceitou como identidade explícita uma Coca-Cola cuja
variante estava ausente. A triagem bloqueou o uso comercial desses casos.

A política foi conferida à parte com uma oferta vigente sintética e
dez variações rejeitadas, incluindo combo, clube, embalagem diferente,
outra praça, dado vencido e preços ausentes ou com tipo incorreto.
Esse teste de política não mede a habilidade do modelo de reconhecer
ofertas vigentes reais.

## Ensaio do texto para a tela

Em uma chamada adicional, o mesmo Qwen recebeu só os fatos verificados
e os números calculados pelo app. A resposta está em
[`briefing_gerado.json`](briefing_gerado.json). Ela preservou a validade
vencida do combo e os 58,2% de volume adicional. Também extrapolou
“nenhuma oferta avulsa vigente validada nesta amostra” para “não há
oferta avulsa disponível”, omitiu os dois preços da simulação e usou
quatro frases. A resposta fica como evidência de avaliação. A próxima
versão deve exigir fonte por afirmação e manter literalmente os limites
de cobertura antes de mostrar texto gerado no Streamlit.

[Encarte oficial](https://institucional.condor.com.br/wp-content/uploads/2025/02/NATAL_CONDOR_08-12_A_24-12-2025_PR.pdf#page=20)
· [Consulta de IPCA usada no contexto](https://servicodados.ibge.gov.br/api/v3/agregados/7060/periodos/202609/variaveis/63?localidades=N7%5B4101%5D&classificacao=315%5B107621%5D)

## Próximo teste

Usar encartes de redes diferentes, com exemplos positivos vigentes e
preço avulso, além de casos com loja restrita e limite de quantidade.
Comparar um modelo multimodal usando a página original com o modelo
de texto usando OCR. Medir acerto dos campos críticos, aceites indevidos
e cobertura das ofertas válidas antes de colocar o extrator na tela.

Para o resultado do Streamlit, testar o texto gerado com evidências
validadas, IDs das fontes, preços, datas e números calculados pelo motor.
O primeiro caso de demo é Coca-Cola 2 L. Para Café Pilão 500 g, acrescentar
o contexto regional de categoria do Deral e a variação do IPCA de
Curitiba, com as respectivas datas e unidade de medida.
