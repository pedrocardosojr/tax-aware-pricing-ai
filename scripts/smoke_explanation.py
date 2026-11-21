"""Run one authenticated pricing explanation on the Coca-Cola demo scenario."""
import json
from pathlib import Path
from time import perf_counter

from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.ui.grounded_explanation import (
    explanation_facts, request_explanation, required_terms, validated_explanation,
)
from tax_pricing.ui.view import _llm_setting

SNAPSHOT = (Path(__file__).resolve().parents[1] /
            'evidencias/integracao_mercado_2026-11-09/snapshots/7894900027013.json')


def main() -> None:
    """Read the same settings as the app and report the single-call outcome."""
    key = _llm_setting('OPENAI_API_KEY')
    model = _llm_setting('TAX_PRICING_LLM_MODEL')
    if not key or not model:
        raise SystemExit('Configure OPENAI_API_KEY e TAX_PRICING_LLM_MODEL nos Secrets.')
    inputs = {'ean': '7894900027013', 'regime': 'simples_nacional',
              'acquisition_cost': '7.00', 'selling_price': '12.00'}
    result = analyze_mvp(inputs, json.loads(SNAPSHOT.read_text()),
                         api='http://127.0.0.1:1')
    facts = explanation_facts(result)
    required = required_terms(result)
    start = perf_counter()
    reply = request_explanation(facts, 'contribution', model=model, api_key=key,
                                required=required, url=_llm_setting(
                                    'TAX_PRICING_LLM_URL'))
    seconds = round(perf_counter() - start, 3)
    paragraphs, written = validated_explanation(facts, reply, required=required)
    status = ('sem_resposta' if reply is None else
              'aceita' if written else 'recusada_pelo_validador')
    print(json.dumps({'modelo': model, 'segundos': seconds, 'resultado': status,
                      'texto_exibido': paragraphs}, ensure_ascii=False, indent=2))
    if not written:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
