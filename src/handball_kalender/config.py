"""Laden von config.yaml und halls.yaml (SPEC.md Abschnitt 4, 8, 11)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TeamConfig:
    key: str
    anzeigename: str
    spieldauer_minuten: int
    # Fehlt bei den gemerkten Spielen: dort ist die Quelle ein Abruf pro
    # Spielnummer, kein Team-Kalender.
    handballnet_team_id: int | None = None
    # Eigenname bei handball.net fuer die Gegnererkennung. Zusaetzlich gilt
    # immer der X-WR-CALNAME des Quell-Feeds (SPEC.md Abschnitt 4).
    handballnet_name: str | None = None
    # Alle Eigennamen fuer die Gegnererkennung: handballnet_name und der
    # X-WR-CALNAME. Setzt spiele.resolve_own_name je Lauf, nicht config.yaml.
    eigennamen: tuple[str, ...] = ()
    spielerplus_env: str | None = None
    # None heisst "keine Treffpunkt-Notiz" -- so sind die Fremdteams als reine
    # Zuschauertermine konfiguriert (SPEC-ADMIN.md Abschnitt 3).
    treffpunkt_spiel_minuten: int | None = None
    treffpunkt_training_minuten: int | None = None
    # False = Fremdteam, liefert nur den Pool (own_team in pool.json).
    own: bool = True
    # Nur fuer die Admin-Oberflaeche, sie bekommt beides ueber pool.json
    # (SPEC-ADMIN.md Abschnitt 2). kurzname steht in der Bilanz der Uebersicht
    # ("M2 Training"); fehlt er, gilt der Anzeigename. Die Farben tragen die
    # Schiene links an jeder Terminzeile, hell und dunkel getrennt.
    kurzname: str | None = None
    farbe: str | None = None
    farbe_dunkel: str | None = None


@dataclass(frozen=True)
class FeedConfig:
    key: str
    team: str
    type: str  # "training" oder "spiele"
    # Fuellt Archiv und Pool, schreibt aber keine eigene .ics-Datei.
    pool_only: bool = False
    # "team" = ein Team-Kalender von handball.net oder SpielerPlus.
    # "watch" = ein Abruf pro Spielnummer aus overrides.json.
    source: str = "team"


@dataclass(frozen=True)
class Hall:
    key: str
    name: str
    search_terms: list[str]
    address: str
    geo: tuple[float, float] | None
    exact_terms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Config:
    timezone: str
    feed_ttl: str
    uid_prefix: str
    output_dir: str
    archive_dir: str
    teams: dict[str, TeamConfig]
    feeds: dict[str, FeedConfig]
    opponent_overrides: dict[str, str]
    overrides_path: str = "overrides.json"
    pool_file: str = "pool.json"
    extra_feed_key: str = "extra"
    extra_calname: str = "TBW Extra"
    # Name und Farbe des Extra-Feeds in der Admin-Oberflaeche.
    extra_anzeigename: str = "Extra"
    extra_farbe: str | None = None
    extra_farbe_dunkel: str | None = None
    watch_feed_key: str = "watch-spiele"
    spielerplus_uid_prefixes: list[str] = field(default_factory=lambda: ["training", "event"])
    halls: list[Hall] = field(default_factory=list)

    def spielerplus_url(self, team_key: str) -> str | None:
        env_name = self.teams[team_key].spielerplus_env
        if not env_name:
            return None
        return os.environ.get(env_name)


def load_halls(path: str | Path) -> list[Hall]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    halls = []
    for key, entry in raw.items():
        geo = entry.get("geo")
        halls.append(
            Hall(
                key=key,
                name=entry["name"],
                search_terms=list(entry["search_terms"]),
                address=entry["address"],
                geo=tuple(geo) if geo else None,
                exact_terms=list(entry.get("exact_terms") or []),
            )
        )
    return halls


def load_config(config_path: str | Path, halls_path: str | Path) -> Config:
    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}

    teams = {
        key: TeamConfig(key=key, **team_raw) for key, team_raw in raw["teams"].items()
    }
    feeds = {
        key: FeedConfig(key=key, **feed_raw) for key, feed_raw in raw["feeds"].items()
    }

    return Config(
        timezone=raw["timezone"],
        feed_ttl=raw["feed_ttl"],
        uid_prefix=raw["uid_prefix"],
        output_dir=raw["output_dir"],
        archive_dir=raw["archive_dir"],
        teams=teams,
        feeds=feeds,
        opponent_overrides=dict(raw.get("opponent_overrides") or {}),
        overrides_path=raw.get("overrides_path", "overrides.json"),
        pool_file=raw.get("pool_file", "pool.json"),
        extra_feed_key=raw.get("extra_feed_key", "extra"),
        extra_calname=raw.get("extra_calname", "TBW Extra"),
        extra_anzeigename=raw.get("extra_anzeigename", "Extra"),
        extra_farbe=raw.get("extra_farbe"),
        extra_farbe_dunkel=raw.get("extra_farbe_dunkel"),
        watch_feed_key=raw.get("watch_feed_key", "watch-spiele"),
        spielerplus_uid_prefixes=list(raw.get("spielerplus_uid_prefixes") or ["training", "event"]),
        halls=load_halls(halls_path),
    )
