"""Brazilian presentation formatting, separate from financial arithmetic."""
from datetime import date
from decimal import Decimal
import re


MONTH_NAMES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
               'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')


def product_name(description: str) -> str:
    """Make catalog separators readable without changing product identity.

    Parameters
    ----------
    description : str
        Original catalog description.

    Returns
    -------
    str
        Display label. The original catalog remains unchanged.
    """
    return re.sub(r'\s*-\s*', ' · ', description.title())


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
