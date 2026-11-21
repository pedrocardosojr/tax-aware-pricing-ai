"""Seven-day weather forecast for Curitiba from Open-Meteo (free, no key).

Context only: the app never uses the forecast in any calculation.
"""
import json
from datetime import date, datetime
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

FORECAST_URL = ('https://api.open-meteo.com/v1/forecast?latitude=-25.43&longitude=-49.27'
                '&daily=weather_code,temperature_2m_max,temperature_2m_min,'
                'precipitation_probability_max&timezone=America%2FSao_Paulo&forecast_days=7')
SOURCE_URL = 'https://open-meteo.com/'
INMET_FORECAST_URL = 'https://apiprevmet3.inmet.gov.br/previsao/4106902'
INMET_SOURCE_URL = 'https://tempo.inmet.gov.br/'
WEEKDAYS = ('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')
# WMO weather interpretation codes grouped into what a shopkeeper cares about.
CODES = (
    ((0,), '☀️', 'Céu limpo'),
    ((1, 2), '🌤️', 'Poucas nuvens'),
    ((3,), '☁️', 'Nublado'),
    ((45, 48), '🌫️', 'Neblina'),
    ((51, 53, 55, 56, 57), '🌦️', 'Garoa'),
    ((61, 63, 65, 66, 67, 80, 81, 82), '🌧️', 'Chuva'),
    ((71, 73, 75, 77, 85, 86), '❄️', 'Neve'),
    ((95, 96, 99), '⛈️', 'Tempestade'),
)


def describe(code: int) -> tuple[str, str]:
    """Icon and short label for a WMO weather code."""
    for codes, icon, label in CODES:
        if code in codes:
            return icon, label
    return '🌡️', 'Sem descrição'


def parse_forecast(payload: dict) -> list[dict]:
    """Turn the Open-Meteo daily block into one row per day."""
    daily = payload['daily']
    days = []
    for index, day in enumerate(daily['time']):
        when = date.fromisoformat(day)
        icon, label = describe(int(daily['weather_code'][index]))
        chance = daily['precipitation_probability_max'][index]
        days.append({'data': when, 'dia': WEEKDAYS[when.weekday()], 'icone': icon,
                     'descricao': label,
                     'maxima': round(float(daily['temperature_2m_max'][index])),
                     'minima': round(float(daily['temperature_2m_min'][index])),
                     'chuva': int(chance) if chance is not None else None})
    return days


def fetch_forecast(timeout: float = 5) -> list[dict] | None:
    """Next seven days, or None when the service does not answer."""
    try:
        with urlopen(FORECAST_URL, timeout=timeout) as response:
            return parse_forecast(json.loads(response.read(65536)))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None


def fetch_inmet_forecast(timeout: float = 5) -> list[dict] | None:
    """Read the official daily fallback from INMET for Curitiba."""
    request = Request(INMET_FORECAST_URL, headers={
        'Accept': 'application/json',
        'User-Agent': 'Tax-Aware Pricing AI (https://tax-pricing-ai.streamlit.app/)',
    })
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    try:
        with urlopen(request, timeout=timeout) as response:
            days = json.loads(response.read(1024 * 1024))['4106902']
        forecast = []
        dated_days = {datetime.strptime(day, '%d/%m/%Y').date(): values
                      for day, values in days.items()}
        for when, values in sorted(dated_days.items()):
            if when < today:
                continue
            periods = [values] if 'temp_max' in values else [
                period for period in values.values()
                if isinstance(period, dict) and 'temp_max' in period]
            if periods:
                forecast.append({
                    'data': when, 'dia': WEEKDAYS[when.weekday()], 'icone': '🌡️',
                    'descricao': ' / '.join(dict.fromkeys(str(p['resumo']) for p in periods)),
                    'maxima': max(int(p['temp_max']) for p in periods),
                    'minima': min(int(p['temp_min']) for p in periods), 'chuva': None,
                })
        return forecast[:5] or None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
