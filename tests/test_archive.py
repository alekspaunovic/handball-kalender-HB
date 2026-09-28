from datetime import datetime
from zoneinfo import ZoneInfo

from handball_kalender import archive
from handball_kalender.models import Event

BERLIN = ZoneInfo("Europe/Berlin")


def _spiel_event(dtstart, summary="3. Herren Heim TV Beispiel", uid="tbw-m3-spiel-1"):
    return Event(
        uid=uid,
        source_uid="spiel-1@mmcc-news",
        summary=summary,
        dtstart=dtstart,
        dtend=dtstart,
        all_day=False,
        location="Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
        geo=(51.282, 7.0398),
        description="Treffpunkt: 14:35",
        url="https://www.handball.net/match/1",
        cancelled=False,
    )


def _archive_entry(dtstart, first_seen, last_seen, summary="3. Herren Heim TV Beispiel", uid="tbw-m3-spiel-1"):
    return {
        "uid": uid,
        "source_uid": "spiel-1@mmcc-news",
        "summary": summary,
        "dtstart": dtstart.isoformat(),
        "dtend": dtstart.isoformat(),
        "all_day": False,
        "location": "Sporthalle Fliethe, Fortunastraße 30, 42489 Wülfrath, Deutschland",
        "geo": [51.282, 7.0398],
        "description": "Treffpunkt: 14:35",
        "url": "https://www.handball.net/match/1",
        "cancelled": False,
        "first_seen": first_seen.isoformat(),
        "last_seen": last_seen.isoformat(),
    }


def test_new_event_gets_first_and_last_seen():
    now = datetime(2026, 9, 2, 9, 0, tzinfo=BERLIN)
    event = _spiel_event(datetime(2026, 9, 19, 15, 50, tzinfo=BERLIN))
    result = archive.merge([], [event], now)
    assert len(result) == 1
    assert result[0]["first_seen"] == now.isoformat()
    assert result[0]["last_seen"] == now.isoformat()
    assert result[0]["cancelled"] is False


def test_disappeared_event_before_its_date_stays_unchanged():
    now = datetime(2026, 9, 2, 9, 0, tzinfo=BERLIN)
    first_seen = datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN)
    existing = [_archive_entry(datetime(2026, 9, 19, 15, 50, tzinfo=BERLIN), first_seen, first_seen)]

    result = archive.merge(existing, [], now)
    assert len(result) == 1
    assert result[0]["cancelled"] is False
    assert not result[0]["summary"].startswith("ABGESAGT ")


def test_disappeared_event_after_its_date_gets_abgesagt():
    now = datetime(2026, 9, 20, 9, 0, tzinfo=BERLIN)
    first_seen = datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN)
    existing = [_archive_entry(datetime(2026, 9, 19, 15, 50, tzinfo=BERLIN), first_seen, first_seen)]

    result = archive.merge(existing, [], now)
    assert len(result) == 1
    assert result[0]["cancelled"] is True
    assert result[0]["summary"] == "ABGESAGT 3. Herren Heim TV Beispiel"


def test_uid_stays_stable_when_time_or_location_changes():
    now = datetime(2026, 9, 2, 9, 0, tzinfo=BERLIN)
    original = _spiel_event(datetime(2026, 9, 19, 15, 50, tzinfo=BERLIN))
    existing = archive.merge([], [original], now)

    later = datetime(2026, 9, 3, 9, 0, tzinfo=BERLIN)
    moved = _spiel_event(datetime(2026, 9, 19, 17, 0, tzinfo=BERLIN))
    moved.location = "Sporthalle Flehenberg, Flehenberg 91, 42489 Wülfrath, Deutschland"

    result = archive.merge(existing, [moved], later)
    assert len(result) == 1
    assert result[0]["uid"] == original.uid
    assert result[0]["dtstart"] == moved.dtstart.isoformat()
    assert result[0]["location"] == moved.location
    assert result[0]["first_seen"] == now.isoformat()
    assert result[0]["last_seen"] == later.isoformat()
