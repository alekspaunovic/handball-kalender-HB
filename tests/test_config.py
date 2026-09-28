"""Die Konfiguration der 1. Herren (config.yaml im Wurzelverzeichnis).

Die uebrigen Tests laufen gegen tests/config.yaml, die Konfiguration des
Ursprungsrepositorys. Hier wird geprueft, dass die eigene Konfiguration das
Gewuenschte ergibt -- mit einem vollstaendigen Lauf gegen die Fixtures. Die
Spielplaene der 1. Herren und der 2. Herren liegen dort unter ihren Namen im
Ursprung (handballnet-1-herren.ics, handballnet-m2.ics) und werden fuer den
Lauf unter die Kuerzel dieses Repositorys kopiert.
"""

import json
import re
import shutil
from datetime import datetime, timedelta

import pytest
import yaml

from handball_kalender import main, training
from handball_kalender.config import load_config

from conftest import FIXTURES_DIR, REPO_ROOT

CONFIG = REPO_ROOT / "config.yaml"
HALLS = REPO_ROOT / "halls.yaml"


@pytest.fixture(scope="module")
def config():
    return load_config(CONFIG, HALLS)


@pytest.fixture(scope="module")
def lauf(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("hb")
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    shutil.copy(FIXTURES_DIR / "handballnet-1-herren.ics", fixtures / "handballnet-m1.ics")
    shutil.copy(FIXTURES_DIR / "handballnet-1-damen.ics", fixtures / "handballnet-1-damen.ics")
    shutil.copy(FIXTURES_DIR / "handballnet-m2.ics", fixtures / "handballnet-2-herren.ics")

    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw["output_dir"] = str(tmp_path / "docs")
    raw["archive_dir"] = str(tmp_path / "data")
    raw["overrides_path"] = str(REPO_ROOT / "overrides.json")
    config_path = tmp_path / "config.yaml"
    # sort_keys=False: die Reihenfolge der Teams und Feeds ist Teil dessen,
    # was hier geprueft wird.
    config_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    main.main(["--config", str(config_path), "--halls", str(HALLS), "--local", str(fixtures)])
    return tmp_path


def _pool(lauf):
    return json.loads((lauf / "docs" / "pool.json").read_text(encoding="utf-8"))


def test_own_team_is_the_first_men(config):
    m1 = config.teams["m1"]

    assert [key for key, team in config.teams.items() if team.own] == ["m1"]
    assert m1.anzeigename == "1. Herren"
    assert m1.handballnet_team_id == 75787
    assert m1.spielerplus_env == "SPIELERPLUS_M1"
    assert m1.treffpunkt_spiel_minuten == 75
    assert m1.treffpunkt_training_minuten == 5
    assert m1.spieldauer_minuten == 90


def test_foreign_teams_are_pool_only(config):
    fremd = {key: team for key, team in config.teams.items() if not team.own and key != "watch"}

    assert {key: team.handballnet_team_id for key, team in fremd.items()} == {
        "1-damen": 76182,
        "2-herren": 74503,
    }
    for feed in config.feeds.values():
        if feed.team in fremd:
            assert feed.pool_only


def test_only_the_m1_feeds_are_written(config):
    assert [key for key, feed in config.feeds.items() if not feed.pool_only] == [
        "m1-training", "m1-spiele",
    ]


def test_calendar_names(config):
    assert main._calname(config.feeds["m1-training"], config) == "TBW 1. Herren Training"
    assert main._calname(config.feeds["m1-spiele"], config) == "TBW 1. Herren Spiele"


def test_workflow_uses_only_the_m1_secret(config):
    workflow = (REPO_ROOT / ".github" / "workflows" / "feeds.yml").read_text(encoding="utf-8")

    assert set(re.findall(r"secrets\.(SPIELERPLUS_\w+)", workflow)) == {"SPIELERPLUS_M1"}
    assert {team.spielerplus_env for team in config.teams.values()} - {None} == {"SPIELERPLUS_M1"}


def test_training_meeting_point_is_five_minutes_before(config):
    beginn = datetime(2026, 10, 1, 20, 0)

    assert training.build_notiz("training", config.teams["m1"], beginn) == "Treffpunkt: 19:55"


def test_run_writes_the_games_feed_with_its_calendar_name(lauf):
    spiele = (lauf / "docs" / "m1-spiele.ics").read_text(encoding="utf-8")

    assert "X-WR-CALNAME:TBW 1. Herren Spiele" in spiele
    # Ohne SPIELERPLUS_M1 kein Training-Feed, aber auch kein Abbruch.
    assert not (lauf / "docs" / "m1-training.ics").exists()
    # Fremdteams schreiben keinen eigenen Feed.
    assert not (lauf / "docs" / "1-damen-spiele.ics").exists()
    assert not (lauf / "docs" / "2-herren-spiele.ics").exists()
    assert (lauf / "docs" / "extra.ics").exists()


def test_games_get_meeting_point_75_minutes_before_and_90_minutes_duration(lauf):
    archiv = json.loads((lauf / "data" / "m1-spiele.json").read_text(encoding="utf-8"))
    mit_uhrzeit = [eintrag for eintrag in archiv if not eintrag["all_day"]]
    assert mit_uhrzeit

    for eintrag in mit_uhrzeit:
        anwurf = datetime.fromisoformat(eintrag["dtstart"])
        treffpunkt = (anwurf - timedelta(minutes=75)).strftime("%H:%M")
        assert eintrag["description"].splitlines()[0] == f"Treffpunkt: {treffpunkt}"
        assert datetime.fromisoformat(eintrag["dtend"]) - anwurf == timedelta(minutes=90)
        assert re.match(r"^(ABGESAGT )?1\. Herren (Heim|Auswärts) ", eintrag["summary"])
        assert eintrag["uid"].startswith("tbw-m1-spiel-")


def test_pool_carries_the_teams_and_feeds_of_this_repository(lauf):
    pool = _pool(lauf)

    assert [team["key"] for team in pool["teams"]] == ["m1", "1-damen", "2-herren", "watch"]
    assert [feed["key"] for feed in pool["feeds"]] == ["m1-training", "m1-spiele", "extra"]
    assert pool["feeds"][1]["name"] == "1. Herren Spiele"
    assert pool["feeds"][1]["short_name"] == "M1 Spiele"


def test_pool_separates_own_and_foreign_games(lauf):
    events = _pool(lauf)["events"]

    assert {e["team_key"] for e in events if e["own_team"]} == {"m1"}
    assert {e["team_key"] for e in events if not e["own_team"]} == {"1-damen", "2-herren"}
    # Der Eigenname der 2. Herren kommt aus dem X-WR-CALNAME ihres Feeds --
    # sonst stuende bei Heimspielen "TB Wülfrath II" als eigener Gegner da.
    zweite = [e["summary"] for e in events if e["team_key"] == "2-herren"]
    assert zweite
    assert not any("Wülfrath II" in titel for titel in zweite)
