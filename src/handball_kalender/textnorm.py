"""Normalisierung von Text für Hallen- und Namensvergleiche (SPEC.md Abschnitt 8/9)."""

import re
import unicodedata

_UMLAUT_MAP = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    """Lowercase, Umlaute transliterieren (ue/oe/ae/ss), Sonderzeichen und
    Leerzeichen entfernen. Wird sowohl auf Hallen-Suchbegriffe als auch auf
    Eingabetext angewandt, damit beide Seiten unabhängig von ihrer
    Rohschreibweise vergleichbar sind.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_UMLAUT_MAP)
    text = text.lower()
    return _NON_ALNUM.sub("", text)
