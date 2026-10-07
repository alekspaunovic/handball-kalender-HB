from datetime import date, datetime
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


def _archive_entry(
    dtstart, first_seen, last_seen, summary="3. Herren Heim TV Beispiel", uid="tbw-m3-spiel-1", cancelled=False
):
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
        "cancelled": cancelled,
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
    assert result[0]["abgesagt_weil"] == "verschwunden"


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


def test_disappeared_event_seen_after_its_start_has_taken_place():
    """Die C-Jugend-Spiele vom 19.09.2026 standen bis zum 28.09. in
    handball.net und fielen dann aus dem Team-Kalender. SpielerPlus macht
    dasselbe mit Trainings nach rund drei Monaten. Was die Quelle nach seinem
    Beginn noch geführt hat, hat stattgefunden und bleibt unverändert."""
    dtstart = datetime(2026, 9, 19, 11, 40, tzinfo=BERLIN)
    first_seen = datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN)
    last_seen = datetime(2026, 9, 28, 7, 1, tzinfo=BERLIN)
    existing = [_archive_entry(dtstart, first_seen, last_seen, summary="C-Jugend Auswärts SV Wipperfürth")]

    result = archive.merge(existing, [], datetime(2026, 10, 4, 14, 0, tzinfo=BERLIN))
    assert result[0]["cancelled"] is False
    assert result[0]["summary"] == "C-Jugend Auswärts SV Wipperfürth"
    assert "abgesagt_weil" not in result[0]


def test_all_day_event_counts_as_started_only_the_day_after():
    dtstart = date(2026, 9, 19)
    first_seen = datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN)
    now = datetime(2026, 9, 25, 9, 0, tzinfo=BERLIN)

    am_tag = _archive_entry(dtstart, first_seen, datetime(2026, 9, 19, 18, 0, tzinfo=BERLIN))
    am_tag["all_day"] = True
    assert archive.merge([am_tag], [], now)[0]["cancelled"] is True

    am_folgetag = _archive_entry(dtstart, first_seen, datetime(2026, 9, 20, 9, 0, tzinfo=BERLIN))
    am_folgetag["all_day"] = True
    assert archive.merge([am_folgetag], [], now)[0]["cancelled"] is False


def test_source_cancellation_survives_disappearing_after_start():
    """Eine Absage der Quelle (handball.net: Retirado) hebt nur die Quelle
    wieder auf -- auch wenn der Termin danach aus der Quelle fällt."""
    dtstart = datetime(2026, 9, 10, 20, 0, tzinfo=BERLIN)
    event = _spiel_event(dtstart, summary="ABGESAGT 3. Herren Heim TV Beispiel")
    event.cancelled = True
    archiv = archive.merge([], [event], datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN))
    archiv = archive.merge(archiv, [event], datetime(2026, 9, 20, 9, 0, tzinfo=BERLIN))
    assert archiv[0]["abgesagt_weil"] == "quelle"

    result = archive.merge(archiv, [], datetime(2026, 12, 20, 9, 0, tzinfo=BERLIN))
    assert result[0]["cancelled"] is True
    assert result[0]["summary"] == "ABGESAGT 3. Herren Heim TV Beispiel"
    assert result[0]["abgesagt_weil"] == "quelle"


def test_reappearing_event_lifts_vanish_cancellation():
    dtstart = datetime(2026, 9, 19, 15, 50, tzinfo=BERLIN)
    first_seen = datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN)
    existing = [_archive_entry(dtstart, first_seen, first_seen)]
    archiv = archive.merge(existing, [], datetime(2026, 9, 20, 9, 0, tzinfo=BERLIN))
    assert archiv[0]["cancelled"] is True

    result = archive.merge(archiv, [_spiel_event(dtstart)], datetime(2026, 9, 21, 9, 0, tzinfo=BERLIN))
    assert result[0]["cancelled"] is False
    assert result[0]["summary"] == "3. Herren Heim TV Beispiel"
    assert "abgesagt_weil" not in result[0]


def test_legacy_vanish_cancellation_of_played_event_is_lifted():
    """Archive von vor "abgesagt_weil": die alte Verschwinden-Logik hat auch
    Termine abgesagt, die nach ihrem Beginn noch in der Quelle standen. Die
    werden beim nächsten Lauf zurückgenommen."""
    dtstart = datetime(2026, 9, 19, 11, 40, tzinfo=BERLIN)
    first_seen = datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN)
    last_seen = datetime(2026, 9, 28, 7, 1, tzinfo=BERLIN)
    existing = [
        _archive_entry(
            dtstart, first_seen, last_seen, summary="ABGESAGT C-Jugend Auswärts SV Wipperfürth", cancelled=True
        )
    ]

    result = archive.merge(existing, [], datetime(2026, 10, 4, 14, 0, tzinfo=BERLIN))
    assert result[0]["cancelled"] is False
    assert result[0]["summary"] == "C-Jugend Auswärts SV Wipperfürth"
    assert "abgesagt_weil" not in result[0]


def test_legacy_vanish_cancellation_before_start_stays():
    dtstart = datetime(2026, 9, 19, 15, 50, tzinfo=BERLIN)
    first_seen = datetime(2026, 9, 1, 9, 0, tzinfo=BERLIN)
    existing = [
        _archive_entry(dtstart, first_seen, first_seen, summary="ABGESAGT 3. Herren Heim TV Beispiel", cancelled=True)
    ]

    result = archive.merge(existing, [], datetime(2026, 10, 4, 14, 0, tzinfo=BERLIN))
    assert result[0]["cancelled"] is True
    assert result[0]["summary"] == "ABGESAGT 3. Herren Heim TV Beispiel"
    assert result[0]["abgesagt_weil"] == "verschwunden"
