"""SPEC-ADMIN.md Abschnitt 5 und 9: ein vollstaendiger Lauf mit manuellen
Eingriffen, gegen die echten Fixtures.

Aufgebaut wie der Workflow: Konfiguration und Ausgabeverzeichnisse liegen in
tmp_path, die Quellen kommen aus fixtures/ statt aus dem Netz.
"""

import json
import logging
from pathlib import Path

import pytest
import yaml

from handball_kalender import main

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"

POOL_FEEDS = {"a-jugend-spiele", "1-herren-spiele", "1-damen-spiele"}


@pytest.fixture
def workspace(tmp_path):
    """Ein isoliertes Arbeitsverzeichnis mit eigener config.yaml."""
    raw = yaml.safe_load((REPO_ROOT / "tests" / "config.yaml").read_text(encoding="utf-8"))
    raw["output_dir"] = str(tmp_path / "docs")
    raw["archive_dir"] = str(tmp_path / "data")
    raw["overrides_path"] = str(tmp_path / "overrides.json")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return tmp_path, config_path


def _run(workspace, overrides=None):
    tmp_path, config_path = workspace
    if overrides is not None:
        (tmp_path / "overrides.json").write_text(
            json.dumps(overrides, ensure_ascii=False), encoding="utf-8"
        )
    main.main([
        "--config", str(config_path),
        "--halls", str(REPO_ROOT / "halls.yaml"),
        "--local", str(FIXTURES_DIR),
    ])
    return tmp_path


def _pool(tmp_path):
    return json.loads((tmp_path / "docs" / "pool.json").read_text(encoding="utf-8"))


def _feed(tmp_path, name):
    return (tmp_path / "docs" / f"{name}.ics").read_text(encoding="utf-8")


def _archive(tmp_path, name):
    return json.loads((tmp_path / "data" / f"{name}.json").read_text(encoding="utf-8"))


def _first_uid(tmp_path, *, own_team, feed_type="spiele"):
    """Erste passende UID aus dem Pool samt Feed, in dem sie stehen muss."""
    for event in _pool(tmp_path)["events"]:
        if event["own_team"] is own_team and event["type"] == feed_type:
            return event["uid"], f"{event['team_key']}-{feed_type}"
    raise AssertionError("Kein passender Termin im Pool")


def test_run_without_overrides_file_still_writes_all_feeds(workspace, caplog):
    with caplog.at_level(logging.WARNING):
        tmp_path = _run(workspace)

    assert "fehlt" in caplog.text
    for name in ("m2-training", "m2-spiele", "m3-training", "m3-spiele", "mc-spiele", "extra"):
        assert (tmp_path / "docs" / f"{name}.ics").exists()
    assert (tmp_path / "docs" / "pool.json").exists()


def test_run_with_broken_overrides_file_still_writes_all_feeds(workspace, caplog):
    tmp_path, _ = workspace
    (tmp_path / "overrides.json").write_text('{"hidden": [', encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        _run(workspace)

    assert "JSON" in caplog.text
    assert (tmp_path / "docs" / "m2-spiele.ics").exists()
    assert (tmp_path / "docs" / "extra.ics").exists()


def test_pool_only_teams_get_an_archive_but_no_feed(workspace):
    tmp_path = _run(workspace, {"version": 1})

    for feed_key in POOL_FEEDS:
        assert (tmp_path / "data" / f"{feed_key}.json").exists()
        assert not (tmp_path / "docs" / f"{feed_key}.ics").exists()


def test_pool_contains_own_and_foreign_events(workspace):
    tmp_path = _run(workspace, {"version": 1})
    events = _pool(tmp_path)["events"]

    assert any(event["own_team"] for event in events)
    assert any(not event["own_team"] for event in events)
    assert {event["team"] for event in events} >= {
        "2. Herren", "3. Herren", "C-Jugend", "A-Jugend", "1. Herren", "1. Damen",
    }


def test_foreign_opponent_is_resolved_from_x_wr_calname(workspace):
    tmp_path = _run(workspace, {"version": 1})

    # Ohne Eigennamen aus dem X-WR-CALNAME stuende hier immer die Heimseite,
    # bei Heimspielen also "TB Wülfrath" als eigener Gegner.
    titel = [
        event["summary"]
        for event in _pool(tmp_path)["events"]
        if event["team_key"] == "a-jugend"
    ]
    assert titel
    assert not any("Wülfrath" in t for t in titel)


def test_hidden_uid_is_missing_from_the_feed_but_stays_in_the_archive(workspace):
    tmp_path = _run(workspace, {"version": 1})
    uid, feed = _first_uid(tmp_path, own_team=True)

    _run(workspace, {"version": 1, "hidden": [uid]})

    assert uid not in _feed(tmp_path, feed)
    assert uid in {entry["uid"] for entry in _archive(tmp_path, feed)}
    # Der Pool kommt aus dem Archiv, sonst liesse sich das nicht zuruecknehmen.
    assert uid in {event["uid"] for event in _pool(tmp_path)["events"]}


def test_removing_a_uid_from_hidden_brings_the_event_back(workspace):
    tmp_path = _run(workspace, {"version": 1})
    uid, feed = _first_uid(tmp_path, own_team=True)

    _run(workspace, {"version": 1, "hidden": [uid]})
    assert uid not in _feed(tmp_path, feed)

    _run(workspace, {"version": 1, "hidden": []})
    assert uid in _feed(tmp_path, feed)


def test_hiding_a_training_works_the_same_way(workspace):
    tmp_path = _run(workspace, {"version": 1})
    uid, feed = _first_uid(tmp_path, own_team=True, feed_type="training")

    _run(workspace, {"version": 1, "hidden": [uid]})

    assert uid not in _feed(tmp_path, feed)
    assert uid in {entry["uid"] for entry in _archive(tmp_path, feed)}


def test_included_foreign_game_and_custom_event_share_the_extra_feed(workspace):
    tmp_path = _run(workspace, {"version": 1})
    uid, _ = _first_uid(tmp_path, own_team=False)

    _run(workspace, {
        "version": 1,
        "custom": [{
            "uid": "tbw-custom-a1b2c3",
            "summary": "Mannschaftsabend",
            "dtstart": "2026-11-14T19:00:00",
            "dtend": "2026-11-14T23:00:00",
            "all_day": False,
            "location": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
            "description": "",
        }],
        "included": [uid],
    })

    extra = _feed(tmp_path, "extra")
    assert "X-WR-CALNAME:TBW Extra" in extra
    assert "tbw-custom-a1b2c3" in extra
    assert "Mannschaftsabend" in extra
    assert uid in extra
    # Freigeschaltet heisst nicht abonniert: der Fremdteam-Feed bleibt aus.
    assert not (tmp_path / "docs" / "a-jugend-spiele.ics").exists()


def test_included_game_disappears_from_extra_feed_when_switched_off(workspace):
    tmp_path = _run(workspace, {"version": 1})
    uid, _ = _first_uid(tmp_path, own_team=False)

    _run(workspace, {"version": 1, "included": [uid]})
    assert uid in _feed(tmp_path, "extra")

    _run(workspace, {"version": 1, "included": []})
    assert uid not in _feed(tmp_path, "extra")


# --- Gemerkte Spiele (SPEC-ADMIN.md Abschnitt 3 und 9) -------------------

WATCH_ID = "563599"
WATCH_UID = "tbw-watch-spiel-563599"


def test_watched_match_lands_in_the_extra_feed(workspace):
    tmp_path = _run(workspace, {"version": 1, "watch": [WATCH_ID]})

    extra = _feed(tmp_path, "extra")
    assert WATCH_UID in extra
    assert "SUMMARY:TV Aldekerk II - SG Langenfeld" in extra
    # Eigenes Archiv, aber kein eigener Feed.
    assert (tmp_path / "data" / "watch-spiele.json").exists()
    assert not (tmp_path / "docs" / "watch-spiele.ics").exists()


def test_watched_match_appears_in_the_pool_as_its_own_feed(workspace):
    tmp_path = _run(workspace, {"version": 1, "watch": [WATCH_ID]})

    eintrag = next(e for e in _pool(tmp_path)["events"] if e["uid"] == WATCH_UID)
    assert eintrag["team_key"] == "watch"
    assert eintrag["own_team"] is False


def test_watched_match_keeps_roman_numerals_and_team_suffixes(workspace):
    tmp_path = _run(workspace, {"version": 1, "watch": [WATCH_ID, "563602"]})

    titel = {
        e["summary"] for e in _pool(tmp_path)["events"] if e["team_key"] == "watch"
    }
    assert "TV Aldekerk II - SG Langenfeld" in titel
    assert "HBD Löwen Oberberg - Solinger TB mA" in titel


def test_watched_match_can_be_switched_off_via_hidden(workspace):
    tmp_path = _run(workspace, {"version": 1, "watch": [WATCH_ID]})
    assert WATCH_UID in _feed(tmp_path, "extra")

    _run(workspace, {"version": 1, "watch": [WATCH_ID], "hidden": [WATCH_UID]})

    # Aus dem Feed verschwunden, aber in Archiv und Pool erhalten -- damit
    # umkehrbar.
    assert WATCH_UID not in _feed(tmp_path, "extra")
    assert WATCH_UID in {e["uid"] for e in _archive(tmp_path, "watch-spiele")}
    assert WATCH_UID in {e["uid"] for e in _pool(tmp_path)["events"]}

    _run(workspace, {"version": 1, "watch": [WATCH_ID]})
    assert WATCH_UID in _feed(tmp_path, "extra")


def test_hidden_now_also_applies_to_custom_and_included(workspace):
    """hidden gilt für alle Feeds, nicht nur die Team-Feeds."""
    tmp_path = _run(workspace, {"version": 1})
    fremd_uid, _ = _first_uid(tmp_path, own_team=False)

    basis = {
        "version": 1,
        "custom": [{
            "uid": "tbw-custom-a1b2c3", "summary": "Mannschaftsabend",
            "dtstart": "2026-11-14T19:00:00", "dtend": "2026-11-14T23:00:00",
            "all_day": False, "location": "", "description": "",
        }],
        "included": [fremd_uid],
    }
    _run(workspace, basis)
    assert "tbw-custom-a1b2c3" in _feed(tmp_path, "extra")
    assert fremd_uid in _feed(tmp_path, "extra")

    _run(workspace, dict(basis, hidden=["tbw-custom-a1b2c3", fremd_uid]))
    assert "tbw-custom-a1b2c3" not in _feed(tmp_path, "extra")
    assert fremd_uid not in _feed(tmp_path, "extra")


def test_unknown_match_number_does_not_break_the_run(workspace):
    tmp_path = _run(workspace, {"version": 1, "watch": [WATCH_ID, "999999999"]})

    # Das bekannte Spiel ist da, der Lauf ist durchgelaufen.
    assert WATCH_UID in _feed(tmp_path, "extra")
    assert (tmp_path / "docs" / "pool.json").exists()
    assert "tbw-watch-spiel-999999999" not in _feed(tmp_path, "extra")


def test_removing_a_number_from_watch_keeps_the_event_in_the_archive(workspace):
    """Termine bleiben dauerhaft erhalten und werden nicht nachträglich als
    abgesagt markiert, nur weil sie nicht mehr gemerkt sind."""
    tmp_path = _run(workspace, {"version": 1, "watch": [WATCH_ID]})
    assert WATCH_UID in {e["uid"] for e in _archive(tmp_path, "watch-spiele")}

    _run(workspace, {"version": 1, "watch": []})

    eintrag = next(e for e in _archive(tmp_path, "watch-spiele") if e["uid"] == WATCH_UID)
    assert eintrag["cancelled"] is False
    assert not eintrag["summary"].startswith("ABGESAGT ")
