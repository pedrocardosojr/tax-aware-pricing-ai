"""Let a model write the pricing brief, then show it only if it stays grounded."""
import json
import logging
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TypedDict
from urllib.request import Request, urlopen

from tax_pricing.seasonal_calendar import sector_month, upcoming
from tax_pricing.ui.formatting import MONTH_NAMES
from tax_pricing.ui.reading import decision_text

NUMBER = re.compile(r'\d+(?:[.,]\d+)*')
UNESCAPED_DOLLAR = re.compile(r'(?<!\\)\$')
LOGGER = logging.getLogger(__name__)
MAX_CHARS = 800
OPENAI_URL = 'https://api.openai.com/v1/chat/completions'
# Gemini models think before answering and the thinking counts against the
# output limit, so other providers get a larger limit and more time.
OPENAI_LIMITS = {'max_completion_tokens': 300, 'timeout': 10}
OTHER_LIMITS = {'max_completion_tokens': 4000, 'timeout': 30}
SECTIONS = ('contribution', 'position', 'action', 'season')
SEASON_DAYS = 45
# Claims the app cannot support from observed prices and demonstrative profiles.
FORBIDDEN = ('lucro', 'garant', 'certeza', 'certamente', 'demanda',
             'elasticidade', 'previs', 'vai vender', 'vendera', 'otimo')
SYSTEM_PROMPT = (
    'Você é um consultor de preços conversando com o dono de um mercado de '
    'bairro. Explique o cenário como numa conversa no balcão, em português do '
    'Brasil: frases curtas, palavras do dia a dia, tratando o lojista por '
    'você. Não copie as frases dos fatos; diga o mesmo com suas palavras. '
    'Evite termos técnicos: em vez de deduções, contribuição ou margem de '
    'contribuição, fale no que sobra por unidade depois dos impostos e '
    'custos; em vez de mediana observada, fale no preço do meio entre os '
    'mercados pesquisados; não use índice de preço, posicionamento, premissas '
    'nem cenário. Em season, conte a data ou o mês e o que a pesquisa do '
    'setor observa, como contexto e nunca como previsão para a loja. '
    'Quando a fonte apenas cita uma categoria, diga que ela foi citada. '
    'Use somente números que aparecem nos fatos, escritos como '
    'estão, sem arredondar nem calcular valores novos. Comece pelo tema '
    'indicado em priority. Se os fatos disserem que a referência é histórica '
    'ou estimada, mantenha essa palavra. Não fale em lucro, garantia, demanda '
    'ou previsão, exceto para dizer que a sazonalidade não é previsão. '
    'Responda só com JSON nos campos contribution, position, action e '
    'season, no máximo uma frase curta em cada, sem deixar campo vazio '
    'quando o fato tiver conteúdo. Em contribution, use o valor e o '
    'percentual do fato, no formato do exemplo: "Tirando impostos e custos, '
    'sobram R$ X por unidade, Y% do preço de venda." Use '
    'apenas números dos fatos da própria seção. Position e action podem ser '
    'strings vazias; season fica vazia quando o fato season for vazio.'
)


class PricingExplanation(TypedDict):
    """Sentences whose values and interpretation come from the app."""

    contribution: str
    position: str
    action: str
    season: str


def season_fact(group: str, today: date) -> str:
    """Return the current season sentence for the existing explanation flow."""
    return season_context(group, today)[0]


def season_context(group: str, today: date) -> tuple[str, str]:
    """Name the next retail date for the product, or the month's sector signal.

    Only dates whose source names the product group are tied to it; the IBGE
    monthly figure describes all supermarkets in Paraná, never this store.
    """
    events = [event for event in upcoming(today, group, days=SEASON_DAYS)
              if event['cita_o_produto']]
    if events:
        event = events[0]
        start = date.fromisoformat(str(event['inicio']))
        end = date.fromisoformat(str(event['fim']))
        if start <= today:
            when = f' vai até {end:%d/%m}'
        elif end > start:
            when = f', de {start:%d/%m} a {end:%d/%m}'
        else:
            when = f' em {start:%d/%m}'
        product = group[:1].lower() + group[1:]
        line = (f"{event['evento']}{when}: a fonte cita {product} "
                'entre as categorias associadas à data. É uma sugestão do setor, não '
                'uma previsão para a sua loja.')
        return line, str(event['fonte_url'])
    month = sector_month(today.month)
    deviation = float(str(month['desvio_medio_pct']))
    if abs(deviation) < 3:
        return '', str(month['fonte_url'])
    direction = 'acima' if deviation > 0 else 'abaixo'
    value = f'{abs(deviation):.1f}'.replace('.', ',')
    line = (f'Em {MONTH_NAMES[today.month - 1]}, os supermercados do Paraná '
            f'tiveram volume de vendas {value}% {direction} da média anual, segundo o '
            'IBGE (2022 a 2025). É uma sugestão do setor, não uma previsão para a sua loja.')
    return line, str(month['fonte_url'])


def explanation_facts(result: dict, today: date | None = None) -> PricingExplanation:
    """Build the text the model rewrites and the app shows as fallback."""
    reading = decision_text(result)
    return {
        'contribution': reading['contribution'],
        'position': reading['position'],
        'action': reading['action'],
        'season': season_fact(result['product']['group'], today or date.today()),
    }


def required_terms(result: dict) -> tuple[str, ...]:
    """Return the caveats a written explanation must keep for this scenario."""
    terms = []
    if result['market']['status'] == 'historical_reference':
        terms.append('histor')
    if result['market'].get('kind') == 'estimated':
        terms.append('estimad')
    return tuple(terms)


def _ordered(facts: PricingExplanation) -> list[str]:
    """Return the three app sentences in their reading order."""
    return [facts['contribution'], facts['position'], facts['action'],
            facts['season']]


def _plain(text: str) -> str:
    """Lowercase without accents, so 'Histórica' matches 'histor'."""
    decomposed = unicodedata.normalize('NFKD', text.lower())
    return ''.join(char for char in decomposed
                   if not unicodedata.combining(char))


def _numbers(text: str) -> set[Decimal]:
    """Read every figure the way it is printed in Brazilian formatting."""
    values = set()
    for token in NUMBER.findall(text):
        if ',' in token:
            token = token.replace('.', '').replace(',', '.')
        try:
            values.add(Decimal(token).normalize())
        except InvalidOperation:
            continue
    return values


def rejection_reason(facts: PricingExplanation, text: str,
                     required: tuple[str, ...] = ()) -> str | None:
    """Explain why a written text cannot be shown, or None if it can.

    Parameters
    ----------
    facts : PricingExplanation
        Deterministic sentences the model was asked to rewrite.
    text : str
        Text written by the model.
    required : tuple of str
        Accent-free fragments that must survive, such as 'histor'.

    Returns
    -------
    str or None
        Short reason for the fallback; None when every check passes.
    """
    source = ' '.join(_ordered(facts))
    if not text.strip() or len(text) > MAX_CHARS:
        return 'tamanho'
    invented = _numbers(text) - _numbers(source)
    if invented:
        return 'numero_fora_do_calculo'
    if not _numbers(facts['contribution']) <= _numbers(text):
        return 'omitiu_contribuicao'
    plain, plain_source = _plain(text), _plain(source)
    if any(term in plain and term not in plain_source for term in FORBIDDEN):
        return 'termo_proibido'
    if any(term not in plain for term in required):
        return 'perdeu_aviso'
    return None


def _valid_sections(facts: PricingExplanation, payload: object,
                    required: tuple[str, ...]) -> bool:
    """Keep financial figures and market caveats in their respective sections."""
    if not isinstance(payload, dict) or set(payload) != set(SECTIONS):
        return False
    if any(not isinstance(payload[section], str) for section in SECTIONS):
        return False
    if any(_numbers(payload[section]) - _numbers(str(fact))
           for section, fact in facts.items()):
        return False
    if not payload['contribution'].strip() or not (
            _numbers(facts['contribution']) <= _numbers(payload['contribution'])):
        return False
    if any(term not in _plain(payload['position']) for term in required):
        return False
    return True


def validated_explanation(facts: PricingExplanation,
                          reply: str | None = None, *,
                          priority: str = 'contribution',
                          required: tuple[str, ...] = ()
                          ) -> tuple[list[str], bool]:
    """Return the model's text when grounded, otherwise the app's reading.

    Parameters
    ----------
    facts : PricingExplanation
        Deterministic sentences from the calculated scenario.
    reply : str, optional
        Raw model output with contribution, position and action sections.
    priority : str
        Section shown first in the fallback.
    required : tuple of str
        Caveats the written text must keep.

    Returns
    -------
    tuple
        Paragraphs to render and whether they were written by the model.
    """
    first = facts['position'] if priority == 'position' else (
        facts['action'] if priority == 'action' else facts['contribution'])
    fallback = [first, *(text for text in _ordered(facts)
                         if text and text != first)]
    if not isinstance(reply, str) or len(reply) > 4 * MAX_CHARS:
        return fallback, False
    try:
        payload = json.loads(reply)
    except ValueError:
        return fallback, False
    if not _valid_sections(facts, payload, required):
        return fallback, False
    priority = priority if priority in SECTIONS else 'contribution'
    order = [priority, *(section for section in SECTIONS if section != priority)]
    text = ' '.join(payload[section].strip() for section in order
                    if payload[section].strip())
    if rejection_reason(facts, text, required) is not None:
        return fallback, False
    # Two bare dollar signs on one line render as a formula in Streamlit.
    return [UNESCAPED_DOLLAR.sub(r'\\$', text.strip())], True


# pylint: disable-next=too-many-arguments
def request_explanation(facts: PricingExplanation, priority: str, *,
                        model: str, api_key: str,
                        required: tuple[str, ...] = (),
                        url: str = '') -> str | None:
    """Ask the configured model to write the brief on explicit user request.

    ``url`` points to any chat completions endpoint that follows the OpenAI
    format, such as Gemini's; it defaults to OpenAI.
    """
    url = url or OPENAI_URL
    openai = url == OPENAI_URL
    limits = OPENAI_LIMITS if openai else OTHER_LIMITS
    payload: dict = {
        'model': model,
        'max_completion_tokens': limits['max_completion_tokens'],
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': json.dumps(
                {'priority': priority, 'avisos_obrigatorios': list(required),
                 'facts': facts}, ensure_ascii=False)},
        ],
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': 'pricing_explanation', 'strict': True,
            'schema': {
                'type': 'object', 'additionalProperties': False,
                'required': list(SECTIONS),
                'properties': {section: {'type': 'string'} for section in SECTIONS},
            },
        }},
    }
    if openai:
        payload['store'] = False
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={'Authorization': f'Bearer {api_key}',
                 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(request, timeout=limits['timeout']) as response:
            completion = json.loads(response.read(65536))
        choice = completion['choices'][0]
        if choice['finish_reason'] == 'stop':
            content = choice['message']['content']
            if isinstance(content, str):
                return content
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        pass
    return None


def request_answer(messages: list[dict[str, str]], *, model: str, api_key: str,
                   url: str = '', timeout: int | None = None) -> str | None:
    """Ask the configured model for a short sourced answer in plain text.

    A caller whose answer is optional can pass a shorter ``timeout``.
    """
    url = url or OPENAI_URL
    openai = url == OPENAI_URL
    limits = OPENAI_LIMITS if openai else OTHER_LIMITS
    if timeout is not None:
        limits = {**limits, 'timeout': min(timeout, limits['timeout'])}
    payload: dict = {'model': model, 'messages': messages,
                     'max_completion_tokens': limits['max_completion_tokens']}
    if openai:
        payload['store'] = False
    request = Request(url, data=json.dumps(payload).encode(), method='POST',
                      headers={'Authorization': f'Bearer {api_key}',
                               'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=limits['timeout']) as response:
            completion = json.loads(response.read(65536))
        choice = completion['choices'][0]
        content = choice['message']['content']
        if choice['finish_reason'] == 'stop' and isinstance(content, str):
            return content
        LOGGER.warning('Model answer not usable: finish_reason=%s', choice['finish_reason'])
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        LOGGER.warning('Model request failed: %s status=%s', type(error).__name__,
                       getattr(error, 'code', None))
    return None


def sourced_answer_is_valid(answer: str | None, allowed_text: str,
                            cites_retrieved: bool) -> bool:
    """Show a sourced answer only with known figures and retrieved citations.

    ``allowed_text`` joins the question, the calculated facts and the
    retrieved excerpts; ``cites_retrieved`` is the citation check result.
    """
    if not answer or not answer.strip() or len(answer) > 4 * MAX_CHARS:
        return False
    invented = _numbers(answer) - _numbers(allowed_text)
    return cites_retrieved and not invented


def invented_numbers(answer: str | None, allowed_text: str) -> list[str]:
    """List figures in the answer that the facts and excerpts do not contain."""
    return sorted(str(value) for value in _numbers(answer or '') - _numbers(allowed_text))


def markdown_safe(text: str) -> str:
    """Escape dollar signs so Streamlit does not render them as formulas."""
    return UNESCAPED_DOLLAR.sub(r'\\$', text)
