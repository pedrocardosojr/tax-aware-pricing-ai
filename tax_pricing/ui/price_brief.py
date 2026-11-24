"""Prioritize a short pricing brief without handing the calculation to a model."""
import json

from tax_pricing.ui.grounded_explanation import request_answer

# The order is optional: past this, the summary keeps its standard order.
BRIEF_TIMEOUT_SECONDS = 5


def position_insight(result: dict) -> str:
    """Explain how to use the price comparison without repeating the chart."""
    market = result['market']
    position = result['market_position']
    if position is None:
        return 'Compare com o custo e procure preços do mesmo produto antes de se reposicionar.'
    if market['status'] == 'historical_reference':
        return 'A comparação é histórica. Confirme os preços atuais antes de mudar o seu.'
    if market.get('kind') == 'estimated' or market.get('low_precision'):
        return 'Use a referência como ponto de partida e confira preços em outras lojas.'
    gap = position['gap_brl']
    if gap > 0:
        return ('Seu preço está acima do centro do mercado. '
                'Confira se cabe baixar sem perder margem demais.')
    if gap < 0:
        return ('Seu preço já está abaixo do centro do mercado. '
                'Compare a margem antes de baixar mais.')
    return 'Seu preço está no centro do mercado. Use a margem para decidir se vale mudar.'


def promotion_insight(result: dict) -> str:
    """Use the calculated lower market point as a candidate for a promotion."""
    points = result['corridor_points']
    current = result['analysis']['personalized']['margin']['contribution_brl']
    if current <= 0:
        return ('O preço analisado não deixa margem positiva. '
                'Reveja custo e preço antes de dar desconto.')
    if not points:
        return ('Teste um desconto no simulador e confira a margem. '
                'A base atual não sustenta uma promoção de referência.')
    lower = points[0]
    if lower['price_brl'] >= result['evaluated_price_brl']:
        return ('Seu preço já está entre os mais baixos do mercado. '
                'Antes de dar desconto, confira quanto sobra por unidade.')
    if lower['contribution_brl'] <= 0:
        return ('No preço mais baixo comum no mercado, você perderia dinheiro. '
                'Teste um desconto menor no simulador.')
    return ('Teste no simulador o preço mais baixo comum no mercado e veja quanto a mais '
            'você precisaria vender para ganhar o mesmo no total.')


def prioritize_brief(lines: dict[str, str], *, model: str, api_key: str,
                     url: str) -> tuple[str, ...]:
    """Let the LLM set the reading order using the approved insights only."""
    reply = request_answer([
        {'role': 'system', 'content':
         'Ordene os insights de preço do mais urgente ao menos urgente para '
         'um pequeno lojista. Considere risco de perder margem, qualidade da '
         'referência e se faz sentido testar promoção. Responda só com um '
         'array JSON com todas as chaves recebidas, cada uma exatamente uma vez.'},
        {'role': 'user', 'content': json.dumps(lines, ensure_ascii=False)},
    ], model=model, api_key=api_key, url=url, timeout=BRIEF_TIMEOUT_SECONDS)
    try:
        order = json.loads(reply or 'null')
    except ValueError:
        return ()
    if (isinstance(order, list) and all(isinstance(key, str) for key in order)
            and len(order) == len(lines) and set(order) == lines.keys()):
        return tuple(order)
    return ()
