"""Transformation von handball.net-Spielen (SPEC.md Abschnitt 6 + 7)."""

from __future__ import annotations

import dataclasses
import logging
import re
from datetime import date, datetime, timedelta

from .config import Hall, TeamConfig
from .halls import find_hall, hall_address
from .ics_io import calendar_name, extract_geo, extract_location, localize_naive
from .models import Event
from .names import clean_handballnet_address, normalize_opponent

logger = logging.getLogger(__name__)

_RESULT_RE = re.compile(r"\s*\((\d+:\d+)\)\s*$")
_SOURCE_ID_RE = re.compile(r"spiel-(\d+)@")

_STATUS_WORDS = {"Pendiente", "Finalizado", "Retirado"}


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _source_id(source_uid: str) -> str:
    match = _SOURCE_ID_RE.search(source_uid)
    return match.group(1) if match else source_uid


def parse_status(description: str) -> str | None:
    for line in description.splitlines():
        line = line.strip()
        if line in _STATUS_WORDS:
            return line
    return None


def split_summary(raw_summary: str) -> tuple[str, str, str | None]:
    """Trennt Ergebnis in Klammern ab und splittet an ' - '.

    Gibt (heim_seite, gast_seite, ergebnis) zurueck.
    """
    ergebnis = None
    match = _RESULT_RE.search(raw_summary)
    if match:
        ergebnis = match.group(1)
        raw_summary = raw_summary[: match.start()]

    heim_seite, _, gast_seite = raw_summary.partition(" - ")
    return heim_seite.strip(), gast_seite.strip(), ergebnis


def resolve_own_name(team: TeamConfig, cal) -> TeamConfig:
    """Eigenname fuer die Gegnererkennung. Steht er nicht in config.yaml -- so
    bei den Fremdteams, SPEC-ADMIN.md Abschnitt 3 -- kommt er aus dem
    X-WR-CALNAME der Quelle (SPEC.md Abschnitt 4)."""
    if team.handballnet_name:
        return team
    return dataclasses.replace(team, handballnet_name=calendar_name(cal))


def resolve_opponent(heim_seite: str, gast_seite: str, team: TeamConfig) -> str:
    if not team.handballnet_name:
        logger.warning(
            "Kein Eigenname für %s (weder in config.yaml noch als X-WR-CALNAME "
            "der Quelle), Gegner kann nicht bestimmt werden",
            team.key,
        )
        return heim_seite
    own = _normalize_for_compare(team.handballnet_name)
    if _normalize_for_compare(heim_seite) == own:
        return gast_seite
    return heim_seite


def resolve_location(
    halls: list[Hall],
    location: str | None,
) -> tuple[str | None, tuple[float, float] | None, bool]:
    """Ort-Regel fuer Spiele (SPEC.md Abschnitt 6). Gibt (location, geo,
    ist_heim) zurueck. Heim/Auswaerts wird ausschliesslich ueber die Halle
    bestimmt, nie ueber die SUMMARY-Seite."""
    if not location:
        logger.warning("Spiel ohne LOCATION, wird als Auswaerts angenommen")
        return None, None, False

    hall = find_hall(halls, location)
    if hall:
        return hall_address(hall), hall.geo, hall.key == "fliethe"

    return clean_handballnet_address(location), None, False


def transform(
    vevent,
    team: TeamConfig,
    halls: list[Hall],
    opponent_overrides: dict[str, str],
    uid_prefix: str,
    tz_name: str,
) -> Event:
    source_uid = str(vevent["UID"])
    raw_summary = str(vevent["SUMMARY"])
    raw_description = str(vevent.get("DESCRIPTION", ""))

    heim_seite, gast_seite, ergebnis = split_summary(raw_summary)
    opponent_raw = resolve_opponent(heim_seite, gast_seite, team)
    opponent = normalize_opponent(opponent_raw, opponent_overrides)

    location = extract_location(vevent)
    geo_from_source = extract_geo(vevent)
    final_location, final_geo, is_heim = resolve_location(halls, location)
    if final_geo is None:
        final_geo = geo_from_source

    dtstart_raw = vevent["DTSTART"].dt
    all_day = not isinstance(dtstart_raw, datetime)

    status = parse_status(raw_description)
    cancelled = status == "Retirado"
    if status is None and raw_description.strip():
        logger.warning("Unbekanntes oder fehlendes Statuswort in %r, wird als normal behandelt", source_uid)

    if all_day:
        dtstart: datetime | date = dtstart_raw
        dtend: datetime | date = vevent["DTEND"].dt
    else:
        dtstart = localize_naive(dtstart_raw, tz_name)
        dtend = dtstart + timedelta(minutes=team.spieldauer_minuten)

    notiz_lines = []
    if all_day:
        notiz_lines.append("Uhrzeit noch offen")
    elif team.treffpunkt_spiel_minuten is not None:
        # Fremdteams haben keinen Vorlauf konfiguriert -- fuer reine
        # Zuschauertermine gibt es keinen Treffpunkt (SPEC-ADMIN.md
        # Abschnitt 3).
        treffpunkt = dtstart - timedelta(minutes=team.treffpunkt_spiel_minuten)
        notiz_lines.append(f"Treffpunkt: {treffpunkt.strftime('%H:%M')}")
    if ergebnis:
        notiz_lines.append(f"Ergebnis: {ergebnis}")

    title = f"{team.anzeigename} {'Heim' if is_heim else 'Auswärts'} {opponent}"
    if cancelled:
        title = f"ABGESAGT {title}"

    uid = f"{uid_prefix}-{team.key}-spiel-{_source_id(source_uid)}"

    return Event(
        uid=uid,
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
