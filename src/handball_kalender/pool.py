"""docs/pool.json erzeugen (SPEC-ADMIN.md Abschnitt 2).

Auswahlgrundlage fuer die Admin-Oberflaeche. Ein Browser darf die Spielplaene
von handball.net nicht direkt abrufen, deshalb legt der Workflow die Liste hier
ab.

Der Pool entsteht aus den Archiven, nicht aus den Quellen -- er enthaelt
deshalb auch ausgeblendete Termine. Sonst liesse sich ein Ausblenden nicht
wieder zuruecknehmen.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import Config
from .halls import hall_address

# Nur was die Oberflaeche braucht. geo, url und source_uid bleiben draussen,
# damit die Datei auf dem Handy klein bleibt.
def _pool_event(entry: dict, config: Config, feed_key: str) -> dict:
    feed = config.feeds[feed_key]
    team = config.teams[feed.team]
    return {
        "uid": entry["uid"],
        "team": team.anzeigename,
        "team_key": team.key,
        "own_team": team.own,
        "type": feed.type,
        "summary": entry["summary"],
        "dtstart": entry["dtstart"],
        "dtend": entry["dtend"],
        "all_day": entry["all_day"],
        "location": entry.get("location"),
        "cancelled": entry["cancelled"],
    }


def _teams(config: Config) -> list[dict]:
    """Alle Teams in der Reihenfolge aus config.yaml -- die Oberflaeche ordnet
    ihre Filterzeile danach und setzt aus den Farben die Teamfarben."""
    return [
        {
            "key": team.key,
            "name": team.anzeigename,
            "own_team": team.own,
            "color": team.farbe,
            "color_dark": team.farbe_dunkel,
        }
        for team in config.teams.values()
    ]


def _feeds(config: Config) -> list[dict]:
    """Die abonnierbaren Feeds in der Reihenfolge aus config.yaml, der
    Extra-Feed zuletzt, weil er alles Hinzugefuegte sammelt. Pool-Quellen
    fehlen: sie schreiben keinen Kalender."""
    feeds = []
    for feed in config.feeds.values():
        if feed.pool_only:
            continue
        team = config.teams[feed.team]
        suffix = "Training" if feed.type == "training" else "Spiele"
        feeds.append(
            {
                "key": feed.key,
                "team_key": team.key,
                "name": f"{team.anzeigename} {suffix}",
                "short_name": f"{team.kurzname or team.anzeigename} {suffix}",
            }
        )
    feeds.append(
        {
            "key": config.extra_feed_key,
            "team_key": None,
            "name": config.extra_anzeigename,
            "short_name": config.extra_anzeigename,
            # Der Extra-Feed gehoert zu keinem Team und bringt seine Farbe
            # deshalb selbst mit.
            "color": config.extra_farbe,
            "color_dark": config.extra_farbe_dunkel,
        }
    )
    return feeds


def build(archives: dict[str, list[dict]], config: Config, now: datetime) -> dict:
    """`archives` bildet feed_key auf die gemergten Archiveintraege ab.

    Neben den Terminen reisen Teams, Feed-Namen und Farben aus config.yaml
    mit, damit die Oberflaeche nichts davon fest eingebaut haben muss und in
    jeder Kopie des Repositorys unveraendert laeuft."""
    events = [
        _pool_event(entry, config, feed_key)
        for feed_key, entries in archives.items()
        for entry in entries
    ]
    events.sort(key=lambda event: (event["dtstart"], event["summary"]))
    # halls.yaml liegt im Repo-Wurzelverzeichnis und ist ueber GitHub Pages
    # nicht erreichbar. Die Ortsauswahl im Formular braucht die Liste aber --
    # also reist sie im Pool mit, aus demselben Grund, aus dem der Pool
    # ueberhaupt existiert.
    halls = [
        {"name": hall.name, "address": hall_address(hall)}
        for hall in sorted(config.halls, key=lambda hall: hall.name)
    ]
    return {
        "generated": now.isoformat(),
        "teams": _teams(config),
        "feeds": _feeds(config),
        "halls": halls,
        "events": events,
    }


def save(path: str | Path, pool: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(pool, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
