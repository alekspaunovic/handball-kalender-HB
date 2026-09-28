from handball_kalender import ics_io


def _entry(**overrides):
    base = {
        "uid": "tbw-m3-training-1",
        "summary": "Training 3. Herren - Erbacher Berg",
        "dtstart": "2026-09-19T19:00:00+02:00",
        "dtend": "2026-09-19T22:00:00+02:00",
        "all_day": False,
        "location": "Sportplatz Erbacher Berg (1. FC), Silberberger Weg 3, Innenstadt, 42489 Wülfrath, Deutschland",
        "geo": None,
        "description": "",
        "url": "",
        "cancelled": False,
    }
    base.update(overrides)
    return base


def test_write_feed_headers_and_no_valarm(tmp_path):
    path = tmp_path / "m3-training.ics"
    ics_io.write_feed(path, [_entry()], "TBW 3. Herren Training", "Europe/Berlin", "PT6H")

    text = path.read_text(encoding="utf-8")
    assert "X-WR-CALNAME:TBW 3. Herren Training" in text
    assert "X-WR-TIMEZONE:Europe/Berlin" in text
    assert "X-PUBLISHED-TTL:PT6H" in text
    assert "REFRESH-INTERVAL" in text
    assert "VALARM" not in text


def test_write_feed_keeps_umlauts_utf8(tmp_path):
    path = tmp_path / "m3-training.ics"
    ics_io.write_feed(path, [_entry()], "TBW 3. Herren Training", "Europe/Berlin", "PT6H")

    data = path.read_bytes()
    assert "Erbacher Berg".encode("utf-8") in data
    assert "Wülfrath".encode("utf-8") in data


def test_write_feed_uses_named_timezone_not_fixed_offset(tmp_path):
    path = tmp_path / "m3-training.ics"
    ics_io.write_feed(path, [_entry()], "TBW 3. Herren Training", "Europe/Berlin", "PT6H")
    text = path.read_text(encoding="utf-8")
    assert "TZID=Europe/Berlin" in text
    assert "UTC+02:00" not in text
    assert "BEGIN:VTIMEZONE" in text
    assert "TZID:Europe/Berlin" in text


def test_write_feed_all_day_event(tmp_path):
    path = tmp_path / "m3-spiele.ics"
    entry = _entry(
        uid="tbw-m3-spiel-1",
        summary="3. Herren Auswärts TB Wülfrath IV",
        dtstart="2026-08-23",
        dtend="2026-08-24",
        all_day=True,
        location=None,
        description="Uhrzeit noch offen",
    )
    ics_io.write_feed(path, [entry], "TBW 3. Herren Spiele", "Europe/Berlin", "PT6H")
    text = path.read_text(encoding="utf-8")
    assert "DTSTART;VALUE=DATE:20260823" in text
    assert "DTEND;VALUE=DATE:20260824" in text


def test_write_feed_with_geo_adds_apple_structured_location(tmp_path):
    path = tmp_path / "m3-training.ics"
    entry = _entry(geo=[51.282, 7.0398])
    ics_io.write_feed(path, [entry], "TBW 3. Herren Training", "Europe/Berlin", "PT6H")
    text = path.read_text(encoding="utf-8")
    assert "GEO:51.282;7.0398" in text or "GEO:51.282,7.0398" in text
    assert "X-APPLE-STRUCTURED-LOCATION" in text
