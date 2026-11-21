"""Upcoming retail dates for a product group, each tied to its public source.

The calendar is a suggestion layer: it says which dates are coming and what sector
research reports for them. It never forecasts the user's own sales.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

EXTERNAL_DIR = Path(__file__).resolve().parents[1] / 'dados' / 'externo'
CALENDAR_PATH = EXTERNAL_DIR / 'calendario_varejo_2026_2027.csv'
SECTOR_PATH = EXTERNAL_DIR / 'ibge_pmc_pr_supermercados_sazonalidade.csv'
SECTOR_SOURCE = 'https://sidra.ibge.gov.br/tabela/8882'
MONTHS = ('jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez')


@dataclass(frozen=True)
class RetailDate:
    """One commemorative date, season or holiday in the calendar."""

    start: date
    end: date
    name: str
    kind: str
    source_id: str
    groups: tuple[str, ...]
    source_url: str

    def overlaps(self, first: date, last: date) -> bool:
        """True when any day of the event falls between first and last."""
        return self.start <= last and self.end >= first


@lru_cache(maxsize=1)
def load_calendar(path: Path = CALENDAR_PATH) -> tuple[RetailDate, ...]:
    """Read the versioned calendar; groups are only those a source names."""
    with path.open(encoding='utf-8', newline='') as handle:
        return tuple(
            RetailDate(date.fromisoformat(row['inicio']), date.fromisoformat(row['fim']),
                       row['evento'], row['tipo'], row['fonte_id'],
                       tuple(group for group in row['grupos_do_catalogo'].split(';') if group),
                       row['fonte_url'])
            for row in csv.DictReader(handle))


def upcoming(today: date, group: str | None = None, days: int = 90) -> list[dict[str, object]]:
    """Dates from today to today + days, flagging those whose source names the group."""
    last = today + timedelta(days=days)
    return [{'evento': event.name, 'tipo': event.kind,
             'inicio': event.start.isoformat(), 'fim': event.end.isoformat(),
             'cita_o_produto': group is not None and group in event.groups,
             'fonte_id': event.source_id, 'fonte_url': event.source_url}
            for event in load_calendar() if event.overlaps(today, last)]


@lru_cache(maxsize=1)
def sector_by_month(path: Path = SECTOR_PATH) -> dict[str, dict[str, float]]:
    """IBGE supermarket volume in Paraná, deviation of each month from its yearly mean."""
    with path.open(encoding='utf-8', newline='') as handle:
        return {row['mes']: {'desvio_medio_pct': float(row['desvio_medio_pct']),
                             'min_pct': float(row['min_pct']),
                             'max_pct': float(row['max_pct'])}
                for row in csv.DictReader(handle)}


def sector_month(month: int) -> dict[str, object]:
    """The IBGE figure for one month, with its source, for the seasonal chart."""
    name = MONTHS[month - 1]
    return {'mes': name, **sector_by_month()[name], 'fonte_url': SECTOR_SOURCE}


CLIMATE_PATH = EXTERNAL_DIR / 'inmet_normais_1991_2020_curitiba.csv'
CLIMATE_SOURCE = 'https://portal.inmet.gov.br/normais'


@lru_cache(maxsize=1)
def climate_by_month(path: Path = CLIMATE_PATH) -> dict[str, dict[str, float]]:
    """INMET 1991–2020 climate normals for Curitiba, by month."""
    with path.open(encoding='utf-8', newline='') as handle:
        return {row['mes']: {'media': float(row['temp_media_c']),
                             'maxima': float(row['temp_max_c']),
                             'minima': float(row['temp_min_c'])}
                for row in csv.DictReader(handle)}


def climate_month(month: int) -> dict[str, object]:
    """Average, maximum and minimum temperature of one month, with source."""
    name = MONTHS[month - 1]
    return {'mes': name, **climate_by_month()[name], 'fonte_url': CLIMATE_SOURCE}
