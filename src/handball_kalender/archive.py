"""Archiv laden/mergen/speichern (SPEC.md Abschnitt 10)."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .models import Event

# Feld "abgesagt_weil" an abgesagten Archiveinträgen (SPEC.md Abschnitt 10).
# Nur eine Absage aus der Verschwinden-Logik darf das Skript selbst wieder
# aufheben -- eine Absage der Quelle hebt nur die Quelle auf.
ABGESAGT_QUELLE = "quelle"
ABGESAGT_VERSCHWUNDEN = "verschwunden"

_PRAEFIX = "ABGESAGT "


def _iso(value: datetime | date) -> str:
    return value.isoformat()


def _event_fields(event: Event) -> dict:
    return {
        "uid": event.uid,
        "source_uid": event.source_uid,
        "summary": event.summary,
        "dtstart": _iso(event.dtstart),
        "dtend": _iso(event.dtend),
        "all_day": event.all_day,
        "location": event.location,
        "geo": list(event.geo) if event.geo else None,
        "description": event.description,
        "url": event.url,
        "cancelled": event.cancelled,
    }


def _parse_dtstart(entry: dict) -> datetime | date:
    if entry["all_day"]:
        return date.fromisoformat(entry["dtstart"][:10])
    return datetime.fromisoformat(entry["dtstart"])


def _is_past(dtstart: datetime | date, now: datetime) -> bool:
    if isinstance(dtstart, datetime):
        return dtstart < now
    return dtstart < now.date()


def _seen_after_start(entry: dict) -> bool:
    """Stand der Termin nach seinem Beginn noch in der Quelle? Dann hat er
    stattgefunden, und dass er später fehlt, heißt nur, dass er aus dem
    Zeitfenster der Quelle gefallen ist: SpielerPlus behält vergangene
    Termine nur rund drei Monate, handball.net nimmt Turnierspiele einige
    Tage nach dem Turnier aus dem Team-Kalender. Ganztägige Termine zählen
    erst ab dem Folgetag als begonnen, wie in `_is_past`."""
    last_seen = datetime.fromisoformat(entry["last_seen"])
    start = _parse_dtstart(entry)
    if isinstance(start, datetime):
        return last_seen >= start
    return last_seen.date() > start


def merge(
    existing: list[dict],
    new_events: list[Event],
    now: datetime,
    protect: set[str] | None = None,
) -> list[dict]:
    """Aktualisiert das Archiv mit den aktuell aus der Quelle gelesenen
    Events. Bekannte UIDs werden aktualisiert (Zeit/Ort können sich ändern,
    die UID bleibt stabil), neue UIDs werden ergänzt. Termine, die im Archiv
    stehen aber in `new_events` fehlen, bleiben unverändert stehen, solange
    ihr Termin noch nicht vorbei ist. Ist ihr Termin vorbei, ohne dass die
    Quelle ihn nach seinem Beginn noch geführt hat, bekommen sie das
    ABGESAGT-Präfix (Verschwinden-Logik) -- gelöscht wird nie, damit Termine
    dauerhaft im Kalender bleiben.

    `protect` nimmt UIDs von der Verschwinden-Logik aus. Das brauchen die
    gemerkten Spiele (SPEC-ADMIN.md Abschnitt 3): schlägt der Abruf einer
    einzelnen Spielnummer fehl, wissen wir nichts über das Spiel und dürfen es
    deshalb nicht als abgesagt markieren. Ein echtes 404 von handball.net ist
    dagegen eine Aussage und gehört nicht in `protect`.
    """
    protect = protect or set()
    now_iso = now.isoformat()
    by_uid: dict[str, dict] = {e["uid"]: dict(e) for e in existing}
    seen_uids: set[str] = set()

    for event in new_events:
        seen_uids.add(event.uid)
        fields = _event_fields(event)
        if event.uid in by_uid:
            entry = by_uid[event.uid]
            entry.update(fields)
            entry["last_seen"] = now_iso
        else:
            entry = dict(fields)
            entry["first_seen"] = now_iso
            entry["last_seen"] = now_iso
            by_uid[event.uid] = entry
        # Was die Quelle liefert, gilt. Taucht ein verschwundener Termin
        # wieder auf, ist seine Absage damit aufgehoben.
        if entry["cancelled"]:
            entry["abgesagt_weil"] = ABGESAGT_QUELLE
        else:
            entry.pop("abgesagt_weil", None)

    for uid, entry in by_uid.items():
        if uid in seen_uids or uid in protect:
            continue
        if entry["cancelled"]:
            if "abgesagt_weil" not in entry:
                _classify_legacy(entry)
            continue
        if _is_past(_parse_dtstart(entry), now) and not _seen_after_start(entry):
            entry["cancelled"] = True
            entry["abgesagt_weil"] = ABGESAGT_VERSCHWUNDEN
            if not entry["summary"].startswith(_PRAEFIX):
                entry["summary"] = f"{_PRAEFIX}{entry['summary']}"

    return list(by_uid.values())


def _classify_legacy(entry: dict) -> None:
    """Abgesagte Einträge aus der Zeit vor "abgesagt_weil", die nicht mehr in
    der Quelle stehen. Absagen der Quelle bekommen ihren Grund im ersten Lauf,
    in dem die Quelle den Termin noch liefert, und bei Einführung des Felds
    stand jede von ihnen noch in der Quelle -- übrig bleiben also Absagen der
    Verschwinden-Logik. Die hat früher auch Termine abgesagt, die nach ihrem
    Beginn noch in der Quelle standen, also stattgefunden haben (SPEC.md
    Abschnitt 10). Diese werden hier zurückgenommen."""
    if _seen_after_start(entry):
        entry["cancelled"] = False
        if entry["summary"].startswith(_PRAEFIX):
            entry["summary"] = entry["summary"][len(_PRAEFIX):]
    else:
        entry["abgesagt_weil"] = ABGESAGT_VERSCHWUNDEN


def load(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: str | Path, entries: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
