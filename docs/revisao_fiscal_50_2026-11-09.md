# Carteira de 50 SKUs — revisão dos cenários tributários

Os outros 48 SKUs foram incorporados à configuração: **50 produtos, 14 NCMs,
três regimes e 150 combinações**. Cada EAN tem NCM esperado, condições e fontes.
É uma revisão técnica dos cenários demonstrativos de novembro de 2026;
não confirma a apuração de uma empresa nem os dados de uma nota fiscal.

Os inputs continuam grupo, produto, regime, custo e preço praticado ou sugestão.
Nenhuma alíquota, faturamento, crédito ou meta de margem foi adicionada à tela.

## Famílias e diferenças que afetam a conta

| Família | SKUs | ICMS da revenda no cenário regular | PIS/Cofins no cenário regular |
|---|---:|---|---|
| Arroz, feijão, macarrão seco, açúcar e café | 29 | Isenção da venda interna PR ao consumidor final, condicionada à descrição | Zero protegido da redução linear |
| Leite UHT integral 1 L | 5 | ST já retida na compra; não confundir com isenção da cesta estadual | Zero protegido |
| Óleo refinado de soja | 4 | Isenção estadual condicionada | Redução linear do benefício: 10% das taxas comuns |
| Refrigerantes e cervejas | 8 | ST já retida na compra | Zero específico do varejista habilitado à regra |
| Água mineral natural | 2 | ST já retida na compra | Taxas comuns; exceção à regra de bebidas frias |
| Creme dental e sabonete de toucador | 2 | ST já retida na compra | Redução linear do benefício: 10% das taxas comuns |

“ST já retida” é uma condição fictícia da compra. Quando usada, o imposto
retido permanece no custo bruto. Não há outro débito ordinário da mesma ST
na revenda. Restituição, complemento e incentivos especiais não são simulados.

### Federal: alimento protegido e óleo de soja são diferentes

A [Lei 10.925/2004, art. 1](https://www2.camara.leg.br/legin/fed/lei/2004/lei-10925-23-julho-2004-533112-normaatualizada-pl.html)
é cruzada com a [LC 224/2025, art. 4](https://www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-224-26-dezembro-2025-798608-normaatualizada-pl.html)
e os [anexos da LC 214/2025](https://www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-214-16-janeiro-2025-796905-normaatualizada-pl.html).
Alimentos do Anexo I continuam protegidos no recorte analisado. Óleo de soja
está no Anexo VII, não nessa exceção. Higiene também não é alimento protegido.

Nos casos de redução linear configurados, PIS/Cofins ficam em 0,065%/0,30%
no Presumido e 0,165%/0,76% no Real. A regra não cria créditos antes vedados.
Isso não é a redução de 60% de IBS/CBS do RTC: são tributos e bases distintos.

### Água: a descrição e o Ex da TIPI mudam a regra

A [Lei 13.097/2015, art. 14 II e arts. 28–29](https://www2.camara.leg.br/legin/fed/lei/2015/lei-13097-19-janeiro-2015-780071-normaatualizada-pl.html)
exclui os Ex01/Ex02 de água mineral natural. A [orientação classificatória
oficial](https://normas.receita.fazenda.gov.br/sijut2consulta/anexoOutros.action?idArquivoBinario=69369)
distingue as capacidades de recipiente. Para os dois SKUs de água natural,
o cenário usa contribuições comuns (0,65%/3% ou 1,65%/7,6%) e não retira a
parcela federal do DAS. O rótulo precisa confirmar a descrição assumida.

Para refrigerantes e cervejas, a condição de varejista e o tratamento específico
seguem documentados; não se generaliza para fabricante, importador ou atacadista.
A página geral da Receita sobre supermercados é apoio; o enquadramento da água
foi separado pela exceção expressa da lei, mesmo que uma lista geral mencione água.

### ICMS do Paraná e Simples

A [Lei PR 14.978/2005](https://www.legislacao.pr.gov.br/legislacao/pesquisarAto.do?action=exibirImpressao&codAto=284)
orienta as saídas alimentares isentas. UHT está expressamente fora da isenção.
O [RICMS/PR, Anexo IX, arts. 121–122](https://www.sefanet.pr.gov.br/dados/SEFADOCUMENTOS/106201707871.pdf)
traz o tratamento de ST do leite UHT; o cenário pressupõe retenção anterior.
A apresentação e a compra reais continuam exigindo confirmação.

O perfil fictício do Simples tem RBT12 de R$360 mil. Pela [Lei PR
15.562/2007, art. 2](https://www.legislacao.pr.gov.br/legislacao/exibirAto.do?action=iniciarProcesso&codAto=553&codItemAto=31414),
retira-se a parcela de ICMS nessa faixa. Ela não é retirada duas vezes quando
há ST. O DAS demonstrativo fica em 3,729%; para as oito bebidas com regra
federal específica, 2,85325%. Isenção ordinária fora do Simples não autoriza
retirar também PIS/Cofins do DAS. A mudança de faturamento exige outra revisão.

## Créditos, exclusões e pontos condicionais

- Compra bruta preservada. O cenário não inventa crédito porque a venda tem
  imposto. Nos alimentos isentos/protegidos e na revenda de bebidas elegíveis,
  não se presume um crédito ordinário recuperável.
- **Água no Real:** crédito de PIS/Cofins eventualmente elegível não foi
  reconstruído sem NF-e. O cenário conservador sem crédito é uma hipótese,
  não uma proibição legal de todo crédito desse produto.
- Higiene e água: a parcela documental de ICMS-ST para exclusão da base das
  contribuições é fictícia, 10% do custo. Não é alíquota legal nem crédito.
  A referência é o Tema 1125 do STJ; o documento real pode mudar essa parcela.
- Sabonete Protex: assume-se sabão de toucador Ex01, não qualquer mercadoria
  no mesmo NCM. Conferir composição/rótulo e documento antes de uso fiscal real.
- Arroz: a regra estadual exige descrição elegível. A inclusão do parboilizado
  no cenário é condicional; não foi encontrada consulta específica do PR que
  homologue esses três EANs. Não importar interpretações de outro estado.
- Cervejas: confirmar lata/long neck para pauta/ST real. A revisão de tributos
  não atualiza os preços históricos nem resolve a falta de observações recentes.
- O DAS inclui parcelas diferentes do recorte ICMS/PIS/Cofins dos outros
  regimes. Não usar a tabela para recomendar o “melhor regime” ou lucro líquido.

## Evidência e reprodução

A [matriz de 150 combinações](../evidencias/revisao_fiscal_50_2026-11-09/matrix_150.csv)
contém produto, EAN, NCM, regime, taxas em fração, condições e fontes.
Os [300 cálculos conciliados](../evidencias/revisao_fiscal_50_2026-11-09/arithmetic_300.csv)
usam custo R$8 e preços R$6/R$12 **inteiramente fictícios**, para conferir
contribuição negativa e positiva. Não são novos preços de mercado.

```sh
python -m scripts.audit_tax_catalog
make test lint typecheck
```

O manifesto registra hashes do catálogo e das configurações. A nota de pesquisa
registra a versão e o hash do PDF estadual consultado. **118 testes aprovados,
pylint 10/10, mypy sem erros em 39 arquivos.** Há testes de cobertura dos 50,
EAN/NCM divergente, data, famílias, água, sabonete, curvas e interface.

Esta etapa não fez chamadas à API RTC e não altera as evidências anteriores
50/50. Os 12 exemplos anteriores com preços observados de Coca/Sorriso seguem
separados. IBS/CBS retornados pelo RTC não são somados como imposto pago sem
regra de transição correspondente. Falta aceite/reprodução por colega antes
de merge; revisão conjunta do output e histórico/similares continuam na fila.
