"""Execute and score a local LLM on transcribed supermarket offers."""

import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from importlib.metadata import version
import json
from pathlib import Path
from time import monotonic

FOLDER = Path(__file__).resolve().parent
MODEL = 'mlx-community/Qwen2.5-3B-Instruct-4bit'
TARGET_DATE = date(2026, 11, 10)
FIELDS = (
    'identidade', 'volume_ml', 'mecanica', 'preco_unidade_brl',
    'preco_combo_brl', 'quantidade_minima', 'selo_clube',
    'inicio', 'fim', 'praca',
)
INSTRUCTIONS = """Extraia a oferta brasileira fornecida, sem consultar outras fontes.
Responda apenas um objeto JSON com estas chaves, sem Markdown.
- identidade: "exato" se inclui explicitamente Coca-Cola Tradicional PET 2 L
  (mesmo quando há combo), "possivel" se inclui Coca-Cola PET 2 L mas a
  variante não é indicada, ou "outro" nos demais casos.
- volume_ml: inteiro em ml da embalagem anunciada, sem conversão por litro
  equivalente. Se houver mais de um produto, use o volume do primeiro.
- mecanica: "combo_misto" se exige produtos diferentes juntos,
  "quantidade" se exige várias unidades do mesmo produto, ou "avulsa".
- preco_unidade_brl e preco_combo_brl: strings com ponto decimal, ou null.
  Só transcreva os valores explicitamente anunciados e aplicáveis à
  apresentação. Ignore preço anterior e preço equivalente a outro volume.
  Registre o total do combo quando explícito. Nunca divida o total.
- quantidade_minima: inteiro de unidades a levar, 1 para oferta avulsa.
- selo_clube: true se o anúncio indica clube, false se indica ausência do
  selo, null se nada consta sobre o selo.
- inicio e fim: strings ISO AAAA-MM-DD conforme validade informada.
- praca: nome do estado ou da cidade indicada.
Use null para campo sem evidência. Não calcule preço nem complete com suposições."""


EXAMPLES = (
    (
        'Curitiba. De 02/01/2026 a 03/01/2026. Pepsi PET 2 L. Clube: '
        'R$ 8,10 cada. Preço anterior de R$ 9,99.',
        {'identidade': 'outro', 'volume_ml': 2000, 'mecanica': 'avulsa',
         'preco_unidade_brl': '8.10', 'preco_combo_brl': None,
         'quantidade_minima': 1, 'selo_clube': True, 'inicio': '2026-01-02',
         'fim': '2026-01-03', 'praca': 'Curitiba'},
    ),
    (
        'Paraná. De 02/01/2026 a 03/01/2026. Kit de uma Coca-Cola '
        'Tradicional PET 2 L e uma Soda Limão PET 2 L por R$ 16,70. '
        'Sem selo de Clube no quadro. Só há preço do kit.',
        {'identidade': 'exato', 'volume_ml': 2000, 'mecanica': 'combo_misto',
         'preco_unidade_brl': None, 'preco_combo_brl': '16.70',
         'quantidade_minima': 2, 'selo_clube': False, 'inicio': '2026-01-02',
         'fim': '2026-01-03', 'praca': 'Paraná'},
    ),
    (
        'Londrina. De 02/01/2026 a 03/01/2026. Coca-Cola PET 2,5 L, '
        'R$ 9,75 a garrafa, equivalente a R$ 7,80 por 2 L. '
        'Sem selo de Clube no quadro.',
        {'identidade': 'outro', 'volume_ml': 2500, 'mecanica': 'avulsa',
         'preco_unidade_brl': '9.75', 'preco_combo_brl': None,
         'quantidade_minima': 1, 'selo_clube': False, 'inicio': '2026-01-02',
         'fim': '2026-01-03', 'praca': 'Londrina'},
    ),
)


def read_json(name: str) -> list[dict]:
    """Read an evaluation input from the fixture directory."""
    return json.loads((FOLDER / f'{name}.json').read_text(encoding='utf-8'))


def parse_object(text: str) -> dict:
    """Require a single JSON object with all requested fields."""
    value = json.loads(text)
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise ValueError('Resposta fora do contrato de campos.')
    return value


def is_unit_benchmark(offer: dict, day: date) -> bool:
    """Gate expired, unclear and conditional ads from the unit benchmark."""
    if (not isinstance(offer['preco_unidade_brl'], str)
            or type(offer['volume_ml']) is not int
            or type(offer['quantidade_minima']) is not int):
        return False
    try:
        start = date.fromisoformat(offer['inicio'])
        end = date.fromisoformat(offer['fim'])
        price = Decimal(offer['preco_unidade_brl'])
    except (TypeError, ValueError, InvalidOperation):
        return False
    return (start <= day <= end and price.is_finite() and price > 0
            and offer['identidade'] == 'exato' and offer['volume_ml'] == 2000
            and offer['mecanica'] == 'avulsa' and offer['quantidade_minima'] == 1
            and offer['selo_clube'] is False and offer['praca'] in (
                'Curitiba', 'Paraná'))


def main() -> None:
    """Run one generation per ad and record field-level exact matches."""
    from mlx_lm import generate, load

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--examples', action='store_true')
    args = parser.parse_args()
    samples = read_json('anuncios')
    truth = {row['id']: row for row in read_json('gabarito')}
    if len(samples) != len(truth) or {row['id'] for row in samples} != set(truth):
        raise ValueError('Anúncios e gabarito devem ter os mesmos IDs únicos.')
    model, tokenizer = load(args.model)
    results = []
    correct = Counter(dict.fromkeys(FIELDS, 0))
    messages = [{'role': 'system', 'content': INSTRUCTIONS}]
    if args.examples:
        for text, answer in EXAMPLES:
            messages.append({'role': 'user', 'content': text})
            messages.append({'role': 'assistant', 'content': json.dumps(
                answer, ensure_ascii=False)})
    for sample in samples:
        expected = truth[sample['id']]
        prompt = tokenizer.apply_chat_template(
            messages + [{'role': 'user', 'content': sample['text']}],
            tokenize=False, add_generation_prompt=True,
        )
        start = monotonic()
        response = generate(model, tokenizer, prompt=prompt,
                            max_tokens=400, verbose=False)
        elapsed = round(monotonic() - start, 2)
        try:
            parsed = parse_object(response.strip())
        except ValueError:
            parsed = None
        matches = [key for key in FIELDS if parsed is not None
                   and type(parsed[key]) is type(expected[key])
                   and parsed[key] == expected[key]]
        correct.update(matches)
        results.append({
            'id': sample['id'], 'response': response, 'elapsed_s': elapsed,
            'valid_json': parsed is not None, 'correct_fields': matches,
            'current_unit_benchmark': (
                parsed is not None and is_unit_benchmark(parsed, TARGET_DATE)),
        })
        print(f"{sample['id']}: {len(matches)}/{len(FIELDS)}", flush=True)
    report = {
        'model_id': MODEL if Path(args.model).is_dir() else args.model,
        'mlx_lm_version': version('mlx-lm'),
        'evaluation_date': TARGET_DATE.isoformat(),
        'sample_count': len(results),
        'synthetic_prompt_examples': len(EXAMPLES) if args.examples else 0,
        'correct_by_field': dict(correct),
        'results': results,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)
                           + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
