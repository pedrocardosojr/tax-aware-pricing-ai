"""Retrieve supported pricing questions and explain the checked scenario."""
from collections import Counter
from decimal import Decimal
from math import log, sqrt
import re
from unicodedata import normalize

from tax_pricing.pricing_scenarios import volume_scenario
from tax_pricing.ui.formatting import brl_markdown, display_date, network_name, percent
from tax_pricing.ui.reading import decision_text

TOPICS = {
    'promotion': (
        'vale acompanhar fazer promoção oferta desconto baixar reduzir preço '
        'empatar concorrente vender a mais volume unidades baratear corte'),
    'market': (
        'estou caro barato mercado concorrência comparação mediana referência '
        'redes posição posicionamento índice preço'),
    'margin': (
        'quanto sobra margem contribuição lucro ganhar ganho retorno '
        'por unidade cobre custos prejuízo rentável'),
    'tax': (
        'imposto tributação tributo icms substituição icms-st pis cofins '
        'alíquota fiscal zerado simples presumido real'),
}

PRICE_CHANGE = re.compile(
    r'\b(?:e se|simul\w*|vender|vendesse|cobr\w*|baix\w*|sub\w*|'
    r'aument\w*|reduz\w*|diminu\w*)\b')
AMOUNT = re.compile(
    r'(?:\b(por|para|a|em)\s+)?(?:r\$\s*([+-]?\d[\d.,]*)'
    r'|(?<=\s)([+-]?\d[\d.,]*))(?:\s*(%))?')
PROMOTION = re.compile(r'\b(?:promoc\w*|oferta\w*|desconto\w*)\b')
OCCASION = re.compile(r'\b(?:natal|pascoa|carnaval|black friday|ano novo)\b')
CURRENCY = re.compile(r'r\s*\$')
RELATIVE = re.compile(
    r'\b(baix\w*|reduz\w*|sub\w*|aument\w*|diminu\w*)\b'
    r'(?:\s+(?:(?:o|meu)\s+)?preco)?\s*$')
DISCOUNT = re.compile(r'\b(?:dar|aplicar)\s*$')
PRICE = re.compile(r'(?:\d{1,10}|\d{1,3}(?:\.\d{3}){1,3})(?:,\d{1,2})?')
DOT_PRICE = re.compile(r'\d{1,10}\.\d{1,2}')
PERCENT_CHANGE = re.compile(r'(\d{1,2}(?:,\d{1,2})?)\s*%')
LOWER_WORDS = re.compile(r'\b(?:desconto|baix\w*|reduz\w*|diminu\w*)\b')
HIGHER_WORDS = re.compile(r'\b(?:sub\w*|aument\w*|reajust\w*)\b')
LAST_COLLECTION = re.compile(r'\b(?:ultima coleta|data da coleta|quando\b.*\bcolet\w*|'
                             r'atualizad\w*)')
STORE_COUNT = re.compile(r'\bquant[ao]s (?:lojas|redes|mercados|supermercados)\b')
NETWORK_RANK = re.compile(r'\b(?:rede|loja|mercado|supermercado)s?\b.*\bmais (?:barat|car)\w*')
MEDIAN_MEANING = re.compile(r'\b(?:o que (?:e|significa)|como funciona)\b.*\bmediana\b')
MARGIN_MEANING = re.compile(r'\b(?:por ?que|como|o que (?:e|significa))\b.*'
                            r'\b(?:margem|contribuicao)\b')
BEST_PRICE = re.compile(r'\b(?:melhor|ideal|otimo|certo|correto)\b.*\bpreco\b|'
                        r'\bpreco\b.*\b(?:ideal|otimo|certo|correto)\b')
RAISE_ASK = re.compile(r'\b(?:posso|devo|vale|da pra|consigo|e se)\b.*\b(?:sub\w*|aument\w*)\b')


STOP_WORDS = frozenset((
    'qual', 'quais', 'como', 'esta', 'esse', 'essa', 'isso', 'para', 'por',
    'uma', 'uns', 'das', 'dos', 'com', 'que', 'meu', 'minha', 'seu', 'sobre',
    'quanto', 'produto', 'vale',
))

SUGGESTED_QUESTIONS = ('Estou caro?', 'Vale acompanhar uma promoção?',
                       'Qual a minha margem por unidade?', 'Quanto pago de imposto?')


def _tokens(text: str) -> Counter[str]:
    """Normalize accents and discard short words and common query scaffolding."""
    normalized = normalize('NFKD', text.casefold()).encode('ascii', 'ignore')
    return Counter(word for word in re.findall(r'[a-z]{3,}', normalized.decode())
                   if word not in STOP_WORDS)


DOCUMENTS = {topic: _tokens(text) for topic, text in TOPICS.items()}
IDF = {term: 1 + log((1 + len(DOCUMENTS)) /
                     (1 + sum(term in doc for doc in DOCUMENTS.values())))
       for term in set().union(*DOCUMENTS.values())}


def _weights(tokens: Counter[str]) -> dict[str, float]:
    """Weight terms by count and inverse document frequency."""
    return {term: count * IDF.get(term, 1 + log(1 + len(DOCUMENTS)))
            for term, count in tokens.items()}


def match_topic(question: str) -> str | None:
    """Rank topics by cosine similarity and abstain on weak or close matches."""
    query = _weights(_tokens(question))
    if not query:
        return None
    length = sqrt(sum(weight ** 2 for weight in query.values()))
    scores = []
    for topic, document in DOCUMENTS.items():
        terms = _weights(document)
        dot = sum(weight * terms.get(term, 0.0)
                  for term, weight in query.items())
        norm = sqrt(sum(weight ** 2 for weight in terms.values()))
        scores.append((dot / (length * norm), topic))
    best, second = sorted(scores, reverse=True)[:2]
    if best[0] < 0.13 or best[0] - second[0] < 0.04:
        return None
    return best[1]


def _promotion_answer(result: dict) -> str:
    """Compare the first observed band point with the evaluated contribution."""
    points = result['corridor_points']
    if not points:
        return ('Para testar um desconto com referência ao mercado, precisamos '
                'de uma faixa observada dentro da janela e com cobertura '
                'suficiente. Confira a data e a amostra na aba de mercado.')
    lower = points[0]
    price = lower['price_brl']
    if price >= result['evaluated_price_brl']:
        return ('Seu preço avaliado já está no limite inferior da faixa '
                f'central observada ou abaixo dele ({brl_markdown(price)}). '
                'Essa referência não fornece um cenário de redução.')
    current = result['analysis']['personalized']['margin']['contribution_brl']
    discounted = lower['contribution_brl']
    context = (f'No limite inferior da faixa central ({brl_markdown(price)}), '
               f'a contribuição seria de {brl_markdown(discounted)} por unidade, '
               f'ante {brl_markdown(current)} no preço avaliado. ')
    if discounted <= 0:
        return context + ('Nesse preço, vender mais não gera contribuição '
                          'positiva. Revise o custo e o preço.')
    extra = (current / discounted - 1) * Decimal(100)
    return (context + f'Para manter a mesma contribuição total, seria preciso '
            f'vender {percent(extra)} a mais. É uma simulação com as '
            'premissas atuais. A faixa observada não identifica promoções e '
            'o app não estima a reação da demanda.')


def _proposed_price(question: str, current: Decimal) -> Decimal | None:
    """Read one absolute price or one explicitly signed price change."""
    proposals = []
    for match in AMOUNT.finditer(question):
        cue, currency, bare, percentage = match.groups()
        if not (cue or currency):
            continue
        amount = (currency or bare).removesuffix('.')
        if percentage:
            return None
        if PRICE.fullmatch(amount):
            value = Decimal(amount.replace('.', '').replace(',', '.'))
        elif DOT_PRICE.fullmatch(amount):
            value = Decimal(amount)
        else:
            return None
        if value <= 0:
            return None
        if cue in ('por', 'para', 'a'):
            proposals.append(value)
            continue
        before = question[:match.start()]
        relative = RELATIVE.search(before)
        if relative:
            decrease = relative[1].startswith(('baix', 'reduz', 'diminu'))
            proposals.append(current - value if decrease else current + value)
        elif (DISCOUNT.search(before) and
              re.match(r'\s+de\s+desconto\b', question[match.end():])):
            proposals.append(current - value)
        elif cue == 'em' or not re.search(r'\bsimul\w*\s*$', before):
            return None
        else:
            proposals.append(value)
    return proposals[0] if len(proposals) == 1 and proposals[0] > 0 else None


def _simulation_answer(result: dict, price: Decimal, *, tax: bool = False) -> str:
    """Show the same repricing numbers as the slider, with market coverage."""
    scenario = volume_scenario(result, price)
    if tax:
        return (f"A {brl_markdown(price)}, a tributação estimada na venda é de "
                f"{brl_markdown(scenario['tax_brl'])} por unidade no perfil demonstrativo.")
    contribution = scenario['contribution_brl']
    text = (f"A {brl_markdown(price)}, a contribuição fica em "
            f"{brl_markdown(contribution)} por unidade "
            f"({percent(scenario['contribution_percent'])} do preço). ")
    change = scenario['volume_change_percent']
    if contribution <= 0:
        text += 'Aumentar o volume nesse preço não gera contribuição positiva. '
    elif change is None:
        text += 'A comparação de volume exige uma contribuição inicial positiva. '
    elif change == 0:
        text += 'O mesmo volume mantém a contribuição total do cenário inicial. '
    else:
        direction = 'a mais' if change > 0 else 'a menos'
        text += (f"Para manter a contribuição total, o volume seria "
                 f"{percent(abs(change))} {direction}. ")
    position = scenario['position']
    if position is not None:
        text += ('Diferença para a mediana de mercado: '
                 f"{percent(position['gap_percent'], signed=True)}. ")
    else:
        text += 'A comparação atual de mercado está indisponível. '
    return text + 'Simulação com as premissas atuais, sem previsão de demanda.'


def _market_facts(market: dict) -> str:
    """Date and sample size of the market reference, in plain words."""
    stores = market.get('store_count')
    sample = (f"{stores} lojas de {market['network_count']} redes" if stores else
              f"{market['network_count']} redes")
    return (f"A última coleta de preços usada aqui é de {display_date(market['date'])}, "
            f"com preços de {sample} de supermercado em Curitiba.")


def _network_answer(market: dict) -> str:
    """Cheapest and most expensive network in the reference."""
    prices = sorted((Decimal(str(value)), network_name(name))
                    for name, value in market['per_network_brl'].items() if value is not None)
    if len(prices) < 2:
        return 'Ainda não há redes suficientes para comparar neste produto.'
    (low, cheapest), (high, priciest) = prices[0], prices[-1]
    return (f'Na referência de mercado, a rede com o menor preço é {cheapest} '
            f'({brl_markdown(low)}) e a de maior preço é {priciest} ({brl_markdown(high)}). '
            'A lista completa está em "Ver preços por rede", na aba Preço e mercado.')


def _median_answer(market: dict) -> str:
    """Explain the median without statistics vocabulary."""
    return ('A mediana é o preço do meio: se você colocar os preços das lojas em fila, '
            'do mais barato ao mais caro, é o que fica no centro. Metade das lojas cobra '
            'até esse valor e a outra metade cobra mais. Aqui ela é de '
            f"{brl_markdown(market['median'])}. Ela é usada porque um preço muito alto "
            'ou muito baixo em uma loja não a puxa para cima ou para baixo.')


def _margin_answer(result: dict) -> str:
    """Show the contribution as price minus each deduction."""
    margin = result['analysis']['personalized']['margin']
    parts = (f"Preço de venda {brl_markdown(result['evaluated_price_brl'])} − custo de compra "
             f"{brl_markdown(margin['net_cost_brl'])} − tributos na venda "
             f"{brl_markdown(margin['tax_brl'])}")
    if margin['expense_brl']:
        parts += f" − outras despesas {brl_markdown(margin['expense_brl'])}"
    return (f"{parts} = {brl_markdown(margin['contribution_brl'])} por unidade "
            f"({percent(margin['contribution_percent'])} do preço). "
            'Essa margem de contribuição é o que sobra de cada venda para pagar as '
            'despesas fixas da loja, como aluguel e salários, e gerar lucro.')


def _raise_answer(result: dict) -> str:
    """Simulate the top of the central market band."""
    points = result['corridor_points']
    if not points:
        return ('Sem uma referência de mercado recente, o app não indica até onde subir. '
                'Teste um preço, como "E se eu vender a R$ 12,50?".')
    top = points[-1]['price_brl']
    if top <= result['evaluated_price_brl']:
        return (f'Seu preço já está no topo da faixa em que fica a metade do meio das lojas '
                f'({brl_markdown(top)}) ou acima dela. Subir mais deixa você entre as '
                'lojas mais caras.')
    scenario = volume_scenario(result, top)
    current = result['analysis']['personalized']['margin']['contribution_brl']
    text = (f"Subindo para {brl_markdown(top)}, o topo da faixa em que fica a metade do meio "
            f"das lojas, sobram {brl_markdown(scenario['contribution_brl'])} por unidade, "
            f"contra {brl_markdown(current)} hoje. ")
    change = scenario['volume_change_percent']
    if change is not None and change < 0:
        text += (f'Você pode vender até {percent(abs(change))} menos e ainda ganhar o mesmo '
                 'no total. ')
    return text + 'É uma simulação: o app não sabe quanto as vendas cairiam com o aumento.'


def _best_price_answer(market: dict) -> str:
    """Say why there is no single ideal price and what the app offers instead."""
    text = ('O app não calcula um preço ideal, porque não sabe quanto as vendas mudam '
            'quando o preço muda. Ele mostra onde o seu preço fica no mercado e quanto '
            'sobra por unidade em cada preço. ')
    if market.get('usable_for_band') and market.get('p25') is not None:
        text += (f"Aqui, a metade do meio das lojas cobra entre {brl_markdown(market['p25'])} "
                 f"e {brl_markdown(market['p75'])}. ")
    return text + 'Para testar outros preços, use a aba Margem e promoção.'


def direct_answer(question: str, result: dict) -> str | None:
    """Plain answers to common questions that the scenario itself settles."""
    if result['status'] != 'ready':
        return None
    text = normalize('NFKD', question.casefold()).encode('ascii', 'ignore').decode()
    market = result['market']
    has_market = market.get('median') is not None
    routes = (
        (has_market and bool(LAST_COLLECTION.search(text) or STORE_COUNT.search(text)),
         lambda: _market_facts(market)),
        (has_market and bool(NETWORK_RANK.search(text)), lambda: _network_answer(market)),
        (has_market and bool(MEDIAN_MEANING.search(text)), lambda: _median_answer(market)),
        (bool(BEST_PRICE.search(text)), lambda: _best_price_answer(market)),
        (bool(MARGIN_MEANING.search(text)), lambda: _margin_answer(result)),
        (bool(RAISE_ASK.search(text)) and not re.search(r'\d', text),
         lambda: _raise_answer(result)),
    )
    return next((answer() for matches, answer in routes if matches), None)


def _percent_price(question: str, current: Decimal) -> tuple[Decimal | None, str]:
    """Turn '10% de desconto' or 'subir 5%' into a price and a short lead-in."""
    match = PERCENT_CHANGE.search(question)
    if not match:
        return None, ''
    rate = Decimal(match[1].replace(',', '.')) / 100
    if LOWER_WORDS.search(question):
        rate = -rate
    elif not HIGHER_WORDS.search(question):
        return None, ''
    price = (current * (1 + rate)).quantize(Decimal('0.01'))
    if price <= 0:
        return None, ''
    return price, (f'Com essa variação, o preço vai de {brl_markdown(current)} '
                   f'para {brl_markdown(price)}. ')


def answer_question(question: str, result: dict) -> str:
    """Route a question to an answer built from the selected result."""
    if result['status'] != 'ready':
        return ('Ainda não há preço avaliado neste cenário. Informe um preço '
                'para calcular a margem e a tributação estimada.')
    normalized = normalize('NFKD', question.casefold()).encode('ascii', 'ignore').decode()
    price = _proposed_price(normalized, result['evaluated_price_brl'])
    prefix = ''
    if price is None:
        price, prefix = _percent_price(normalized, result['evaluated_price_brl'])
    topic = match_topic(question)
    explicit = PRICE_CHANGE.search(normalized) and (
        CURRENCY.search(normalized) or price is not None
        or normalized.startswith(('e se', 'simul')))
    discount = re.search(r'\b(?:dar|aplicar)\b.*\bdesconto\b', normalized)
    seasonal = PROMOTION.search(normalized) and OCCASION.search(normalized)
    if prefix or explicit or seasonal or (discount and price is not None):
        is_tax = (
            topic == 'tax' or bool(re.search(r'\b(?:imposto|tributo|tributacao)\b', normalized)))
        return (prefix + _simulation_answer(result, price, tax=is_tax) if price is not None else
                'Informe um único preço de venda em reais, como R$ 11,48.')
    if topic is None:
        return ('Tente perguntar sobre um assunto por vez: posição no mercado, '
                'desconto, margem de contribuição ou tributação estimada.')
    if topic == 'promotion':
        return _promotion_answer(result)
    if topic == 'tax':
        margin = result['analysis']['personalized']['margin']
        share = margin['tax_brl'] * 100 / result['evaluated_price_brl']
        detail = ' Veja as premissas e o detalhe tributário na aba Detalhes.'
        treatment = result['assumptions'].get('product_tax') or {}
        if margin['tax_brl'] == 0 and treatment.get('purchase_icms_st_assumed'):
            detail = (' O perfil assume ICMS-ST retido na compra e '
                      'incluído no custo informado.')
        return (f"Tributação estimada na venda: {brl_markdown(margin['tax_brl'])} "
                f"por unidade ({percent(share)} do preço) no perfil "
                f"demonstrativo.{detail}")
    reading = decision_text(result)
    return (reading['contribution'] if topic == 'margin' else
            f"{reading['position']} {reading['action']}")
