"""The seasonal layer lists sourced dates and never claims the user's own sales."""
from datetime import date
import unittest

from tax_pricing.seasonal_calendar import load_calendar, sector_month, upcoming
from tax_pricing.source_search import find_sources, load_sources


class SeasonalCalendarTests(unittest.TestCase):
    """Calendar dates, product flags and sector figures."""

    def test_black_friday_flags_coffee_before_the_demo(self) -> None:
        """From 14/11/2026, Black Friday is next and its source names coffee."""
        events = upcoming(date(2026, 11, 14), group='Café', days=45)
        black_friday = [e for e in events if e['evento'] == 'Black Friday'][0]
        self.assertEqual(black_friday['inicio'], '2026-11-23')
        self.assertTrue(black_friday['cita_o_produto'])
        natal = [e for e in events if e['evento'] == 'Natal e Ano Novo'][0]
        self.assertFalse(natal['cita_o_produto'])

    def test_moveable_dates_are_computed(self) -> None:
        """Easter and Carnival follow the Easter rule in both years."""
        ends = {(e.name, e.end.year): e.end for e in load_calendar()}
        self.assertEqual(ends[('Páscoa', 2027)], date(2027, 3, 28))
        self.assertEqual(ends[('Carnaval', 2027)], date(2027, 2, 9))

    def test_every_event_cites_a_source_in_the_corpus(self) -> None:
        """No calendar row without a matching, linked excerpt."""
        corpus = {source['id']: source['url'] for source in load_sources()}
        for event in load_calendar():
            self.assertEqual(corpus[event.source_id], event.source_url)

    def test_december_is_the_strongest_sector_month(self) -> None:
        """IBGE: December is about 21% above the yearly mean in Paraná."""
        self.assertAlmostEqual(sector_month(12)['desvio_medio_pct'], 21.2)
        self.assertLess(sector_month(2)['desvio_medio_pct'], 0)

    def test_date_questions_find_their_own_source(self) -> None:
        """Each commemorative date is retrievable by the shopkeeper's wording."""
        cases = {'Dia das Mães vale a pena fazer ação no mercado?': 'saz_maes',
                 'O que vende mais na festa junina?': 'saz_junina',
                 'Na Black Friday compensa baixar o preço do óleo?': 'saz_black_friday',
                 'No Carnaval vende mais água?': 'saz_carnaval'}
        for question, expected in cases.items():
            result = find_sources(question)
            self.assertTrue(result.answerable, question)
            self.assertEqual(result.excerpts[0].source_id, expected, question)


if __name__ == '__main__':
    unittest.main()
