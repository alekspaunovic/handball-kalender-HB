"""Gemerkte Spiele beliebiger Vereine (SPEC-ADMIN.md Abschnitt 3).

Quelle ist ein Abruf pro Spiel:

    https://www.handball.net/kalender/spiel/<spielnummer>.ics

Anders als bei den Team-Feeds ist hier kein eigenes Team beteiligt. Es gibt
deshalb kein Heim und kein Auswärts, keinen Treffpunkt und keinen Vorsatz im
Titel -- nur die beiden Vereine.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from .config import Hall
from .ics_io import extract_geo, extract_location, localize_naive
from .models import Event
from .names import normalize_opponent
from .spiele import parse_status, resolve_location, split_summary

logger = logging.getLogger(__name__)

# Die drei Eingabeformen aus SPEC-ADMIN.md Abschnitt 6. Gemeint ist immer die
# Zahl aus der Adresse, nicht die Spielnummer des Verbands.
_MATCH_ID_RES = (
    re.compile(r"handball\.net/kalender/spiel/(\d+)\.ics", re.IGNORECASE),
    re.compile(r"handball\.net/match/(\d+)", re.IGNORECASE),
    re.compile(r"^(\d+)$"),
)


def match_id(text: str) -> str | None:
    """Zieht die Spielnummer aus Spiel-Adresse, ICS-Link oder nackter Zahl.
    Gibt None zurück, wenn keine der drei Formen passt."""
    text = (text or "").strip()
    for muster in _MATCH_ID_RES:
        treffer = muster.search(text)
        if treffer:
            return treffer.group(1)
    return None


def match_url(mid: str) -> str:
    return f"https://www.handball.net/kalender/spiel/{mid}.ics"


def liga(description: str) -> str:
    """Die Liga steht in der ersten Zeile der DESCRIPTION, danach folgen
    Spieltag, Spielnummer, Statuswort und Link."""
    for zeile in (description or "").splitlines():
        zeile = zeile.strip()
        if zeile:
            return zeile
    return ""


def transform(
    vevent,
    mid: str,
    halls: list[Hall],
    opponent_overrides: dict[str, str],
    uid_prefix: str,
    tz_name: str,
    spieldauer_minuten: int,
) -> Event:
    source_uid = str(vevent["UID"])
    raw_summary = str(vevent["SUMMARY"])
    raw_description = str(vevent.get("DESCRIPTION", ""))

    # Beide Seiten werden gleich behandelt -- es gibt keine eigene Seite.
    # Kennungen bleiben stehen, sie sind hier die einzige Unterscheidung.
    heim_seite, gast_seite, _ergebnis = split_summary(raw_summary)
    heim = normalize_opponent(heim_seite, opponent_overrides, strip_team_suffix=False)
    gast = normalize_opponent(gast_seite, opponent_overrides, strip_team_suffix=False)

    final_location, final_geo, _ist_heim = resolve_location(halls, extract_location(vevent))
    if final_geo is None:
        final_geo = extract_geo(vevent)

    dtstart_raw = vevent["DTSTART"].dt
    all_day = not isinstance(dtstart_raw, datetime)

    if all_day:
        dtstart: datetime | date = dtstart_raw
        dtend: datetime | date = vevent["DTEND"].dt
    else:
        dtstart = localize_naive(dtstart_raw, tz_name)
        # Die Endzeit der Quelle ist immer Anwurf plus zwei Stunden und damit
        # nicht brauchbar (SPEC.md Abschnitt 6).
        dtend = dtstart + timedelta(minutes=spieldauer_minuten)

    status = parse_status(raw_description)
    cancelled = status == "Retirado"

    # Notiz: ausschliesslich die Liga, kein Treffpunkt und kein Ergebnis.
    notiz_lines = ["Uhrzeit noch offen"] if all_day else []
    liga_name = liga(raw_description)
    if liga_name:
        notiz_lines.append(liga_name)

    title = f"{heim} - {gast}"
    if cancelled:
        title = f"ABGESAGT {title}"

    return Event(
        uid=f"{uid_prefix}-watch-spiel-{mid}",
        source_uid=source_uid,
        summary=title,
        dtstart=dtstart,
        dtend=dtend,
        all_day=all_day,
        location=final_location,
        geo=final_geo,
        description="\n".join(notiz_lines),
        url=str(vevent.get("URL", "")),
        cancelled=cancelled,
    )
