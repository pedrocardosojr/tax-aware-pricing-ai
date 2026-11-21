"""Measure the grounded explanation over every catalogue SKU and regime.

Without credentials this checks the validator itself on each scenario: the
app's own reading must be accepted, and the same reading with one figure
moved by a cent must be rejected. With OPENAI_API_KEY and
TAX_PRICING_LLM_MODEL set it also asks the model to write each brief and
records how many were shown and why the others fell back.

Run from the repository root: python -m scripts.eval_grounded_explanation
"""
from collections import Counter
from decimal import Decimal
import json
from math import isfinite
from pathlib import Path
import re
from time import perf_counter, sleep
from unittest.mock import patch

from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.ui.data import market_snapshot, products
from tax_pricing.ui.grounded_explanation import (
    explanation_facts, rejection_reason, request_explanation, required_terms,
    validated_explanation,
)

from tax_pricing.ui.view import _llm_setting

REGIMES = ('simples_nacional', 'lucro_presumido', 'lucro_real')
OUT = Path(__file__).resolve().parents[1] / 'evidencias' / 'explicacao_ia'
FIRST_AMOUNT = re.compile(r'(\d+),(\d{2})')


def scenarios() -> list[dict]:
    """Analyse each SKU in each regime with the market available to the app."""
    rows = []
    with patch('tax_pricing.product_analysis.calculate_current_tax',
               side_effect=RuntimeError('offline evaluation')):
        for product in products():
            market = market_snapshot(product['ean'])
            price = (Decimal(str(market['median'])) if market
                     else Decimal('12.00'))
            for regime in REGIMES:
                inputs = {'ean': product['ean'], 'regime': regime,
                          'acquisition_cost': (price * Decimal('0.6')
                                               ).quantize(Decimal('0.01')),
                          'selling_price': price}
                rows.append({'ean': product['ean'], 'regime': regime,
                             'result': analyze_mvp(inputs, market)})
    return rows


def _shift_one_cent(text: str) -> str:
    """Move the first decimal figure by one cent, the smallest invention."""
    match = FIRST_AMOUNT.search(text)
    if match is None:
        return text
    cents = int(match.group(1)) * 100 + int(match.group(2)) + 1
    moved = f'{cents // 100},{cents % 100:02d}'
    return text[:match.start()] + moved + text[match.end():]


def main() -> None:
    """Print and save validator checks and, when configured, model results."""
    rows = scenarios()
    accepted = rejected_shift = 0
    model_reasons: Counter = Counter()
    api_key = _llm_setting('OPENAI_API_KEY')
    model = _llm_setting('TAX_PRICING_LLM_MODEL')
    url = _llm_setting('TAX_PRICING_LLM_URL')
    pause = float(_llm_setting('TAX_PRICING_LLM_PAUSE') or '5')
    limit = int(_llm_setting('TAX_PRICING_LLM_EVAL_LIMIT') or len(rows))
    if not isfinite(pause) or pause < 0 or limit < 1:
        raise SystemExit('Informe uma pausa finita >= 0 e um limite de chamadas >= 1.')
    attempts = 0
    duration = 0.0
    for row in rows:
        facts = explanation_facts(row['result'])
        required = required_terms(row['result'])
        reading = ' '.join([facts['contribution'], facts['position'],
                            facts['action'], facts['season']])
        accepted += rejection_reason(facts, reading, required) is None
        rejected_shift += rejection_reason(
            facts, _shift_one_cent(reading), required) is not None
        if api_key and model and attempts < limit:
            start = perf_counter()
            margin = row['result']['analysis']['personalized']['margin']
            priority = ('position' if 'histor' in required and
                        margin['contribution_brl'] >= 0 else 'contribution')
            reply = request_explanation(facts, priority, model=model,
                                        api_key=api_key, required=required,
                                        url=url)
            _, written = validated_explanation(
                facts, reply, priority=priority, required=required)
            reason = ('sem_resposta' if reply is None else
                      'aceito' if written else 'recusado_pelo_validador')
            model_reasons[reason] += 1
            attempts += 1
            elapsed = perf_counter() - start
            duration += elapsed
            if attempts < min(limit, len(rows)):
                sleep(max(0, pause - elapsed))
    summary = {
        'cenarios': len(rows),
        'texto_do_app_aceito': accepted,
        'um_centavo_alterado_rejeitado': rejected_shift,
        'modelo': model if attempts else None,
        'chamadas_tentadas': attempts,
        'segundos_medios_por_chamada': round(duration / attempts, 3) if attempts else None,
        'resultado_do_modelo': dict(model_reasons) or None,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'resumo.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
