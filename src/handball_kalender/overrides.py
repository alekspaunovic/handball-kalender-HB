"""Manuelle Eingriffe aus overrides.json lesen (SPEC-ADMIN.md Abschnitt 5).

Die Datei wird ausschliesslich von der Admin-Oberflaeche geschrieben, hier nur
gelesen. Sie darf das Erzeugen der Feeds nie verhindern: fehlt sie oder ist sie
kaputt, wird mit leeren Listen weitergearbeitet und gewarnt.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from . import watch as watch_mod

logger = logging.getLogger(__name__)

# Pflichtfelder eines eigenen Termins. created wird von der Oberflaeche
# gesetzt, ist fuer den Feed aber nicht noetig.
_CUSTOM_REQUIRED = ("uid", "summary", "dtstart", "dtend")


@dataclass(frozen=True)
class Overrides:
    hidden: set[str] = field(default_factory=set)
    custom: list[dict] = field(default_factory=list)
    included: set[str] = field(default_factory=set)
    watch: set[str] = field(default_factory=set)


def _string_set(raw, name: str) -> set[str]:
    if not isinstance(raw, list):
        if raw is not None:
            logger.warning("overrides.json: %r ist keine Liste, wird ignoriert", name)
        return set()
    return {item for item in raw if isinstance(item, str) and item}


def _custom_list(raw) -> list[dict]:
    if not isinstance(raw, list):
        if raw is not None:
            logger.warning("overrides.json: 'custom' ist keine Liste, wird ignoriert")
        return []

    entries = []
    for item in raw:
        if not isinstance(item, dict):
            logger.warning("overrides.json: Eintrag in 'custom' ist kein Objekt, wird übersprungen")
            continue
        fehlend = [key for key in _CUSTOM_REQUIRED if not item.get(key)]
        if fehlend:
            logger.warning(
                "overrides.json: eigener Termin %r ohne %s, wird übersprungen",
                item.get("uid", "?"),
                ", ".join(fehlend),
            )
            continue
        entries.append(item)
    return entries


def _watch_set(raw) -> set[str]:
    """Spielnummern gemerkter Spiele. Die App schreibt nur die nackte Zahl,
    aber eine von Hand eingetragene Spiel-Adresse oder ein ICS-Link werden
    genauso akzeptiert -- dieselben drei Formen wie in der Oberfläche."""
    nummern = set()
    for eintrag in _string_set(raw, "watch"):
        mid = watch_mod.match_id(eintrag)
        if mid is None:
            logger.warning(
                "overrides.json: %r in 'watch' ist keine Spielnummer und keine "
                "handball.net-Adresse, wird übersprungen",
                eintrag,
            )
            continue
        nummern.add(mid)
    return nummern


def parse(raw: object) -> Overrides:
    if not isinstance(raw, dict):
        logger.warning("overrides.json enthält kein Objekt, wird ignoriert")
        return Overrides()

    return Overrides(
        hidden=_string_set(raw.get("hidden"), "hidden"),
        custom=_custom_list(raw.get("custom")),
        included=_string_set(raw.get("included"), "included"),
        watch=_watch_set(raw.get("watch")),
    )


def load(path: str | Path) -> Overrides:
    path = Path(path)
    if not path.exists():
        logger.warning(
            "%s fehlt, es werden keine manuellen Eingriffe angewendet", path
        )
        return Overrides()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning(
            "%s ist nicht lesbar oder kein gültiges JSON, es werden keine "
            "manuellen Eingriffe angewendet",
            path,
            exc_info=True,
        )
        return Overrides()

    return parse(raw)
