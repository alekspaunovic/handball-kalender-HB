"""ICS parsen (Quellen) und ICS-Feeds schreiben (SPEC.md Abschnitt 3)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from icalendar import Calendar, Timezone
from icalendar.prop import vUri

_DURATION_RE = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")


def parse_duration(value: str) -> timedelta:
    match = _DURATION_RE.match(value)
    if not match:
        raise ValueError(f"Unbekanntes Dauer-Format: {value!r}")
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def parse_calendar(raw: bytes | str) -> Calendar:
    return Calendar.from_ical(raw)


def iter_vevents(cal: Calendar):
    return cal.walk("VEVENT")


def calendar_name(cal: Calendar) -> str | None:
    """X-WR-CALNAME der Quelle. Bei handball.net steht dort der Eigenname des
    Teams (SPEC.md Abschnitt 4), den die Gegnererkennung braucht."""
    value = cal.get("X-WR-CALNAME")
    if value is None:
        return None
    return str(value) or None


def extract_geo(vevent) -> tuple[float, float] | None:
    geo = vevent.get("GEO")
    if geo is None:
        return None
    return (float(geo.latitude), float(geo.longitude))


def extract_location(vevent) -> str | None:
    location = vevent.get("LOCATION")
    if location is None:
        return None
    text = str(location)
    return text or None


def localize_naive(dt: datetime | date, tz_name: str) -> datetime | date:
    """handball.net liefert zeitgebundene Termine ohne TZID -- als
    Europe/Berlin interpretieren (X-WR-TIMEZONE der Quelle)."""
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo(tz_name))
    return dt


def _add_location(event, location: str | None, geo: tuple[float, float] | None) -> None:
    if not location:
        return
    event.add("LOCATION", location)
    if geo:
        lat, lon = geo
        event.add("GEO", (lat, lon))
        event.add(
            "X-APPLE-STRUCTURED-LOCATION",
            vUri(f"geo:{lat},{lon}"),
            parameters={
                "VALUE": "URI",
                "X-ADDRESS": location,
                "X-APPLE-RADIUS": "49",
                "X-TITLE": "",
            },
        )


def write_feed(
    path,
    entries: list[dict],
    calname: str,
    tz_name: str,
    ttl: str,
) -> None:
    from icalendar import Calendar as ICalendar
    from icalendar import Event as IEvent

    cal = ICalendar()
    cal.add("prodid", "-//TB Wuelfrath//Handball-Kalender//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", calname)
    cal.add("x-wr-timezone", tz_name)
    cal.add("x-published-ttl", ttl)
    cal.add("refresh-interval", parse_duration(ttl), parameters={"VALUE": "DURATION"})

    if any(not entry["all_day"] for entry in entries):
        cal.add_component(Timezone.from_tzid(tz_name))

    now = datetime.now(dt_timezone.utc)

    for entry in sorted(entries, key=lambda e: e["dtstart"]):
        event = IEvent()
        event.add("UID", entry["uid"])
        event.add("DTSTAMP", now)

        if entry["all_day"]:
            event.add("DTSTART", date.fromisoformat(entry["dtstart"][:10]))
            event.add("DTEND", date.fromisoformat(entry["dtend"][:10]))
        else:
            # ISO-Strings aus dem Archiv tragen nur den UTC-Offset, nicht
            # den Zonennamen -- auf die benannte Zone ummappen, damit
            # icalendar TZID=Europe/Berlin statt UTC+02:00 schreibt.
            tz = ZoneInfo(tz_name)
            event.add("DTSTART", datetime.fromisoformat(entry["dtstart"]).astimezone(tz))
            event.add("DTEND", datetime.fromisoformat(entry["dtend"]).astimezone(tz))

        event.add("SUMMARY", entry["summary"])
        if entry.get("description"):
            event.add("DESCRIPTION", entry["description"])
        if entry.get("url"):
            event.add("URL", entry["url"])

        _add_location(event, entry.get("location"), entry.get("geo"))

        cal.add_component(event)

    from pathlib import Path as _Path

    path = _Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(cal.to_ical())
