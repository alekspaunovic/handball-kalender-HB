"""Orchestrierung: fetch -> transform -> Archiv-Merge -> manuelle Eingriffe
-> Feeds schreiben (SPEC.md Abschnitt 11, SPEC-ADMIN.md Abschnitt 5)."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

import requests

from . import (
    archive,
    extra,
    ics_io,
    overrides as overrides_mod,
    pool,
    spiele,
    training,
    watch,
)
from .config import Config, FeedConfig, load_config
from .fetch import fetch_ics
from .models import Event
from .overrides import Overrides

logger = logging.getLogger(__name__)


def _handballnet_url(team_id: int) -> str:
    return f"https://www.handball.net/kalender/team/{team_id}.ics"


def _load_source(
    feed: FeedConfig, config: Config, local_fixtures_dir: Path | None
) -> bytes | None:
    team = config.teams[feed.team]

    if local_fixtures_dir is not None:
        filename = (
            f"spielerplus-{feed.team}.ics"
            if feed.type == "training"
            else f"handballnet-{feed.team}.ics"
        )
        path = local_fixtures_dir / filename
        if not path.exists():
            logger.warning("Keine lokale Fixture für %s (%s), Feed wird übersprungen", feed.key, path)
            return None
        return path.read_bytes()

    if feed.type == "training":
        url = config.spielerplus_url(feed.team)
        if not url:
            logger.warning(
                "Keine SpielerPlus-URL für %s gesetzt (%s), Feed wird übersprungen",
                feed.team,
                team.spielerplus_env,
            )
            return None
        return fetch_ics(url)

    return fetch_ics(_handballnet_url(team.handballnet_team_id))


def _calname(feed: FeedConfig, config: Config) -> str:
    team = config.teams[feed.team]
    suffix = "Training" if feed.type == "training" else "Spiele"
    return f"TBW {team.anzeigename} {suffix}"


def _load_watch_source(mid: str, local_fixtures_dir: Path | None) -> bytes | None:
    """Ein gemerktes Spiel abrufen. None heisst "handball.net kennt diese
    Spielnummer nicht" -- eine Aussage, die in die Verschwinden-Logik gehoert.
    Jeder andere Fehler wird durchgeworfen, damit der Archiveintrag unberuehrt
    bleibt (SPEC-ADMIN.md Abschnitt 3)."""
    if local_fixtures_dir is not None:
        pfad = local_fixtures_dir / f"handballnet-spiel-{mid}.ics"
        if not pfad.exists():
            logger.warning("Keine lokale Fixture für Spiel %s (%s)", mid, pfad)
            return None
        return pfad.read_bytes()

    try:
        return fetch_ics(watch.match_url(mid))
    except requests.HTTPError as fehler:
        if fehler.response is not None and fehler.response.status_code == 404:
            logger.warning("handball.net kennt die Spielnummer %s nicht", mid)
            return None
        raise


def run_watch(
    config: Config,
    manual: Overrides,
    local_fixtures_dir: Path | None,
    now: datetime,
) -> list[dict]:
    """Ruft jede gemerkte Spielnummer einzeln ab und mergt sie gegen
    data/watch-spiele.json (SPEC-ADMIN.md Abschnitt 3 und 5)."""
    feed = config.feeds[config.watch_feed_key]
    team = config.teams[feed.team]
    archive_path = Path(config.archive_dir) / f"{config.watch_feed_key}.json"
    existing = archive.load(archive_path)

    events: list[Event] = []
    # UIDs, über die wir nichts wissen, weil ihr Abruf scheiterte. Sie dürfen
    # nicht als abgesagt markiert werden.
    protect: set[str] = set()

    for mid in sorted(manual.watch):
        uid = f"{config.uid_prefix}-watch-spiel-{mid}"
        try:
            raw = _load_watch_source(mid, local_fixtures_dir)
            if raw is None:
                # 404 oder fehlende Fixture: keine Aussage über das Spiel
                # selbst, wenn es lokal fehlt -- aber ein echtes 404 schon.
                # Beides führt hier zum selben Weg, weil eine fehlende Fixture
                # nur im lokalen Lauf vorkommt.
                continue
            cal = ics_io.parse_calendar(raw)
            vevent = next(iter(ics_io.iter_vevents(cal)), None)
            if vevent is None:
                logger.warning("Spiel %s enthält kein VEVENT, wird übersprungen", mid)
                protect.add(uid)
                continue
            events.append(
                watch.transform(
                    vevent,
                    mid,
                    config.halls,
                    config.opponent_overrides,
                    config.uid_prefix,
                    config.timezone,
                    team.spieldauer_minuten,
                )
            )
        except Exception:
            logger.exception(
                "Abruf des gemerkten Spiels %s fehlgeschlagen, Archiveintrag "
                "bleibt unverändert",
                mid,
            )
            protect.add(uid)

    # Eine Spielnummer, die nicht mehr in `watch` steht, bleibt im Archiv
    # stehen (Termine bleiben dauerhaft erhalten) und darf nicht nachträglich
    # als abgesagt gelten.
    gemerkt = {f"{config.uid_prefix}-watch-spiel-{mid}" for mid in manual.watch}
    protect |= {e["uid"] for e in existing if e["uid"] not in gemerkt}

    merged = archive.merge(existing, events, now, protect=protect)
    archive.save(archive_path, merged)
    return merged


def run_feed(
    feed: FeedConfig,
    config: Config,
    local_fixtures_dir: Path | None,
    now: datetime,
    hidden: set[str],
) -> list[dict]:
    """Verarbeitet eine Quelle und gibt ihr gemergtes Archiv zurueck.

    Der Feed wird um die in `hidden` aufgefuehrten UIDs gekuerzt, das Archiv
    nicht -- deshalb ist jedes Ausblenden umkehrbar (SPEC-ADMIN.md Abschnitt 5).
    Pool-Quellen schreiben gar keine .ics-Datei.
    """
    archive_path = Path(config.archive_dir) / f"{feed.key}.json"
    output_path = Path(config.output_dir) / f"{feed.key}.ics"
    existing = archive.load(archive_path)
    if feed.type == "training":
        existing = training.filter_archive_entries(existing, config.spielerplus_uid_prefixes)

    def write(entries: list[dict]) -> None:
        if feed.pool_only:
            return
        ics_io.write_feed(
            output_path,
            [entry for entry in entries if entry["uid"] not in hidden],
            _calname(feed, config),
            config.timezone,
            config.feed_ttl,
        )

    try:
        raw = _load_source(feed, config, local_fixtures_dir)
        if raw is None:
            if existing:
                write(existing)
            return existing

        cal = ics_io.parse_calendar(raw)
        team = config.teams[feed.team]
        if feed.type == "spiele":
            team = spiele.resolve_own_name(team, cal)
        events = []
        for vevent in ics_io.iter_vevents(cal):
            if feed.type == "training":
                event = training.transform(
                    vevent, team, config.halls, config.uid_prefix, config.spielerplus_uid_prefixes
                )
                if event is not None:
                    events.append(event)
            else:
                events.append(
                    spiele.transform(
                        vevent,
                        team,
                        config.halls,
                        config.opponent_overrides,
                        config.uid_prefix,
                        config.timezone,
                    )
                )

        merged = archive.merge(existing, events, now)
    except Exception:
        logger.exception("Fehler beim Verarbeiten von %s, Archiv bleibt unverändert", feed.key)
        merged = existing

    archive.save(archive_path, merged)
    write(merged)
    return merged


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Handball-Kalender-Feeds erzeugen")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--halls", default="halls.yaml")
    parser.add_argument(
        "--local",
        metavar="FIXTURES_DIR",
        nargs="?",
        const="fixtures",
        default=None,
        help="liest aus lokalen ICS-Fixtures statt aus dem Netz (kein Zugriff auf echte SpielerPlus-URLs/Secrets nötig)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = load_config(args.config, args.halls)
    local_fixtures_dir = Path(args.local) if args.local else None
    now = datetime.now(dt_timezone.utc)

    manual = overrides_mod.load(config.overrides_path)

    archives = {
        feed.key: run_feed(feed, config, local_fixtures_dir, now, manual.hidden)
        for feed in config.feeds.values()
        if feed.source == "team"
    }
    archives[config.watch_feed_key] = run_watch(config, manual, local_fixtures_dir, now)

    output_dir = Path(config.output_dir)
    pool.save(output_dir / config.pool_file, pool.build(archives, config, now))
    ics_io.write_feed(
        output_dir / f"{config.extra_feed_key}.ics",
        [
            entry
            for entry in extra.build_entries(
                manual, archives, config.halls, config.timezone, config.watch_feed_key
            )
            if entry["uid"] not in manual.hidden
        ],
        config.extra_calname,
        config.timezone,
        config.feed_ttl,
    )


if __name__ == "__main__":
    main()
