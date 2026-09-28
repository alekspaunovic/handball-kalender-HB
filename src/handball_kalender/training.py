"""Transformation von SpielerPlus-Terminen (SPEC.md Abschnitt 2 + 5)."""

from __future__ import annotations

import logging
import re
from datetime import timedelta

from .config import Hall, TeamConfig
from .halls import find_hall, hall_address
from .ics_io import extract_geo, extract_location
from .models import Event
from .textnorm import normalize

logger = logging.getLogger(__name__)

_TRAINING_TITLE_RE = re.compile(r"^Training\s*-\s*(.+)$")

# Grobe Plausibilitaetspruefung fuer eine LOCATION, die zu keiner bekannten
# Halle passt: SpielerPlus liefert teils nur ein unvollstaendiges Fragment
# wie "42 Wülfrath, Deutschland" (Navigation landet in der Stadtmitte). Eine
# echte Adresse hat eine Hausnummer direkt hinter einem Strassennamen und
# eine fuenfstellige PLZ.
_PLZ_RE = re.compile(r"\b\d{5}\b")
_HAUSNUMMER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}\.?\s+\d{1,4}\s*[a-zA-Z]?\b")

# Bekannte, erwartete Praefixe, die trotz Positivliste stillschweigend
# verworfen werden (SPEC.md Abschnitt 2): "game" sind Spiele (kommen aus
# handball.net), "absence" sind Abwesenheiten -- beides fuer den Kalender
# irrelevant, aber kein Hinweis auf ein unbekanntes/neues Praefix.
_KNOWN_DISCARD_PREFIXES = ("game", "absence")


def classify_uid(uid: str, allowed_prefixes: list[str]) -> str | None:
    """Ordnet eine SpielerPlus-UID einer Kategorie zu (SPEC.md Abschnitt 2).

    Positivliste: Nur Praefixe aus `allowed_prefixes` (per config.yaml,
    typischerweise "training" und "event") werden übernommen. Alles andere
    wird verworfen -- die bekannten Praefixe "game" und "absence" ohne
    Log-Eintrag, unbekannte Praefixe mit einer Warnung, damit nichts
    stillschweigend verlorengeht.
    """
    prefix = uid.split(".", 1)[0]
    if prefix in allowed_prefixes:
        return prefix
    if prefix not in _KNOWN_DISCARD_PREFIXES:
        logger.warning("Unbekanntes SpielerPlus-UID-Präfix %r, wird verworfen", uid)
    return None


def _source_id(uid: str) -> str:
    return uid.split(".", 1)[1] if "." in uid else uid


def build_title(anzeigename: str, raw_summary: str) -> tuple[str, str | None]:
    """Titel gemäß SPEC.md Abschnitt 5 sowie den erkannten Ortszusatz, falls
    vorhanden.

    "Halle" als Ortszusatz meint die Standardhalle Fliethe und wird wie gar
    kein Ortszusatz behandelt -- taucht also nicht im Titel auf.
    """
    if raw_summary == "Training":
        return f"Training {anzeigename}", None

    match = _TRAINING_TITLE_RE.match(raw_summary)
    if match:
        ortszusatz = match.group(1).strip()
        if normalize(ortszusatz) == normalize("Halle"):
            return f"Training {anzeigename}", None
        return f"Training {anzeigename} - {ortszusatz}", ortszusatz

    return f"{anzeigename}: {raw_summary}", None


def _looks_like_plausible_address(text: str) -> bool:
    """Eine LOCATION, die zu keiner bekannten Halle passt, ist nur dann
    verlässlich genug, um unverändert übernommen zu werden, wenn sie eine
    Hausnummer (Strassenname direkt gefolgt von einer Zahl) UND eine
    fünfstellige PLZ enthält. Sonst ist es meist ein unbrauchbares
    SpielerPlus-Fragment wie "42 Wülfrath, Deutschland"."""
    return bool(_PLZ_RE.search(text)) and bool(_HAUSNUMMER_RE.search(text))


def resolve_location(
    halls: list[Hall],
    location: str | None,
    geo: tuple[float, float] | None,
    ortszusatz: str | None,
) -> tuple[str, tuple[float, float] | None]:
    """Ort-Regel gemäß der korrigierten SPEC.md Abschnitt 5.

    1. Ortszusatz aus dem Titel bekannt (halls.yaml): Halle aus der Tabelle.
       Geht vor einer evtl. vorhandenen LOCATION, weil SpielerPlus dort
       teils nur eine unvollständige Rohadresse liefert (z.B. "42 Wülfrath,
       Deutschland"), waehrend der Titelzusatz eindeutig ist.
    2. Kein (bekannter) Ortszusatz, aber LOCATION vorhanden: gegen
       halls.yaml prüfen -- bei Treffer den Hallentabellen-Eintrag nehmen
       (einheitliche Schreibweise). Kein Treffer, aber die LOCATION sieht
       wie eine echte Adresse aus (Hausnummer + fünfstellige PLZ):
       unverändert übernehmen (inkl. GEO). Sonst als nicht vorhanden
       behandeln (Warnung loggen) und wie Fall 3/4 weiterverfahren.
    3. Weder Ortszusatz noch (brauchbare) LOCATION: Standardhalle Fliethe.
    4. Unbekannter Ortszusatz und keine (brauchbare) LOCATION: Ortszusatz
       als reinen Text setzen, Warnung loggen.
    """
    if ortszusatz:
        hall = find_hall(halls, ortszusatz)
        if hall:
            return hall_address(hall), hall.geo

    if location:
        hall = find_hall(halls, location)
        if hall:
            return hall_address(hall), hall.geo
        if _looks_like_plausible_address(location):
            return location, geo
        logger.warning(
            "LOCATION %r passt zu keiner Halle und wirkt unvollständig "
            "(keine Hausnummer/PLZ), wird verworfen",
            location,
        )
        location = None

    if ortszusatz:
        logger.warning("Unbekannter Ortszusatz %r, wird als reiner Text übernommen", ortszusatz)
        return ortszusatz, None

    fliethe = next(h for h in halls if h.key == "fliethe")
    return hall_address(fliethe), fliethe.geo


def filter_archive_entries(existing: list[dict], allowed_prefixes: list[str]) -> list[dict]:
    """Wendet die Positivliste (SPEC.md Abschnitt 2) auch auf bereits im
    Archiv stehende Einträge an.

    Vor Einführung der Positivliste wurden SpielerPlus-Termine mit den
    Präfixen "game", "absence" und unbekannten Präfixen (z.B. "tournament")
    fälschlich übernommen und als Kategorie "event" im Archiv abgelegt. Da
    `archive.merge` Einträge, die in der Quelle nicht mehr auftauchen, auf
    unbestimmte Zeit stehen lässt, würden diese Alt-Einträge sonst nie
    verschwinden. Wird bei jedem Lauf angewandt, bevor gemergt wird.
    """
    kept = []
    for entry in existing:
        source_uid = entry.get("source_uid", "")
        if "." not in source_uid:
            kept.append(entry)
            continue
        if classify_uid(source_uid, allowed_prefixes) is None:
            continue
        kept.append(entry)
    return kept


def build_notiz(kind: str, team: TeamConfig, dtstart) -> str:
    if kind == "training" and team.treffpunkt_training_minuten is not None:
        treffpunkt = dtstart - timedelta(minutes=team.treffpunkt_training_minuten)
        return f"Treffpunkt: {treffpunkt.strftime('%H:%M')}"
    return ""


def transform(
    vevent,
    team: TeamConfig,
    halls: list[Hall],
    uid_prefix: str,
    allowed_uid_prefixes: list[str],
) -> Event | None:
    """Wandelt ein SpielerPlus-VEVENT in ein Event um, oder None, wenn das
    UID-Präfix nicht in der Positivliste steht (SPEC.md Abschnitt 2)."""
    source_uid = str(vevent["UID"])
    kind = classify_uid(source_uid, allowed_uid_prefixes)
    if kind is None:
        return None

    raw_summary = str(vevent["SUMMARY"])
    title, ortszusatz = build_title(team.anzeigename, raw_summary)

    location = extract_location(vevent)
    geo = extract_geo(vevent)
    final_location, final_geo = resolve_location(halls, location, geo, ortszusatz)

    dtstart = vevent["DTSTART"].dt
    dtend = vevent["DTEND"].dt
    description = build_notiz(kind, team, dtstart)

    uid = f"{uid_prefix}-{team.key}-{kind}-{_source_id(source_uid)}"

    return Event(
        uid=uid,
        source_uid=source_uid,
        summary=title,
        dtstart=dtstart,
        dtend=dtend,
        all_day=False,
        location=final_location,
        geo=final_geo,
        description=description,
        url=str(vevent.get("URL", "")),
        cancelled=False,
    )
