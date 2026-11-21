"""Measure source retrieval before connecting a model.

Uso, na raiz do repositório:
    python pesquisas/ia_fontes_2026-11-14/avaliar_busca.py construcao
    python pesquisas/ia_fontes_2026-11-14/avaliar_busca.py reservado2

'construcao' e 'reservado1' ajustaram a busca. 'reservado2' foi rodado uma vez,
depois do ajuste, e não pode orientar novos ajustes.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))

from tax_pricing.source_search import default_index  # noqa: E402  pylint: disable=C0413

SETS = {'construcao': 'perguntas.json', 'reservado1': 'perguntas_reservadas.json',
        'reservado2': 'perguntas_reservadas_2.json'}


def evaluate(set_name: str, min_score: float | None = None) -> dict:
    """Top source per question, correct refusals and the misses."""
    questions = json.loads((ROOT / SETS[set_name]).read_text(encoding='utf-8'))
    index = default_index()
    rows = []
    for question, expected in questions:
        result = (index.search(question) if min_score is None
                  else index.search(question, min_score=min_score))
        got = result.excerpts[0].source_id if result.answerable else None
        rows.append({'pergunta': question, 'esperado': expected, 'recuperado': got,
                     'status': result.status,
                     'pontuacao': result.excerpts[0].score if result.answerable else None,
                     'fontes': [item.url for item in result.excerpts]})
    with_source = [row for row in rows if row['esperado'] is not None]
    outside = [row for row in rows if row['esperado'] is None]
    return {
        'conjunto': set_name,
        'fontes_corretas': sum(row['esperado'] == row['recuperado'] for row in with_source),
        'perguntas_com_fonte': len(with_source),
        'recusas_corretas': sum(row['recuperado'] is None for row in outside),
        'perguntas_fora_do_acervo': len(outside),
        'erros': [row for row in rows if row['esperado'] != row['recuperado']],
    }


if __name__ == '__main__':
    print(json.dumps(evaluate(sys.argv[1] if len(sys.argv) > 1 else 'construcao'),
                     ensure_ascii=False, indent=2))
