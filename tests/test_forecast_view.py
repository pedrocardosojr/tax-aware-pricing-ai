"""Check the next-month forecast contract read by the Previsão tab."""
import json
from pathlib import Path
import tempfile
import unittest

from tax_pricing.ui.forecast_view import (
    FORECAST, evaluation_rows, forecast_rows, load_forecast)

CAFE = '7896089011357'


def bundle(**changes):
    """Return a minimal valid forecast bundle, optionally altered."""
    data = {
        'schema_version': 1, 'fonte': 'test fixture',
        'avaliacao': {'teste': [{'modelo': 'híbrido', 'mae_brl': 0.93,
                                 'mdape_pct': 4.64, 'erro_ate_5_pct': 51.8}]},
        'bootstrap_teste': {'ganho_medio_pp': 0.46, 'ic95_pp': [0.07, 0.93]},
        'previsoes': {CAFE: {
            'mes_base': '2026-10', 'mes_previsto': '2026-11',
            'referencia_mes_base': 27.99, 'mediana_prevista': 28.2,
            'redes': [{'rede': 'A', 'previsto': 21.49, 'origem': 'preco_rede',
                       'preco_mes_base': 21.49},
                      {'rede': 'B', 'previsto': 26.52, 'origem': 'nivel_rede',
                       'preco_mes_base': None}]}},
    }
    data.update(changes)
    return data


class ForecastViewTests(unittest.TestCase):
    """Keep the tab honest about origin, months and missing files."""

    def load(self, data):
        """Write a bundle to a temporary file and read it through the loader."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'previsao.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            return load_forecast(path)

    def test_missing_file_is_not_an_error(self) -> None:
        """An unpublished forecast shows a notice instead of failing."""
        self.assertIsNone(load_forecast(Path('/nonexistent/previsao.json')))

    def test_unknown_schema_is_rejected(self) -> None:
        """A future format cannot be read silently with old rules."""
        with self.assertRaisesRegex(ValueError, 'schema'):
            self.load(bundle(schema_version=2))

    def test_forecast_must_point_forward(self) -> None:
        """Predicting the base month itself would reuse the answer."""
        data = bundle()
        data['previsoes'][CAFE]['mes_previsto'] = '2026-10'
        with self.assertRaisesRegex(ValueError, 'later month'):
            self.load(data)

    def test_unknown_origin_is_rejected(self) -> None:
        """Every network forecast declares where its value came from."""
        data = bundle()
        data['previsoes'][CAFE]['redes'][0]['origem'] = 'palpite'
        with self.assertRaisesRegex(ValueError, 'Invalid forecast row'):
            self.load(data)

    def test_rows_show_origin_and_missing_base_price(self) -> None:
        """Model-based rows have no base-month price to display."""
        rows = forecast_rows(self.load(bundle())['previsoes'][CAFE])
        self.assertEqual(rows[0]['Preço estimado'], 'R$ 21,49')
        self.assertEqual(rows[1]['Como estimamos'], 'Estimado pelo padrão de preços da rede')
        self.assertEqual(rows[1]['Preço em outubro de 2026'], '—')

    def test_evaluation_uses_the_same_metrics(self) -> None:
        """Each model row carries the three comparison metrics."""
        row = evaluation_rows(bundle())[0]
        self.assertEqual(row['Período avaliado'], 'Teste')
        self.assertEqual(row['Erro percentual mediano'], '4,64%')

    def test_published_bundle_beats_the_network_baseline(self) -> None:
        """The versioned file covers the demo SKU and keeps the validated result."""
        data = load_forecast(FORECAST)
        self.assertIsNotNone(data)
        assert data is not None
        self.assertIn(CAFE, data['previsoes'])
        for stage in ('validacao', 'teste'):
            models = {row['modelo']: row for row in data['avaliacao'][stage]}
            self.assertLess(models['híbrido']['mae_brl'],
                            models['baseline 2: preço da rede no mês anterior']['mae_brl'])
        self.assertIn('diário de outubro', data['fonte'])
        cafe = data['previsoes'][CAFE]
        self.assertEqual((cafe['referencia_mes_base'], cafe['mediana_prevista']),
                         (26.59, 26.85))

    def test_evaluation_names_months_when_the_split_is_versioned(self) -> None:
        """Dates are taken from the evidence instead of hardcoding the demo year."""
        cuts = {'teste': {'treino_ate': '2026-07', 'avaliacao_ate': '2026-10'}}
        row = evaluation_rows(bundle(cortes=cuts))[0]
        self.assertEqual(row['Período avaliado'], 'Teste de agosto a outubro de 2026')


if __name__ == '__main__':
    unittest.main()
