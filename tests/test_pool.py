"""SPEC-ADMIN.md Abschnitt 2 und 9: der Pool als Auswahlgrundlage."""

import dataclasses
from datetime import datetime, timezone as dt_timezone

from handball_kalender import pool

NOW = datetime(2026, 9, 24, 6, 0, tzinfo=dt_timezone.utc)


def _entry(uid, dtstart, summary="Termin"):
    return {
        "uid": uid,
        "source_uid": uid,
        "summary": summary,
        "dtstart": dtstart,
        "dtend": dtstart,
        "all_day": False,
        "location": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
        "geo": [51.2759225, 7.0168646],
        "description": "Treffpunkt: 18:50",
        "url": "https://www.handball.net/match/1",
        "cancelled": False,
    }


def test_own_and_foreign_events_are_distinguished_by_own_team(config):
    archives = {
        "m2-spiele": [_entry("tbw-m2-spiel-1", "2026-10-03T15:50:00+02:00")],
        "a-jugend-spiele": [_entry("tbw-a-jugend-spiel-2", "2026-10-05T16:00:00+02:00")],
    }

    events = {e["uid"]: e for e in pool.build(archives, config, NOW)["events"]}

    assert events["tbw-m2-spiel-1"]["own_team"] is True
    assert events["tbw-m2-spiel-1"]["team"] == "2. Herren"
    assert events["tbw-a-jugend-spiel-2"]["own_team"] is False
    assert events["tbw-a-jugend-spiel-2"]["team"] == "A-Jugend"
    assert events["tbw-a-jugend-spiel-2"]["team_key"] == "a-jugend"


def test_type_separates_games_from_trainings(config):
    archives = {
        "m3-training": [_entry("tbw-m3-training-1", "2026-10-01T20:00:00+02:00")],
        "m3-spiele": [_entry("tbw-m3-spiel-1", "2026-10-03T18:00:00+02:00")],
    }

    events = {e["uid"]: e for e in pool.build(archives, config, NOW)["events"]}

    assert events["tbw-m3-training-1"]["type"] == "training"
    assert events["tbw-m3-spiel-1"]["type"] == "spiele"


def test_events_are_sorted_chronologically_across_feeds(config):
    archives = {
        "m2-spiele": [_entry("tbw-m2-spiel-1", "2026-10-10T15:50:00+02:00")],
        "m3-spiele": [_entry("tbw-m3-spiel-1", "2026-10-03T18:00:00+02:00")],
        "a-jugend-spiele": [_entry("tbw-a-jugend-spiel-1", "2026-10-05T16:00:00+02:00")],
    }

    uids = [e["uid"] for e in pool.build(archives, config, NOW)["events"]]

    assert uids == ["tbw-m3-spiel-1", "tbw-a-jugend-spiel-1", "tbw-m2-spiel-1"]


def test_pool_carries_only_the_fields_the_interface_needs(config):
    archives = {"m2-spiele": [_entry("tbw-m2-spiel-1", "2026-10-03T15:50:00+02:00")]}

    event = pool.build(archives, config, NOW)["events"][0]

    assert set(event) == {
        "uid", "team", "team_key", "own_team", "type", "summary",
        "dtstart", "dtend", "all_day", "location", "cancelled",
    }


def test_generated_timestamp_is_recorded(config):
    assert pool.build({}, config, NOW)["generated"] == NOW.isoformat()


def test_halls_travel_with_the_pool_for_the_location_picker(config):
    halls = pool.build({}, config, NOW)["halls"]

    namen = [hall["name"] for hall in halls]
    assert "Sporthalle Fliethe" in namen
    assert namen == sorted(namen)
    fliethe = next(hall for hall in halls if hall["name"] == "Sporthalle Fliethe")
    # Vollstaendige Adresse inkl. ", Deutschland", damit das Formular sie
    # unveraendert in overrides.json schreiben kann.
    assert fliethe["address"] == (
        "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland"
    )


def test_teams_travel_with_the_pool_in_config_order(config):
    teams = pool.build({}, config, NOW)["teams"]

    assert [team["key"] for team in teams] == list(config.teams)
    assert teams[0] == {
        "key": "m2",
        "name": "2. Herren",
        "own_team": True,
        "color": "#007aff",
        "color_dark": "#0a84ff",
    }
    a_jugend = next(team for team in teams if team["key"] == "a-jugend")
    assert a_jugend["own_team"] is False


def test_feeds_are_the_subscribable_calendars_with_extra_last(config):
    feeds = pool.build({}, config, NOW)["feeds"]

    # Pool-Quellen schreiben keinen Kalender und fehlen deshalb.
    assert [feed["key"] for feed in feeds] == [
        "m2-training", "m2-spiele", "m3-training", "m3-spiele",
        "mc-training", "mc-spiele", "extra",
    ]
    assert feeds[1] == {
        "key": "m2-spiele",
        "team_key": "m2",
        "name": "2. Herren Spiele",
        "short_name": "M2 Spiele",
    }


def test_extra_feed_brings_its_own_name_and_color(config):
    extra = pool.build({}, config, NOW)["feeds"][-1]

    assert extra == {
        "key": "extra",
        "team_key": None,
        "name": "Extra",
        "short_name": "Extra",
        "color": "#8e8e93",
        "color_dark": "#98989d",
    }


def test_short_name_falls_back_to_display_name(config):
    ohne_kurzname = dataclasses.replace(
        config,
        teams={**config.teams, "m2": dataclasses.replace(config.teams["m2"], kurzname=None)},
    )

    feeds = {feed["key"]: feed for feed in pool.build({}, ohne_kurzname, NOW)["feeds"]}

    assert feeds["m2-training"]["short_name"] == "2. Herren Training"


def test_watched_matches_are_their_own_pseudo_feed(config):
    archives = {
        "watch-spiele": [_entry("tbw-watch-spiel-563599", "2026-09-13T15:00:00+02:00",
                                "TV Aldekerk II - SG Langenfeld")],
    }

    event = pool.build(archives, config, NOW)["events"][0]

    assert event["team_key"] == "watch"
    assert event["own_team"] is False
    assert event["type"] == "spiele"
    assert event["team"] == "Gemerktes Spiel"
    assert event["summary"] == "TV Aldekerk II - SG Langenfeld"
