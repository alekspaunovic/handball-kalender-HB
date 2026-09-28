"""Gemeinsames Event-Modell, entspricht dem Archiv-Schema aus SPEC.md Abschnitt 10."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Event:
    uid: str
    source_uid: str
    summary: str
    dtstart: datetime | date
    dtend: datetime | date
    all_day: bool
    location: str | None
    geo: tuple[float, float] | None
    description: str
    url: str
    cancelled: bool
