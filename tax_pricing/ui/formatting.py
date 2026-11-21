"""Brazilian presentation formatting, separate from financial arithmetic."""
from datetime import date
from decimal import Decimal
import re


MONTH_NAMES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
               'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')


_WORDS = {
    'Joao': 'João', 'Feijao': 'Feijão', 'Pe': 'Pé', 'Macarrao': 'Macarrão',
    'Com': 'com', 'De': 'de', 'Orquidea': 'Orquídea', 'Acucar': 'Açúcar',
    'Uniao': 'União', 'Cafe': 'Café', 'Vacuo': 'a Vácuo', 'Coracoes': 'Corações',
    'Pilao': 'Pilão', 'Guarana': 'Guaraná', 'Antartica': 'Antarctica',
    'Antártica': 'Antarctica', 'Agua': 'Água', 'Oleo': 'Óleo',
}
_UNITS = {'Kg': 'kg', 'Gr': 'g', 'Ml': 'ml', 'Litro': 'L', 'Litros': 'L'}
_NETWORKS = {'Armazem da Maria': 'Armazém da Maria', 'Rio verde': 'Rio Verde'}


def product_name(description: str) -> str:
    """Make catalog separators readable without changing product identity.

    Parameters
    ----------
    description : str
        Original catalog description.

    Returns
    -------
    str
        Display label with accents and units. The original catalog remains unchanged.
    """
    text = re.sub(r'\s*-\s*', ' · ', description.title())
    words = re.sub(r'\b(\w+)\b', lambda match: _WORDS.get(match.group(1), match.group(1)),
                   text).replace('Coca Cola', 'Coca-Cola')
    return re.sub(r'\b(\d+) (Kg|Gr|Ml|Litros?)\b',
                  lambda match: f'{match.group(1)} {_UNITS[match.group(2)]}', words)


def network_name(name: str) -> str:
    """Show network names in one consistent case without changing the data key."""
    text = name.title() if name.isupper() else name
    text = re.sub(r'(?<=\s)(E|De|Da|Do)\b', lambda match: match.group(1).lower(), text)
    return _NETWORKS.get(text, text)


def brl(value: Decimal | str) -> str:
    """Format a monetary value for display without altering stored precision.

    Parameters
    ----------
    value : Decimal or str
        Monetary value in BRL.

    Returns
    -------
    str
        Brazilian currency representation.
    """
    text = f'{Decimal(str(value)):,.2f}'
    return 'R$ ' + text.replace(',', '_').replace('.', ',').replace('_', '.')


def brl_markdown(value: Decimal | str) -> str:
    """Escape the currency symbol for Streamlit Markdown text."""
    return brl(value).replace('$', r'\$')


def percent(value: Decimal | str, signed: bool = False) -> str:
    """Format percentage points, optionally with a sign.

    Parameters
    ----------
    value : Decimal or str
        Percentage points, not a fraction.
    signed : bool
        Include a plus sign for a positive comparison.

    Returns
    -------
    str
        Localized percentage.
    """
    number = Decimal(str(value))
    text = f'{number:+.2f}' if signed else f'{number:.2f}'
    return text.replace('.', ',') + '%'


def display_date(value: str) -> str:
    """Format an ISO reference date for people reading the page.

    Parameters
    ----------
    value : str
        YYYY-MM-DD reference date.

    Returns
    -------
    str
        DD/MM/YYYY.
    """
    return date.fromisoformat(value).strftime('%d/%m/%Y')


def display_month(value: str) -> str:
    """Write a YYYY-MM reference as a month and year in Portuguese."""
    month = date.fromisoformat(f'{value}-01')
    return f'{MONTH_NAMES[month.month - 1]} de {month.year}'
