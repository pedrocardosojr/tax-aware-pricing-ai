"""Find the versioned project sources that explain a price reference.

The retrieval step of the "why should I trust this reference?" answer. Values and
coverage always come from the calculation; this module only returns the method
excerpts and links that support an explanation, or an explicit refusal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

SOURCES_PATH = Path(__file__).with_name('fontes_ia.json')
MIN_SCORE = 0.12
MAX_EXCERPTS = 2
SECOND_EXCERPT_RATIO = 0.8

STOP_WORDS = ['que', 'qual', 'quais', 'como', 'quanto', 'quantas', 'esse', 'essa',
              'esses', 'essas', 'para', 'uma', 'um', 'com', 'dos', 'das', 'por',
              'onde', 'de', 'do', 'da', 'o', 'a', 'os', 'as', 'e', 'se', 'no',
              'na', 'em', 'eu', 'é', 'quem', 'última', 'último', 'ano']

# Questions the project cannot answer from its sources, whatever the wording scores.
REAL_TIME = re.compile(r'\b(hoje|agora|neste momento|estoque|em promocao)\b')
TAX_TERMS = re.compile(r'\b(aliquota|icms|imposto|impostos|tributo|tributos|pis|'
                       r'cofins|credito|das|faturamento)\b')
FORECAST_ASK = re.compile(r'\b(quanto|qual sera|qual vai ser|preco|inflacao|cotacao|vai custar|'
                          r'vai cobrar|vai chover|chuva)\b')
OWN_COMPANY = re.compile(r'\b(minha|meu|minhas|meus|nossa|nosso|eu pago|vou pagar)\b')
FUTURE_DATE = re.compile(r'\b(em|ate) (janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|'
                         r'setembro|outubro|novembro|dezembro)\b|\b20(2[7-9]|3\d)\b|'
                         r'\bamanha\b|\bano que vem\b|\bproximo (mes|ano)\b')

REFUSALS = {
    'tempo_real': ('O app usa preços já coletados, com data da última coleta. '
                   'Não consulta preço, promoção ou estoque em tempo real.'),
    'dados_da_empresa': ('A tributação do app usa perfis demonstrativos por regime. '
                         'Não tem os dados fiscais da sua empresa; para a carga real, '
                         'consulte a sua contabilidade.'),
    'previsao': ('O app não prevê preços, vendas ou indicadores futuros. Mostra preços '
                 'já coletados e simula cenários com as premissas da tela.'),
    'sem_evidencia': 'Não encontrei essa informação nas fontes disponíveis.',
}


@dataclass(frozen=True)
class Excerpt:
    """One versioned source that supports an answer."""

    source_id: str
    title: str
    url: str
    text: str
    score: float


@dataclass(frozen=True)
class SearchResult:
    """Excerpts to cite, or the reason the question must be refused."""

    status: str
    reason: str = ''
    excerpts: tuple[Excerpt, ...] = field(default_factory=tuple)

    @property
    def answerable(self) -> bool:
        """True when there is at least one source to ground an answer."""
        return self.status == 'ok'


def normalize(text: str) -> str:
    """Lowercase and drop accents so 'referência' matches 'referencia'."""
    decomposed = unicodedata.normalize('NFKD', text.casefold())
    return ''.join(char for char in decomposed if not unicodedata.combining(char))


def out_of_scope_reason(question: str) -> str | None:
    """Return the refusal key for questions the sources can never support."""
    text = normalize(question)
    if REAL_TIME.search(text):
        return 'tempo_real'
    if TAX_TERMS.search(text) and OWN_COMPANY.search(text):
        return 'dados_da_empresa'
    if FUTURE_DATE.search(text) and FORECAST_ASK.search(text):
        return 'previsao'
    return None


def load_sources(path: Path = SOURCES_PATH) -> tuple[dict[str, str], ...]:
    """Read the curated corpus; every entry needs id, title, url and text."""
    sources = json.loads(path.read_text(encoding='utf-8'))
    required = {'id', 'title', 'url', 'text'}
    for source in sources:
        missing = required - set(source)
        if missing:
            raise ValueError(f"fonte sem campos {sorted(missing)}: {source}")
    return tuple(sources)


class SourceIndex:
    """TF-IDF over words and character fragments, robust to Portuguese inflection."""

    def __init__(self, sources: tuple[dict[str, str], ...]) -> None:
        self.sources = sources
        self.vectorizer = FeatureUnion([
            ('palavras', TfidfVectorizer(preprocessor=normalize, ngram_range=(1, 2),
                                         stop_words=[normalize(w) for w in STOP_WORDS])),
            ('fragmentos', TfidfVectorizer(preprocessor=normalize, analyzer='char_wb',
                                           ngram_range=(4, 5))),
        ])
        self.matrix = self.vectorizer.fit_transform(
            [f"{source['title']} {source['text']} {source.get('terms', '')}"
             for source in sources])
        self.word_block = self.vectorizer.transformer_list[0][1]

    def scores(self, question: str) -> list[float]:
        """Cosine similarity of the question against each source."""
        query = self.vectorizer.transform([question])
        # Each block is L2-normalised, so halve the sum to keep scores in [0, 1].
        return [float(value) / 2 for value in (query @ self.matrix.T).toarray()[0]]

    def shares_words(self, question: str) -> bool:
        """Character fragments alone do not justify a source: one content word must match."""
        return self.word_block.transform([question]).nnz > 0

    def search(self, question: str, min_score: float = MIN_SCORE) -> SearchResult:
        """Return up to two supporting excerpts, or why there are none."""
        reason = out_of_scope_reason(question)
        if reason:
            return SearchResult(status='fora_do_escopo', reason=REFUSALS[reason])
        ranked = sorted(enumerate(self.scores(question)), key=lambda item: -item[1])
        best_score = ranked[0][1]
        if best_score < min_score or not self.shares_words(question):
            return SearchResult(status='sem_evidencia', reason=REFUSALS['sem_evidencia'])
        excerpts = []
        for position, score in ranked[:MAX_EXCERPTS]:
            if score < min_score or score < best_score * SECOND_EXCERPT_RATIO:
                break
            source = self.sources[position]
            excerpts.append(Excerpt(source['id'], source['title'], source['url'],
                                    source['text'], round(score, 4)))
        return SearchResult(status='ok', excerpts=tuple(excerpts))


@lru_cache(maxsize=1)
def default_index() -> SourceIndex:
    """Index built once from the versioned corpus."""
    return SourceIndex(load_sources())


def find_sources(question: str) -> SearchResult:
    """Entry point for the app: excerpts and links for a user question."""
    return default_index().search(question)


def build_messages(question: str, facts: dict[str, str],
                   result: SearchResult) -> list[dict[str, str]]:
    """Prompt for a model that may only use the calculated facts and the excerpts."""
    excerpts = '\n'.join(f"[{item.source_id}] {item.title}: {item.text}"
                         for item in result.excerpts)
    calculated = '\n'.join(f"- {name}: {value}" for name, value in facts.items())
    system = ('Você explica a referência de preço de um app para lojistas. '
              'Use apenas números dos fatos calculados e dos trechos. Só afirme o que '
              'os trechos sustentam. Cite a fonte de cada afirmação com o id entre '
              'colchetes, por exemplo [cafe_metodo]. Colchetes servem só para os ids '
              'dos trechos: não marque os fatos calculados com colchetes. Se os '
              'trechos não respondem, '
              'diga que não há evidência nas fontes consultadas. Trechos de sazonalidade '
              '(ids saz_) são do setor, do clima ou de pesquisas de mercado: apresente '
              'como sugestão, nunca como previsão para a loja ou para o produto. '
              'Dados de bebidas não descrevem café ou outros produtos. '
              'Ao falar de tributos, use o regime e as premissas do produto selecionado '
              'nos fatos. ICMS-ST só é assumido quando o fato purchase_st o confirma. '
              'Responda à pergunta e evite repetir margem, preço ou datas sem necessidade. '
              'Máximo de 4 frases.')
    user = (f"Pergunta: {question}\n\nFatos calculados:\n{calculated}\n\n"
            f"Trechos recuperados:\n{excerpts}")
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]


CITATION = re.compile(r'\[([a-z_]+)\]')
# Names of the calculated facts; the model sometimes tags them like sources.
FACT_TAGS = frozenset({'contribution', 'position', 'action', 'season',
                       'product', 'tax', 'purchase_st', 'reference'})


def citations_are_valid(answer: str, result: SearchResult) -> bool:
    """An answer must cite at least one retrieved source and nothing else.

    Tags naming a calculated fact are not sources and are ignored here; the
    screen removes them with ``strip_fact_tags`` before showing the answer.
    """
    cited = set(CITATION.findall(answer)) - FACT_TAGS
    allowed = {item.source_id for item in result.excerpts}
    return bool(cited) and cited <= allowed


def strip_fact_tags(answer: str) -> str:
    """Remove tags such as [contribution] that point to a calculated fact."""
    return re.sub(r'\s*\[(' + '|'.join(sorted(FACT_TAGS)) + r')\]', '', answer)
