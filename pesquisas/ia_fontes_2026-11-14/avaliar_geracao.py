"""T4: compare three ways of answering a shopkeeper question.

(a) the app's own answer, no model; (b) the model with the calculated facts
only; (c) the model with the facts and the retrieved source excerpts. Each
answer is scored on three checks: every number comes from the facts, the
excerpts or the question; the expected source is cited and only retrieved
sources are cited; questions outside the sources are refused.

Run from the repository root with the model settings in the environment or
in .streamlit/secrets.toml:
    python pesquisas/ia_fontes_2026-11-14/avaliar_geracao.py [reservado2|grupo]
The free Gemini tier allows 15 requests per minute, so calls are paced.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tax_pricing.mvp_analysis import analyze_mvp
from tax_pricing.source_search import (
    REFUSALS, SearchResult, build_messages, citations_are_valid, find_sources,
)
from tax_pricing.ui.grounded_explanation import OPENAI_URL, _numbers, explanation_facts
from tax_pricing.ui.price_questions import answer_question
from tax_pricing.ui.view import _llm_setting

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SETS = {'reservado2': HERE / 'perguntas_reservadas_2.json',
        'grupo': HERE / 'perguntas_grupo.json'}
OUT = ROOT / 'evidencias' / 'ia_fontes_2026-11-14'
SNAPSHOT = ROOT / 'evidencias/integracao_mercado_2026-11-09/snapshots/7894900027013.json'
PAUSE = 5.0
REFUSED = re.compile(r'n[aã]o h[aá] evid[eê]ncia|sem evid[eê]ncia|n[aã]o (tenho|consigo|sei)|'
                     r'n[aã]o (est[aá]|aparece|consta)|fora d[ao]s? (fontes|acervo)')
APP_FALLBACK = ('Tente perguntar', 'Informe um único preço')


def scenario() -> dict:
    """Coca-Cola 2 L in the Simples, cost R$ 7,00 and price R$ 12,00."""
    inputs = {'ean': '7894900027013', 'regime': 'simples_nacional',
              'acquisition_cost': '7.00', 'selling_price': '12.00'}
    return analyze_mvp(inputs, json.loads(SNAPSHOT.read_text()), api='http://127.0.0.1:1')


def chat(messages: list[dict[str, str]], *, key: str, model: str, url: str) -> str | None:
    """One chat completion; wait and retry once when the free limit is hit."""
    body = json.dumps({'model': model, 'messages': messages,
                       'max_completion_tokens': 4000}).encode()
    for attempt in range(2):
        request = Request(url, data=body, method='POST',
                          headers={'Authorization': f'Bearer {key}',
                                   'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=40) as response:
                reply = json.loads(response.read())
            return reply['choices'][0]['message']['content']
        except HTTPError as error:
            if error.code == 429 and attempt == 0:
                time.sleep(45)
                continue
            return None
        except (OSError, ValueError, KeyError, IndexError):
            return None
    return None


def score(answer: str | None, expected: list, allowed_text: str,
          result: SearchResult) -> dict:
    """Fidelity, source and refusal checks for one written answer."""
    if answer is None:
        return {'sem_resposta': True}
    refused = bool(REFUSED.search(answer.lower()))
    cited = set(re.findall(r'\[([a-z_0-9]+)\]', answer))
    wants_refusal = None in expected
    sources = [item for item in expected if item is not None]
    return {
        'numeros_do_calculo': not (_numbers(answer) - _numbers(allowed_text)),
        'citou_fonte_esperada': bool(cited & set(sources)) and citations_are_valid(answer, result),
        'recusou': refused,
        'acertou_recusa': (refused or not cited) if wants_refusal and not sources else None,
    }


def main() -> None:
    """Answer every question three ways and save the scored answers."""
    set_name = sys.argv[1] if len(sys.argv) > 1 else 'reservado2'
    key = _llm_setting('OPENAI_API_KEY')
    model = _llm_setting('TAX_PRICING_LLM_MODEL')
    url = _llm_setting('TAX_PRICING_LLM_URL') or OPENAI_URL
    if not key or not model:
        raise SystemExit('Configure OPENAI_API_KEY e TAX_PRICING_LLM_MODEL.')
    result = scenario()
    facts = {name: str(text) for name, text in explanation_facts(result).items()}
    rows = []
    for question, expected in json.loads(SETS[set_name].read_text()):
        expected = expected if isinstance(expected, list) else [expected]
        app_answer = answer_question(question, result)
        row = {'pergunta': question, 'esperado': expected,
               'a_app': {'texto': app_answer,
                         'recusou': app_answer.startswith(APP_FALLBACK)}}
        empty = SearchResult('sem_evidencia', REFUSALS['sem_evidencia'], ())
        base_text = question + ' ' + ' '.join(facts.values())
        answer = chat(build_messages(question, facts, empty), key=key, model=model, url=url)
        row['b_modelo_com_dados'] = {'texto': answer,
                                     **score(answer, expected, base_text, empty)}
        time.sleep(PAUSE)
        found = find_sources(question)
        if not found.answerable:
            row['c_modelo_com_trechos'] = {
                'texto': found.reason, 'recuperado': [], 'numeros_do_calculo': True,
                'citou_fonte_esperada': False, 'recusou': True,
                'acertou_recusa': True if None in expected and len(expected) == 1 else None}
        else:
            excerpts = ' '.join(item.text for item in found.excerpts)
            answer = chat(build_messages(question, facts, found), key=key, model=model, url=url)
            row['c_modelo_com_trechos'] = {
                'texto': answer, 'recuperado': [item.source_id for item in found.excerpts],
                **score(answer, expected, base_text + ' ' + excerpts, found)}
            time.sleep(PAUSE)
        rows.append(row)
        print(f"{len(rows):2d}. {question[:60]}", flush=True)
    summary = summarize(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f'geracao_{set_name}.json'
    path.write_text(json.dumps({'modelo': model, 'conjunto': set_name, 'resumo': summary,
                                'respostas': rows}, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def summarize(rows: list[dict]) -> dict:
    """Count each check per version, over the questions where it applies."""
    with_source = [row for row in rows if any(item is not None for item in row['esperado'])]
    outside = [row for row in rows if row['esperado'] == [None]]
    summary: dict = {'perguntas': len(rows), 'com_fonte_esperada': len(with_source),
                     'fora_do_acervo': len(outside),
                     'a_app': {'recusas_corretas': sum(r['a_app']['recusou'] for r in outside)}}
    for version in ('b_modelo_com_dados', 'c_modelo_com_trechos'):
        answers = [row[version] for row in rows]
        summary[version] = {
            'sem_resposta': sum(bool(a.get('sem_resposta')) for a in answers),
            'numeros_do_calculo': sum(bool(a.get('numeros_do_calculo')) for a in answers),
            'fonte_esperada_citada': sum(bool(row[version].get('citou_fonte_esperada'))
                                         for row in with_source),
            'recusas_corretas': sum(bool(row[version].get('acertou_recusa'))
                                    for row in outside),
        }
    return summary


if __name__ == '__main__':
    main()
