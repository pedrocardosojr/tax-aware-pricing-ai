"""Weather forecast is context only and degrades quietly."""
import json
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from tax_pricing.weather import describe, fetch_forecast, fetch_inmet_forecast, parse_forecast

PAYLOAD = {'daily': {'time': ['2026-11-14', '2026-11-15'], 'weather_code': [0, 95],
                     'temperature_2m_max': [26.2, 25.8], 'temperature_2m_min': [15.0, 17.2],
                     'precipitation_probability_max': [None, 100]}}


class WeatherTests(unittest.TestCase):
    """Parsing, icons and the fallback when the service is down."""

    def test_codes_have_icons(self):
        """Known codes get a label; unknown ones a neutral one."""
        self.assertEqual(describe(0)[1], 'Céu limpo')
        self.assertEqual(describe(95)[1], 'Tempestade')
        self.assertEqual(describe(999)[1], 'Sem descrição')

    def test_parse_rounds_and_names_days(self):
        """Temperatures are rounded and days named in Portuguese."""
        days = parse_forecast(PAYLOAD)
        self.assertIsNone(days[0]['chuva'])
        self.assertEqual([day['dia'] for day in days], ['sáb', 'dom'])
        self.assertEqual((days[0]['maxima'], days[0]['minima'], days[1]['chuva']), (26, 15, 100))

    def test_service_down_returns_none(self):
        """A network error returns None; a valid answer is parsed."""
        with patch('tax_pricing.weather.urlopen', side_effect=OSError):
            self.assertIsNone(fetch_forecast())
        with patch('tax_pricing.weather.urlopen') as call:
            call.return_value.__enter__.return_value.read.return_value = json.dumps(
                PAYLOAD).encode()
            self.assertEqual(len(fetch_forecast() or []), 2)

    def test_inmet_supports_daily_and_period_forecasts(self):
        """The first days have period data; later dates expose daily fields."""
        today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
        first, second = (today.strftime('%d/%m/%Y'),
                         (today + timedelta(days=1)).strftime('%d/%m/%Y'))
        forecast = {'4106902': {
            first: {'manha': {'temp_max': 26, 'temp_min': 16, 'resumo': 'Nublado'},
                    'tarde': {'temp_max': 28, 'temp_min': 17, 'resumo': 'Chuva'}},
            second: {'temp_max': 27, 'temp_min': 15, 'resumo': 'Nublado'},
        }}
        with patch('tax_pricing.weather.urlopen') as call:
            call.return_value.__enter__.return_value.read.return_value = json.dumps(
                forecast).encode()
            days = fetch_inmet_forecast() or []
        self.assertEqual([(row['maxima'], row['minima'], row['chuva']) for row in days],
                         [(28, 16, None), (27, 15, None)])
        self.assertEqual(days[0]['descricao'], 'Nublado / Chuva')


if __name__ == '__main__':
    unittest.main()
