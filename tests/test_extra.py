"""SPEC-ADMIN.md Abschnitt 4 und 9: der Extra-Feed aus eigenen Terminen und
freigeschalteten Fremdspielen."""

import logging
from datetime import datetime, timezone as dt_timezone

import pytest

from handball_kalender import archive, extra, ics_io, spiele
from handball_kalender.overrides import Overrides

NOW = datetime(2026, 9, 24, 6, 0, tzinfo=dt_timezone.utc)

CUSTOM = {
    "uid": "tbw-custom-a1b2c3",
    "summary": "Mannschaftsabend",
    "dtstart": "2026-11-14T19:00:00",
    "dtend": "2026-11-14T23:00:00",
    "all_day": False,
    "location": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
    "description": "",
    "created": "2026-09-24T18:00:00Z",
}


def _vevent(status="Finalizado", dtstart="20260913T130000", ergebnis=" (33:26)"):
    """Ein A-Jugend-Spiel im Format von handball.net."""
    raw = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nX-WR-CALNAME:TB WÜLFRATH\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:spiel-563597@mmcc-news\r\n"
        f"DTSTART:{dtstart}\r\n"
        "DTEND:20260913T150000\r\n"
        f"SUMMARY:TB WÜLFRATH - HSG WESEL{ergebnis}\r\n"
        f"DESCRIPTION:Oberliga männliche Jugend A\\n{status}\r\n"
        "URL:https://www.handball.net/match/563597\r\n"
        "LOCATION:MTC ARENA WüLFRATH\\, FORTUNA STR. 30\\, 42489 WüLFRATH\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    cal = ics_io.parse_calendar(raw)
    return next(iter(ics_io.iter_vevents(cal)))


@pytest.fixture
def a_jugend(config):
    """Wie im echten Lauf: der Eigenname kommt aus dem X-WR-CALNAME der
    Quelle, weil config.yaml fuer Fremdteams keinen enthaelt."""
    cal = ics_io.parse_calendar(
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nX-WR-CALNAME:TB WÜLFRATH\r\nEND:VCALENDAR\r\n"
    )
    return spiele.resolve_own_name(config.teams["a-jugend"], cal)


def _transform(config, team, **kwargs):
    return spiele.transform(
        _vevent(**kwargs), team, config.halls, config.opponent_overrides,
        config.uid_prefix, config.timezone,
    )


def _archiv(config, team, **kwargs):
    """Archiv eines Fremdteams mit genau einem Spiel."""
    return {"a-jugend-spiele": archive.merge([], [_transform(config, team, **kwargs)], NOW)}


def test_custom_entry_lands_in_extra_feed_with_stable_uid(config):
    entries = extra.build_entries(
        Overrides(custom=[CUSTOM]), {}, config.halls, config.timezone
    )

    assert len(entries) == 1
    assert entries[0]["uid"] == "tbw-custom-a1b2c3"
    assert entries[0]["summary"] == "Mannschaftsabend"


def test_custom_entry_keeps_local_time_regardless_of_machine_timezone(config):
    entries = extra.build_entries(
        Overrides(custom=[CUSTOM]), {}, config.halls, config.timezone
    )

    # Ortszeit ohne Zonenangabe aus der Oberflaeche muss als Europe/Berlin
    # gelesen werden, nicht als Zeit des ausfuehrenden Rechners.
    assert entries[0]["dtstart"] == "2026-11-14T19:00:00+01:00"
    assert entries[0]["dtend"] == "2026-11-14T23:00:00+01:00"


def test_custom_entry_in_a_known_hall_gets_coordinates(config):
    entries = extra.build_entries(
        Overrides(custom=[CUSTOM]), {}, config.halls, config.timezone
    )

    assert entries[0]["geo"] == [51.2759225, 7.0168646]


def test_custom_all_day_entry_keeps_date_only(config):
    ganztags = dict(CUSTOM, all_day=True, dtstart="2026-11-14", dtend="2026-11-15")
    entries = extra.build_entries(
        Overrides(custom=[ganztags]), {}, config.halls, config.timezone
    )

    assert entries[0]["all_day"] is True
    assert entries[0]["dtstart"] == "2026-11-14"


def test_included_foreign_game_lands_in_extra_feed(config, a_jugend):
    archives = _archiv(config, a_jugend)
    uid = archives["a-jugend-spiele"][0]["uid"]
    assert uid == "tbw-a-jugend-spiel-563597"

    entries = extra.build_entries(
        Overrides(included={uid}), archives, config.halls, config.timezone
    )

    assert len(entries) == 1
    assert entries[0]["uid"] == uid
    assert entries[0]["summary"] == "A-Jugend Heim HSG Wesel"


def test_included_foreign_game_has_no_treffpunkt_note(config, a_jugend):
    archives = _archiv(config, a_jugend)
    entries = extra.build_entries(
        Overrides(included={archives["a-jugend-spiele"][0]["uid"]}),
        archives, config.halls, config.timezone,
    )

    # Zuschauertermin: kein Treffpunkt, aber das Ergebnis bleibt.
    assert "Treffpunkt" not in entries[0]["description"]
    assert entries[0]["description"] == "Ergebnis: 33:26"


def test_moved_foreign_game_moves_in_extra_feed_and_keeps_its_uid(config, a_jugend):
    archives = _archiv(config, a_jugend)
    uid = archives["a-jugend-spiele"][0]["uid"]
    vorher = extra.build_entries(
        Overrides(included={uid}), archives, config.halls, config.timezone
    )[0]

    verlegt = _transform(config, a_jugend, dtstart="20260920T180000")
    spaeter = datetime(2026, 9, 25, 6, 0, tzinfo=dt_timezone.utc)
    archives["a-jugend-spiele"] = archive.merge(
        archives["a-jugend-spiele"], [verlegt], spaeter
    )

    nachher = extra.build_entries(
        Overrides(included={uid}), archives, config.halls, config.timezone
    )[0]

    assert nachher["uid"] == vorher["uid"]
    assert nachher["dtstart"] != vorher["dtstart"]
    assert nachher["dtstart"].startswith("2026-09-20T18:00:00")


def test_withdrawn_foreign_game_gets_abgesagt_prefix(config, a_jugend):
    archives = _archiv(config, a_jugend, status="Retirado")
    uid = archives["a-jugend-spiele"][0]["uid"]

    entries = extra.build_entries(
        Overrides(included={uid}), archives, config.halls, config.timezone
    )

    assert entries[0]["summary"] == "ABGESAGT A-Jugend Heim HSG Wesel"
    assert entries[0]["uid"] == uid


def test_unknown_included_uid_is_skipped_with_a_warning(config, caplog):
    with caplog.at_level(logging.WARNING):
        entries = extra.build_entries(
            Overrides(included={"tbw-a-jugend-spiel-999999"}), {},
            config.halls, config.timezone,
        )

    assert entries == []
    assert "tbw-a-jugend-spiel-999999" in caplog.text


def test_extra_feed_is_written_even_when_empty(config, tmp_path):
    path = tmp_path / "extra.ics"
    ics_io.write_feed(path, [], config.extra_calname, config.timezone, config.feed_ttl)

    raw = path.read_text(encoding="utf-8")
    assert "X-WR-CALNAME:TBW Extra" in raw
    assert "BEGIN:VEVENT" not in raw
