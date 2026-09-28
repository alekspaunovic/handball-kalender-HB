"""SPEC-ADMIN.md Abschnitt 3 und 9: gemerkte Spiele beliebiger Vereine."""

from datetime import datetime, timezone as dt_timezone
from pathlib import Path

import pytest

from handball_kalender import archive, ics_io, watch

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"
NOW = datetime(2026, 9, 24, 6, 0, tzinfo=dt_timezone.utc)


# --- Eingabeformen (SPEC-ADMIN.md Abschnitt 6) ---------------------------


@pytest.mark.parametrize(
    "eingabe",
    [
        "https://www.handball.net/match/563599",
        "https://www.handball.net/kalender/spiel/563599.ics",
        "563599",
        "  563599  ",
        "http://handball.net/match/563599",
        "www.handball.net/match/563599?ref=irgendwas",
    ],
)
def test_all_input_forms_give_the_same_match_id(eingabe):
    assert watch.match_id(eingabe) == "563599"


@pytest.mark.parametrize(
    "eingabe",
    ["", "   ", "abc", "https://www.handball.net/", "2627NROLAJMA0102",
     "https://example.com/match/563599", "563599er"],
)
def test_unusable_input_is_rejected(eingabe):
    assert watch.match_id(eingabe) is None


def test_verbands_spielnummer_is_not_a_match_id():
    # Steht in der DESCRIPTION, lässt sich über diesen Endpunkt nicht auflösen.
    assert watch.match_id("2627NROLAJMA0102") is None


# --- Transformation ------------------------------------------------------


def _vevent(mid):
    cal = ics_io.parse_calendar((FIXTURES_DIR / f"handballnet-spiel-{mid}.ics").read_bytes())
    return next(iter(ics_io.iter_vevents(cal)))


def _transform(config, mid, vevent=None):
    return watch.transform(
        vevent if vevent is not None else _vevent(mid),
        mid,
        config.halls,
        config.opponent_overrides,
        config.uid_prefix,
        config.timezone,
        config.teams["watch"].spieldauer_minuten,
    )


def test_title_is_only_the_two_clubs(config):
    event = _transform(config, "563599")
    assert event.summary == "TV Aldekerk II - SG Langenfeld"


def test_roman_numerals_are_kept(config):
    # Ohne die II wäre nicht erkennbar, welche Mannschaft spielt.
    assert "II" in _transform(config, "563599").summary


def test_team_suffixes_are_kept(config):
    # Hier steht kein eigenes Team im Titel, also ist mA die einzige
    # Unterscheidung zur ersten Mannschaft.
    event = _transform(config, "563602")
    assert event.summary == "HBD Löwen Oberberg - Solinger TB mA"


def test_no_age_group_and_no_prefix_in_the_title(config):
    event = _transform(config, "563599")
    for unerwuenscht in ("Heim", "Auswärts", "A-Jugend", "Oberliga", "2. Herren"):
        assert unerwuenscht not in event.summary


def test_uid_uses_the_watch_prefix(config):
    assert _transform(config, "563599").uid == "tbw-watch-spiel-563599"


def test_duration_is_ninety_minutes_from_anwurf(config):
    event = _transform(config, "563599")
    # Die Quelle liefert 15:00-17:00, das sind die unbrauchbaren zwei Stunden.
    assert event.dtstart.strftime("%H:%M") == "15:00"
    assert event.dtend.strftime("%H:%M") == "16:30"
    assert (event.dtend - event.dtstart).total_seconds() == 90 * 60


def test_note_contains_only_the_liga(config):
    event = _transform(config, "563599")
    assert event.description == "Oberliga männliche Jugend A"
    assert "Treffpunkt" not in event.description
    # Das Ergebnis aus der SUMMARY gehört hier nicht hinein.
    assert "41" not in event.description


def test_result_is_not_in_the_title_either(config):
    assert "(41:31)" not in _transform(config, "563599").summary


def test_location_uses_the_generic_cleanup_for_unknown_halls(config):
    event = _transform(config, "563599")
    # Doppelte PLZ/Stadt entfernt, Title Case, ", Deutschland" angehängt.
    assert event.location == (
        "Sportzentrum Aldekerk, Rahmer Kirchweg 19a, 47647 Kerken, Deutschland"
    )


def test_location_uses_the_hall_table_when_known(config):
    vevent = _vevent("563599")
    vevent["LOCATION"] = "MTC ARENA WÜLFRATH, FORTUNA STR. 30, 42489 WÜLFRATH"
    event = _transform(config, "563599", vevent)
    assert event.location == (
        "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland"
    )
    assert event.geo == (51.2759225, 7.0168646)


def test_liga_is_the_first_description_line():
    beschreibung = "Oberliga männliche Jugend A\nSpieltag 1\nSpielnummer X\nFinalizado\nhttps://…"
    assert watch.liga(beschreibung) == "Oberliga männliche Jugend A"
    assert watch.liga("") == ""


# --- Verhalten -----------------------------------------------------------


def test_withdrawn_match_gets_abgesagt_prefix(config):
    vevent = _vevent("563599")
    vevent["DESCRIPTION"] = "Oberliga männliche Jugend A\nSpieltag 1\nRetirado"
    event = _transform(config, "563599", vevent)
    assert event.summary == "ABGESAGT TV Aldekerk II - SG Langenfeld"
    assert event.cancelled is True
    assert event.uid == "tbw-watch-spiel-563599"


def test_moved_match_keeps_its_uid_and_moves(config):
    original = _transform(config, "563599")
    archiv = archive.merge([], [original], NOW)

    verlegt_vevent = _vevent("563599")
    verlegt_vevent["DTSTART"].dt = verlegt_vevent["DTSTART"].dt.replace(day=20, hour=18)
    verlegt = _transform(config, "563599", verlegt_vevent)

    spaeter = datetime(2026, 9, 25, 6, 0, tzinfo=dt_timezone.utc)
    ergebnis = archive.merge(archiv, [verlegt], spaeter)

    assert len(ergebnis) == 1
    assert ergebnis[0]["uid"] == original.uid
    assert ergebnis[0]["dtstart"].startswith("2026-09-20T18:00:00")


def test_all_day_match_gets_uhrzeit_noch_offen(config):
    from datetime import date

    vevent = _vevent("563599")
    vevent["DTSTART"].dt = date(2026, 10, 3)
    vevent["DTEND"].dt = date(2026, 10, 4)
    event = _transform(config, "563599", vevent)

    assert event.all_day is True
    assert event.description == "Uhrzeit noch offen\nOberliga männliche Jugend A"


def test_protected_uid_is_not_marked_cancelled_when_missing():
    """Schlägt der Abruf einer Spielnummer fehl, wissen wir nichts über das
    Spiel und dürfen es nicht als abgesagt markieren."""
    eintrag = {
        "uid": "tbw-watch-spiel-563599",
        "source_uid": "spiel-563599@mmcc-news",
        "summary": "TV Aldekerk II - SG Langenfeld",
        "dtstart": "2026-09-13T15:00:00+02:00",
        "dtend": "2026-09-13T16:30:00+02:00",
        "all_day": False,
        "location": None,
        "geo": None,
        "description": "Oberliga männliche Jugend A",
        "url": "",
        "cancelled": False,
        "first_seen": NOW.isoformat(),
        "last_seen": NOW.isoformat(),
    }
    danach = datetime(2026, 9, 20, 6, 0, tzinfo=dt_timezone.utc)

    geschuetzt = archive.merge([eintrag], [], danach, protect={eintrag["uid"]})
    assert geschuetzt[0]["cancelled"] is False
    assert geschuetzt[0]["summary"] == "TV Aldekerk II - SG Langenfeld"

    # Ohne Schutz greift die Verschwinden-Logik wie gewohnt -- ein echtes 404
    # von handball.net ist eine Aussage und kommt diesen Weg.
    ungeschuetzt = archive.merge([eintrag], [], danach)
    assert ungeschuetzt[0]["cancelled"] is True
    assert ungeschuetzt[0]["summary"].startswith("ABGESAGT ")
