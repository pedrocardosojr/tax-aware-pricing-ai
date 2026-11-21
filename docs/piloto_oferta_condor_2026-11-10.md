# Piloto de leitura de oferta do Condor

## Evidência conferida em 10/11/2026

A página 20 do [encarte de Natal do Condor](https://institucional.condor.com.br/wp-content/uploads/2025/02/NATAL_CONDOR_08-12_A_24-12-2025_PR.pdf#page=20)
mostra Coca-Cola Tradicional PET 2 L e Coca-Cola Zero Açúcar PET 2 L em
um combo de R$ 20,38. O selo identifica Cliente Clube Condor. O cabeçalho
da página impressa informa validade de 08 a 24/12/2025 para as lojas
Condor do Paraná, incluindo Curitiba, com packs exclusivos de lojas
físicas. A leitura visual confirmou essas condições. A extração inicial
do texto indicava 09/12 e não preservava o selo do Clube.

O anúncio destaca R$ 10,49 na condição do combo. O preço de uma
Tradicional comprada sozinha fica sem evidência nesse anúncio. Dividir
o total por dois daria R$ 10,19 como média das garrafas do combo,
sem estabelecer o preço individual da Tradicional. O vínculo ao EAN
7894900027013 do catálogo é por descrição, variante e apresentação;
o encarte não imprime o código de barras.

**Uso no piloto:** registro histórico de uma oferta condicionada. O
preço anunciado fica fora da mediana de mercado e serve apenas para
simulação. A página 17 do [encarte Condor nº 148](https://institucional.condor.com.br/wp-content/uploads/2025/02/148_TAB_GERAL_PR-1.pdf#page=17)
também foi conferida como controle de identidade. Nesse anúncio, a Coca-Cola
2 L vem com Fanta Guaraná, enquanto o preço unitário de Coca-Cola na mesma
página se refere à lata de 310 ml.

## Simulação com as premissas do MVP

No Lucro Real demonstrativo, com custo de aquisição de R$ 7,00, o motor
recalculou a contribuição por unidade se o lojista escolhesse igualar
o preço destacado de R$ 10,49 para uma garrafa Tradicional. A simulação
mantém as mesmas despesas variáveis e premissas fiscais do preço de
partida de R$ 12,00. O RTC foi simulado indisponível no teste.

| Indicador | Preço de partida | Preço simulado |
|---|---:|---:|
| Venda por unidade | R$ 12,00 | R$ 10,49 |
| Contribuição por unidade | R$ 3,90 | R$ 2,47 |

Para preservar a contribuição total, seriam necessárias **58,2% mais
unidades**. O cálculo usa os valores exatos antes do arredondamento
visual. A demanda e a margem do combo dependem de dados adicionais.
Uma oferta avulsa e vigente em Curitiba segue sem confirmação neste
piloto.

### Reprodução

A partir da raiz do repositório, com as dependências do projeto:

```python
from decimal import Decimal
from unittest.mock import patch

from tax_pricing.mvp_analysis import analyze_mvp

inputs = {
    'ean': '7894900027013',
    'regime': 'lucro_real',
    'acquisition_cost': '7',
}
with patch('tax_pricing.product_analysis.calculate_current_tax',
           side_effect=RuntimeError('RTC indisponível no ensaio')):
    current, simulated = (
        analyze_mvp({**inputs, 'selling_price': price})['analysis']
        ['personalized']['margin']['contribution_brl']
        for price in ('12.00', '10.49')
    )

extra_volume_percent = (current / simulated - 1) * 100
assert current == Decimal('3.90')
assert simulated == Decimal('2.4655')
assert extra_volume_percent.quantize(Decimal('.1')) == Decimal('58.2')
```
