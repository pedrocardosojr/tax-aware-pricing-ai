# MVP: mercado, tributação estimada e margem de contribuição

Decisão final de Pedro em 07/11/2026. O objetivo é ajudar a posicionar o SKU
frente aos concorrentes e interpretar seu resultado comercial. O MVP usa
perfis fiscais demonstrativos configurados internamente. A personalização
fiscal completa fica como evolução, substituindo o recorte intermediário
de exigir dados adicionais da empresa nesta primeira versão.

## O usuário informa

1. Grupo de produtos.
2. Produto/apresentação.
3. Regime: Simples Nacional, Lucro Presumido ou Lucro Real.
4. Custo de aquisição.
5. Preço praticado **ou** escolha de receber uma sugestão de corredor.

Não há meta de margem no input. Faturamento, alíquotas, créditos e despesas
do cenário vêm da configuração interna, sem cadastro fiscal adicional no MVP.
O regime é obrigatório e altera efetivamente as parcelas usadas na conta.

## O que fica interno

| Informação | Origem |
|---|---|
| Descrição, EAN, NCM, grupo e embalagem | Catálogo dos 50 produtos; enquadramentos fiscais continuam candidatos revisáveis |
| Competência, Curitiba/PR e data fiscal | Configuração do cenário de 2026, exibida no resultado |
| Faturamento/anexo nominal e dedução do perfil Simples | Empresa hipotética configurada; cálculo da taxa efetiva pela fórmula já implementada |
| Taxas, crédito e despesas dos três regimes | Premissas demonstrativas versionadas, não alíquotas personalizadas da empresa |
| IBS/CBS do cenário | Motor oficial RTC, quando disponível, sob base/classificação explícitas; separado da dedução usada na margem |
| Mediana, faixa, redes, datas e histórico | Saída de mercado de Edu/Rodrigo, preservando origem observada ou estimada |
| Contribuição, price index e diferenças de preço | Funções de cálculo, sem novos campos para o usuário |
| Resumo dos resultados | Texto por regras sobre os números calculados; LLM pode ser avaliado depois |

Os perfis iniciais usam despesas de 5% + R$ 0,50 por unidade e crédito
hipotético de compra de 5% no perfil Real, zero nos outros. O Simples usa
RBT12 fictícia de R$ 360 mil, nominal de 7,3% e dedução de R$ 5.940. Todas
essas premissas estão no arquivo `dados/tributos/perfis_demo_mvp.json`.
Não representam enquadramento ou benefício real do produto/empresa.
A base usada no RTC é o preço avaliado por convenção demonstrativa, sem
afirmar que essa conversão represente uma operação fiscal real.

## Como apresentar o resultado

- **Margem de contribuição:** R$ e %, com a nota curta “Calculada com a
  tributação estimada e as despesas do cenário”. Não chamar de lucro líquido.
- **Tributação estimada:** componentes e contexto do perfil demonstrativo.
- **Meu produto no mercado:** referência, posição do preço, faixa e cobertura.
- **Cenários de preço:** faixa observada e contribuição nos pontos avaliados.
- **Premissas:** acesso simples às hipóteses, data, fonte e modo demonstrativo.

O detalhe fiscal do contribuinte não deve ser apresentado como conhecido.
A nota de demonstração fica acessível junto aos resultados, sem acrescentar
perguntas ao fluxo principal.

## Corredor inicial para teste

O protótipo usa P25/P75 dos preços comparáveis do mesmo SKU e calcula a
contribuição nos pontos disponíveis, com referência central na mediana.
Não declara preço ótimo nem margem alvo. Limites em centavos permanecem
dentro da faixa observada; pontos iguais não são duplicados.

Os parâmetros iniciais de teste são pelo menos três redes e referência com
até 60 dias em relação à data do cenário. São critérios operacionais
ajustáveis, sem garantia estatística. Dados antigos, insuficientes ou apenas
estimados não geram um corredor atual apresentado como observado.

Sem preço informado e sem referência adequada, a dependência é da base de
mercado: não inventar preço nem pedir campos fiscais extras ao usuário.
Similares e histórico ampliado continuam na integração com Edu/Rodrigo.

## Implementação e validação

Entrada da tela: `tax_pricing.mvp_analysis.analyze_mvp`. Recebe os inputs
acima e um resumo interno do mercado. Os contratos personalizados anteriores
ficam preservados para evolução, fora da coleta obrigatória deste MVP.

Há testes dos três perfis e dos dois caminhos, dados de mercado ausentes,
antigos/estimados, grupo/SKU incompatível e pontos repetidos na faixa. A suíte
também percorre os 50 SKUs nos três regimes com o RTC simulado como indisponível,
sem transformar indisponibilidade em imposto zero. A validação real dos
50 produtos no RTC novo permanece nas evidências da entrega anterior.
