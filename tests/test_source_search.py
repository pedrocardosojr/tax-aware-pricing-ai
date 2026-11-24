"""Source retrieval must cite versioned files or refuse plainly."""
import unittest

from tax_pricing.source_search import (SearchResult, build_messages,
                                       citations_are_valid, find_sources,
                                       collapse_citations, load_sources,
                                       out_of_scope_reason, strip_fact_tags)


class SourceSearchTests(unittest.TestCase):
    """Behaviour the "why trust this reference?" answer depends on."""

    def test_demo_question_finds_the_cafe_method(self) -> None:
        """The Demo Day question must point to the store-median method."""
        result = find_sources('Por que a referência do Café Pilão é R$ 25,98 se '
                              'cada ponto do gráfico é uma rede?')
        self.assertTrue(result.answerable)
        self.assertEqual(result.excerpts[0].source_id, 'cafe_metodo')
        self.assertIn('/blob/', result.excerpts[0].url)

    def test_own_company_tax_is_refused(self) -> None:
        """Demonstrative profiles cannot answer the user's real tax."""
        result = find_sources('Qual é a alíquota de ICMS da minha empresa?')
        self.assertEqual(result.status, 'fora_do_escopo')
        self.assertIn('perfis demonstrativos', result.reason)

    def test_real_time_and_future_questions_are_refused(self) -> None:
        """Collected prices are dated; the app neither streams nor forecasts."""
        self.assertEqual(out_of_scope_reason('O café está em promoção hoje?'), 'tempo_real')
        self.assertEqual(out_of_scope_reason('Quanto vai custar em dezembro?'), 'previsao')
        self.assertIsNone(out_of_scope_reason('Faz sentido promoção em dezembro?'))
        self.assertIsNone(out_of_scope_reason('O que acontece com a minha margem se eu '
                                              'subir o preço?'))

    def test_unrelated_question_has_no_evidence(self) -> None:
        """Without a shared content word, character fragments are not enough."""
        result = find_sources('Quem ganhou a última eleição para governador?')
        self.assertFalse(result.answerable)
        self.assertEqual(result.excerpts, ())

    def test_every_source_is_complete_and_pinned(self) -> None:
        """Project links point to a fixed commit; external ones keep a local copy."""
        sources = load_sources()
        self.assertEqual(len({source['id'] for source in sources}), len(sources))
        for source in sources:
            if source.get('external'):
                self.assertTrue(source['url'].startswith('https://'))
                self.assertTrue(source['id'].startswith('saz_'))
            else:
                self.assertRegex(source['url'], r'/blob/[0-9a-f]{40}/')

    def test_seasonality_is_answered_as_sector_suggestion(self) -> None:
        """A December promotion question finds the IBGE sector data, not a forecast."""
        result = find_sources('Vale a pena fazer promoção em dezembro?')
        self.assertTrue(result.answerable)
        self.assertTrue(result.excerpts[0].source_id.startswith('saz_'))
        messages = build_messages('Vale a pena?', {}, result)
        self.assertIn('nunca como previsão', messages[0]['content'])

    def test_trust_questions_find_the_matching_source(self) -> None:
        """Trust in prices, taxes and the written explanation each has its own source."""
        expected = {'Posso confiar nesses dados?': 'clique_origem',
                    'Posso confiar no imposto?': 'premissas_tributarias',
                    'Posso confiar na explicação da IA?': 'validador'}
        for question, source_id in expected.items():
            with self.subTest(question=question):
                self.assertEqual(find_sources(question).excerpts[0].source_id, source_id)

    def test_prompt_carries_only_facts_and_excerpts(self) -> None:
        """The model sees the calculated values and the retrieved text, nothing else."""
        result = find_sources('Por que a referência é por loja se o gráfico mostra redes?')
        messages = build_messages('Por que por loja?', {'mediana por loja': 'R$ 25,98'},
                                  result)
        self.assertEqual([message['role'] for message in messages], ['system', 'user'])
        self.assertIn('R$ 25,98', messages[1]['content'])
        self.assertIn('[cafe_metodo]', messages[1]['content'])

    def test_citations_must_come_from_the_retrieved_sources(self) -> None:
        """An answer citing nothing, or an unretrieved source, is rejected."""
        result = find_sources('Por que a referência é por loja se o gráfico mostra redes?')
        self.assertTrue(citations_are_valid('Usa a mediana das lojas [cafe_metodo].',
                                            result))
        self.assertFalse(citations_are_valid('Usa a mediana das lojas.', result))
        self.assertFalse(citations_are_valid('Veja [validador].', result))
        self.assertFalse(citations_are_valid('[cafe_metodo]', SearchResult('sem_evidencia')))

    def test_fact_tags_are_not_sources(self) -> None:
        """A tag naming a calculated fact is ignored and removed for display."""
        result = find_sources('Por que a referência é por loja se o gráfico mostra redes?')
        answer = 'Usa as lojas [cafe_metodo]. Sobram R$ 3,56 [contribution].'
        self.assertTrue(citations_are_valid(answer, result))
        self.assertFalse(citations_are_valid('Sobram R$ 3,56 [contribution].', result))
        context_answer = 'Amostra do cenário [reference]. Método por loja [cafe_metodo].'
        self.assertTrue(citations_are_valid(context_answer, result))
        self.assertFalse(citations_are_valid('Amostra do cenário [reference].', result))
        self.assertEqual(strip_fact_tags(context_answer),
                         'Amostra do cenário. Método por loja [cafe_metodo].')
        self.assertEqual(strip_fact_tags(answer),
                         'Usa as lojas [cafe_metodo]. Sobram R$ 3,56.')

    def test_shown_answer_has_no_internal_tags_or_repeated_markers(self) -> None:
        """Grouped fact tags disappear; one marker closes each run of a source."""
        self.assertEqual(strip_fact_tags('Custo com ST [tax, purchase_st]. Perfil [1].'),
                         'Custo com ST. Perfil [1].')
        self.assertEqual(collapse_citations('A [1]. B [1]. C [2]. D [1].\nE [1]. F [1].'),
                         'A. B [1]. C [2]. D [1].\nE. F [1].')


if __name__ == '__main__':
    unittest.main()
