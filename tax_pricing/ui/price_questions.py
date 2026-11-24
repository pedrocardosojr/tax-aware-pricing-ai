"""Retrieve supported pricing questions and explain the checked scenario."""
from collections import Counter
from decimal import Decimal
from math import log, sqrt
import re
from unicodedata import normalize

from tax_pricing.pricing_scenarios import volume_scenario
from tax_pricing.ui.formatting import brl_markdown, percent
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


def answer_question(question: str, result: dict) -> str:
    """Route a question to an answer built from the selected result."""
    if result['status'] != 'ready':
        return ('Ainda não há preço avaliado neste cenário. Informe um preço '
                'para calcular a margem e a tributação estimada.')
    normalized = normalize('NFKD', question.casefold()).encode('ascii', 'ignore').decode()
    price = _proposed_price(normalized, result['evaluated_price_brl'])
    topic = match_topic(question)
    explicit = PRICE_CHANGE.search(normalized) and (
        CURRENCY.search(normalized) or price is not None
        or normalized.startswith(('e se', 'simul')))
    discount = re.search(r'\b(?:dar|aplicar)\b.*\bdesconto\b', normalized)
    seasonal = PROMOTION.search(normalized) and OCCASION.search(normalized)
    if explicit or seasonal or (discount and price is not None):
        is_tax = (
            topic == 'tax' or bool(re.search(r'\b(?:imposto|tributo|tributacao)\b', normalized)))
        return (_simulation_answer(result, price, tax=is_tax) if price is not None else
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
