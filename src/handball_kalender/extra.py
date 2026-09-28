"""docs/extra.ics erzeugen (SPEC-ADMIN.md Abschnitt 4).

Ein einzelner Feed fuer beides: die eigenen Termine aus `custom` und die von
Hand freigeschalteten Fremdspiele aus `included`.

Freigeschaltete Fremdspiele werden aus dem Archiv gelesen, nicht kopiert. Sie
bleiben damit an ihre Quelle gekoppelt: verlegt der Verband ein Spiel,
verschiebt sich der Termin mit, und wird es zurueckgezogen, greift die normale
Absage-Logik inklusive ABGESAGT-Praefix.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import Hall
from .halls import find_hall, hall_address
from .overrides import Overrides

logger = logging.getLogger(__name__)


def _localized_iso(value: str, tz_name: str) -> str:
    """Die Oberflaeche schickt Ortszeit ohne Zonenangabe ("2026-11-14T19:00:00").
    Ohne explizite Zone wuerde sie spaeter als Zeit des ausfuehrenden Rechners
    gelesen -- auf einem GitHub-Runner also als UTC, womit der Termin zwei
    Stunden verrutscht."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    return dt.isoformat()


def _custom_entry(item: dict, halls: list[Hall], tz_name: str) -> dict | None:
    all_day = bool(item.get("all_day"))

    try:
        if all_day:
            dtstart = str(item["dtstart"])[:10]
            dtend = str(item["dtend"])[:10]
        else:
            dtstart = _localized_iso(str(item["dtstart"]), tz_name)
            dtend = _localized_iso(str(item["dtend"]), tz_name)
    except ValueError:
        logger.warning(
            "Eigener Termin %r hat keine lesbare Datumsangabe, wird übersprungen",
            item.get("uid"),
        )
        return None

    # Ist der Ort eine bekannte Halle, gewinnt die Schreibweise aus halls.yaml
    # -- samt Koordinaten, damit Apple die Navigation anbietet.
    location = item.get("location") or None
    geo = None
    if location:
        hall = find_hall(halls, location)
        if hall:
            location = hall_address(hall)
            geo = list(hall.geo) if hall.geo else None

    return {
        "uid": item["uid"],
        "source_uid": item["uid"],
        "summary": item["summary"],
        "dtstart": dtstart,
        "dtend": dtend,
        "all_day": all_day,
        "location": location,
        "geo": geo,
        "description": item.get("description") or "",
        "url": "",
        "cancelled": False,
    }


def build_entries(
    overrides: Overrides,
    archives: dict[str, list[dict]],
    halls: list[Hall],
    tz_name: str,
    watch_feed_key: str = "watch-spiele",
) -> list[dict]:
    """`archives` bildet feed_key auf die gemergten Archiveintraege ab.

    Drei Sorten (SPEC-ADMIN.md Abschnitt 4): eigene Termine, freigeschaltete
    Fremdspiele und gemerkte Spiele. Die `hidden`-Filterung passiert nicht
    hier, sondern beim Schreiben -- einheitlich fuer alle Feeds.
    """
    entries = []

    for item in overrides.custom:
        entry = _custom_entry(item, halls, tz_name)
        if entry is not None:
            entries.append(entry)

    by_uid = {
        entry["uid"]: entry
        for entries_of_feed in archives.values()
        for entry in entries_of_feed
    }
    for uid in sorted(overrides.included):
        entry = by_uid.get(uid)
        if entry is None:
            logger.warning(
                "Freigeschalteter Termin %r steht in keinem Archiv und kommt "
                "nicht in den Extra-Feed",
                uid,
            )
            continue
        entries.append(entry)

    # Gemerkte Spiele kommen vollstaendig aus ihrem Archiv -- jedes, das dort
    # steht, war einmal gemerkt und bleibt dauerhaft erhalten. Abgeschaltet
    # wird ueber `hidden`, nicht durch Entfernen.
    entries.extend(archives.get(watch_feed_key, []))

    return entries
