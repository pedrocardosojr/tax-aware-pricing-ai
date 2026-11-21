# Revisão dos três perfis e dois exemplos — 09/11/2026

> Ampliada: [revisão dos 50 SKUs e matriz por regime](revisao_fiscal_50_2026-11-09.md).
> Os exemplos abaixo continuam como contas detalhadas de Coca/Sorriso.

**Entrega:** os três regimes foram revistos para os exemplos de Coca-Cola 2 L
e Sorriso 70 g. Foram gerados 12 cenários conciliados: dois produtos, três
regimes e os dois caminhos de preço. O ajuste é uma proposta para revisão;
não é apuração de uma empresa real nem homologação fiscal dos 50 produtos.

## Condições internas dos exemplos

Varejista de Curitiba, operação interna para consumidor final, sem fabricação
ou importação. A compra tem ICMS-ST já recolhido e incluído no custo bruto
informado. Não se simula restituição, complemento de ST ou crédito recuperável
dessas aquisições. A Coca pressupõe o critério de varejista da lei específica.
As condições são fictícias e visíveis; não foram conferidas em uma NF-e.

Isso permite manter os inputs aprovados. Não adicionamos perguntas ao usuário.
Condições diferentes exigem outra regra, e não uma correção improvisada na margem.

## O que mudou

| Item | Antes | Proposta |
|---|---|---|
| Regra fiscal do produto | Perfil genérico para qualquer SKU | Dois exemplos com receitas próprias e condições explícitas |
| ICMS dos exemplos | Novo débito na revenda e crédito presumido da compra | ST já no custo; nenhum novo débito ou crédito ordinário nesse cenário |
| Bebida / PIS-Cofins | Alíquotas gerais | Regra do varejista de bebidas frias, sem crédito da bebida |
| Dentifrício / PIS-Cofins | Alíquotas gerais | Tratamento de higiene bucal com o efeito da redução linear de 2026 |
| Simples | DAS integral em ambos | Segregação distinta por produto, preservando a faixa de receita demonstrativa |
| Crédito genérico normal | Soma direta de ICMS + PIS/Cofins sobre o custo inteiro | Base sem ICMS para a parcela PIS/Cofins, quando hipoteticamente elegível |
| Curva e sensibilidade | Recriavam o perfil genérico | Reutilizam a regra do produto da análise principal |

O perfil genérico passa a usar 19,5% como referência **modal** do Paraná.
Isso não determina a alíquota específica de cada SKU. A ampliação para os
50 produtos está no guia vinculado acima, com condições por família. Para uma compra normal
fictícia elegível, o crédito no Real fica 19,5% + 80,5% × 9,25% = 26,94625%
do custo bruto. Para os dois exemplos com as condições acima, o crédito é zero.

Para o Sorriso, a exclusão de ICMS-ST da base PIS/Cofins segue o
[Tema 1125 do STJ](https://processo.stj.jus.br/repetitivos/temas_repetitivos/pesquisa.jsp?cod_tema_final=1125&cod_tema_inicial=1125&novaConsulta=true&tipo_pesquisa=T).
O valor documental é **simulado como 10% do custo bruto**, R$0,15 neste exemplo,
e não é uma alíquota legal. A base das contribuições fica R$3,84; os R$0,15
continuam dentro do custo R$1,50. Exclusão de base não é crédito de compra.
O piso de preço agora é encontrado por centavos na própria função de margem,
preservando essa exclusão também na curva e nas mudanças de custo.

## Fontes e interpretação aplicada ao cenário

- **Paraná:** a [pauta oficial de bebidas](https://www.fazenda.pr.gov.br/Pagina/Pauta-de-bebidas)
  contém atos de ICMS-ST para 2026. A [Resolução SEFA 1245/2025](https://www.legislacao.pr.gov.br/legislacao/listarAtosAno.do?action=exibirImpressao&codAto=381258)
  lista dentifrícios NCM 3306.10.00 / CEST 20.023.00 na tabela de MVA, com efeitos
  em abril de 2026. Essas referências não provam retenção na compra de um usuário.
- A [referência modal de 19,5%](https://www.legislacao.pr.gov.br/legislacao/exibirAto.do?action=iniciarProcesso&codAto=321803&codItemAto=2038037)
  vem do Decreto 5.143/2024, alteração 933, efeitos em 18/03/2024. Não aplicamos
  essa taxa como novo ICMS dos dois exemplos com ST assumida.
- **Bebidas:** [Lei 13.097/2015, arts. 17, 28 e 29](https://www2.camara.leg.br/legin/fed/lei/2015/lei-13097-19-janeiro-2015-780071-normaatualizada-pl.html):
  definição do varejista, redução na sua revenda, inclusão expressa do Simples e
  vedação do crédito da bebida revendida nesse tratamento. A [orientação atual
  da Receita para supermercados](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/restituicao-ressarcimento-reembolso-e-compensacao/conformidade-tributaria/Creditos-Indevidos-de-PIS-Pasep-Cofins-Setor-Supermercadista)
  distingue varejista de atacadista. Essa condição é assumida no exemplo.
- **Dentifrício:** [Lei 10.925/2004, art. 1º, XXVII](https://www2.camara.leg.br/legin/fed/lei/2004/lei-10925-23-julho-2004-533112-normaatualizada-pl.html)
  trata higiene bucal. Não o classificamos automaticamente como monofásico.
  A [LC 224/2025, art. 4º](https://www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-224-26-dezembro-2025-798608-normaatualizada-pl.html)
  inclui o benefício e define 10% das taxas padrão para o caso de alíquota zero
  alcançado pelo corte. Sob as condições do exemplo, o cenário de novembro usa
  PIS/Cofins de 0,065%/0,30% no cumulativo e 0,165%/0,76% no não cumulativo.
  O §7º não cria crédito anteriormente vedado. Exceções precisam ser verificadas
  para uso real. Higiene bucal não é a cesta **alimentar** protegida por esse artigo.
- **Simples:** [LC 123/2006, Anexo I e art. 24](https://www2.camara.leg.br/legin/fed/leicom/2006/leicomplementar-123-14-dezembro-2006-548099-normaatualizada-pl.html)
  e [Resolução CGSN 140, art. 25](https://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idAto=92278).
  Receita fictícia de R$360 mil: taxa efetiva inicial de 5,65%. Na hipótese ST,
  retiramos a parcela ICMS da faixa. Para a Coca, há ainda a regra federal expressa
  da bebida; para Sorriso, não transferimos o benefício comum para o DAS.
  Resultados do cenário: **2,85325%** e **3,729%**, respectivamente.

Os links e condições estão versionados em `dados/tributos/revisao_2026_11.json`.
Essa configuração é limitada a novembro/2026 e falha explicitamente se a data
ou o NCM do exemplo mudar. Uma interpretação aplicável a uma compra fictícia
não é uma conclusão sobre qualquer contribuinte com aquele regime ou NCM.

## Exemplo 1 — Coca-Cola 2 L

**Custo fictício: R$8,00; preço informado: R$12,00.** Mercado observado da
equipe: mediana R$11,85 em 15 redes, janela ago–out/2026, última coleta 01/10.
Despesas fictícias: 5% da venda + R$0,50 por unidade = R$1,10.

| Regime | Tributos adicionais da revenda no cenário | Crédito | Contribuição/un. | Margem |
|---|---:|---:|---:|---:|
| Simples | R$0,34 | R$0,00 | R$2,56 | 21,31% |
| Presumido | R$0,00 | R$0,00 | R$2,90 | 24,17% |
| Real | R$0,00 | R$0,00 | R$2,90 | 24,17% |

Zero nessa coluna **não significa carga total zero**: a aquisição inclui os
tributos embutidos. Eles permanecem nos R$8,00 e não são descontados novamente.
Presumido e Real podem coincidir neste recorte, sem que um seja o regime ideal.

## Exemplo 2 — Sorriso 70 g

**Custo fictício: R$1,50; preço informado: R$3,99.** Mercado observado da
equipe: mediana R$3,39 em 14 redes, mesma janela e última coleta. Despesas
fictícias: R$0,6995, exibidas como R$0,70.

| Regime | Tributos da revenda no cenário | Crédito | Contribuição/un. | Margem |
|---|---:|---:|---:|---:|
| Simples | R$0,15 | R$0,00 | R$1,64 | 41,15% |
| Presumido | R$0,01 | R$0,00 | R$1,78 | 44,52% |
| Real | R$0,04 | R$0,00 | R$1,75 | 43,98% |

Os valores internos mantêm a precisão e a tabela arredonda apenas para exibir.
A soma visual de parcelas arredondadas pode diferir em um centavo.

## Como repetir e conferir

```bash
python -m scripts.demo_reviewed_tax
make test lint typecheck
make team-preview
```

Os arquivos `evidencias/revisao_fiscal_2026-11-09/examples.json` e `examples.csv`
contêm também o caminho de sugestão (medianas R$11,85 e R$3,39), componentes,
créditos, composição, price index, piso e sensibilidade. O manifesto identifica
valores fictícios, condições assumidas e hashes das configurações.

Conciliação de cada exemplo:
`venda - custo bruto + crédito elegível - tributos da revenda - despesas`.
Os 12 casos verificam a identidade e o primeiro centavo de contribuição não
negativa. Curva e sensibilidade mantêm a mesma regra do produto.

Validação: **113 testes aprovados, pylint 10/10 e mypy sem erros em 38
arquivos**, no ambiente limpo da integração (Streamlit 1.65.0). Inclui regra
por produto, condição temporal, NCM divergente, crédito, exclusão de base,
contribuição negativa e piso por centavos. Os testes de tela continuam passando
nos três regimes e nos dois caminhos do Sorriso.

O gerador é **offline**: o detalhe RTC fica explicitamente indisponível; não
foi tratado como imposto zero. As evidências anteriores de 50/50 testes RTC
permanecem preservadas e não foram reexecutadas nesta entrega. IBS/CBS do motor
não são somados automaticamente aos tributos efetivamente deduzidos da margem.

## O que permanece aberto

- Confirmação fiscal das condições de uma empresa real, especialmente
  documentação de compra, exceções e complementos. A revisão demonstrativa
  dos outros 48 produtos foi concluída no guia da carteira completa.
- Aceite dos cenários pelo grupo. Eles não comparam carga total ou lucro líquido
  entre regimes: o DAS inclui parcelas diferentes do recorte ICMS/PIS/Cofins;
  IRPJ/CSLL do Presumido/Real não foram rateados por unidade.
- Revisão conjunta do output (item 3) e integração de histórico/similares (item 4).
  Esta proposta só acrescenta condições e fontes ao expander de premissas já
  existente; não redesenha a experiência ou os gráficos.
