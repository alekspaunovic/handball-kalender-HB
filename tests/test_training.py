from handball_kalender import training
from handball_kalender.halls import hall_address


def _hall(halls, key):
    return next(h for h in halls if h.key == key)


def test_m3_training_without_ortszusatz_lands_on_fliethe(config, halls, spielerplus_m3):
    vevent = spielerplus_m3["training.76261594"]
    event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == hall_address(_hall(halls, "fliethe"))
    assert event.description == ""


def test_m3_training_with_erbacher_berg_resolves_hall(config, halls, spielerplus_m3):
    vevent = spielerplus_m3["training.77001458"]
    event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == hall_address(_hall(halls, "erbacher_berg"))
    assert event.summary == "Training 3. Herren - Erbacher Berg"


def test_m3_training_franky_gym_curly_apostrophe(config, halls, spielerplus_m3):
    vevent = spielerplus_m3["training.77001620"]
    event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == hall_address(_hall(halls, "frankys_gym"))


def test_m2_training_gets_treffpunkt_notiz_10min_before_start(config, halls, spielerplus_m2):
    vevent = spielerplus_m2["training.76020476"]
    event = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.dtstart.strftime("%H:%M") == "20:15"
    assert event.description == "Treffpunkt: 20:05"


def test_m2_teamevent_title_and_no_notiz(config, halls, spielerplus_m2):
    vevent = spielerplus_m2["event.2428839"]
    event = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.summary == "2. Herren: Teamevent"
    assert event.description == ""


def test_m2_training_with_source_location_keeps_it_instead_of_fliethe(config, halls, spielerplus_m2):
    """SPEC.md Abschnitt 5 (korrigiert): eine von der Quelle gelieferte
    LOCATION ist verlaesslicher als die Standardhalle Fliethe und darf nicht
    ueberschrieben werden, solange sie zu keiner bekannten Halle passt."""
    vevent = spielerplus_m2["training.76020476"]
    event = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == "Waldschlösschen 39, 42553 Velbert, Deutschland"
    assert event.geo == (51.303683, 7.079041)


def test_m2_auftakt_zur_vorbereitung_keeps_source_location_and_gets_notiz(config, halls, spielerplus_m2):
    """Diese Quelle liefert eine eigene LOCATION (Goethestrasse) und ist per
    UID-Praefix training.* -- bekommt also trotz abweichendem Titel die
    Treffpunkt-Notiz, aber nicht die Standardhalle Fliethe."""
    vevent = spielerplus_m2["training.75635936"]
    event = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.summary == "2. Herren: Auftakt zur Vorbereitung"
    assert event.location == "Goethestraße 23, 42489 Wülfrath, Deutschland"
    assert event.description.startswith("Treffpunkt: ")


def test_spiel_uid_is_discarded(config, halls):
    from icalendar import Event as IEvent
    from datetime import datetime
    from zoneinfo import ZoneInfo

    vevent = IEvent()
    vevent.add("UID", "spiel.123")
    vevent.add("SUMMARY", "Training")
    vevent.add("DTSTART", datetime(2026, 1, 1, 10, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    vevent.add("DTEND", datetime(2026, 1, 1, 12, 0, tzinfo=ZoneInfo("Europe/Berlin")))

    assert training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes) is None


def test_m3_training_halle_ortszusatz_is_treated_as_no_ortszusatz(config, halls, spielerplus_m3):
    """SpielerPlus gibt den Ort teils explizit als 'Halle' an, gemeint ist
    die Standardhalle Fliethe -- das darf nicht im Titel auftauchen."""
    vevent = spielerplus_m3["training.78506613"]
    event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.summary == "Training 3. Herren"
    assert event.location == hall_address(_hall(halls, "fliethe"))


def test_game_uid_is_discarded_regardless_of_positive_list(config, halls, spielerplus_m2):
    """Echtes VEVENT mit Praefix 'game.' aus dem realen SpielerPlus-Feed --
    Spiele kommen aus handball.net und duerfen nicht doppelt landen."""
    vevent = spielerplus_m2["game.13373164"]
    assert training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes) is None


def test_absence_uid_is_discarded_regardless_of_positive_list(config, halls, spielerplus_m2):
    """Echtes VEVENT mit Praefix 'absence.' aus dem realen SpielerPlus-Feed."""
    vevent = spielerplus_m2["absence.8595485"]
    assert training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes) is None


def test_unknown_uid_prefix_is_discarded_and_logged(config, halls, spielerplus_m2, caplog):
    """Echtes VEVENT mit dem unbekannten Praefix 'tournament.' -- muss
    verworfen UND als Warnung geloggt werden, damit nichts stillschweigend
    verlorengeht."""
    vevent = spielerplus_m2["tournament.2055844"]
    with caplog.at_level("WARNING"):
        result = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert result is None
    assert any("tournament.2055844" in record.message for record in caplog.records)


def test_m3_training_description_link_is_discarded(config, halls, spielerplus_m3):
    """SPEC.md Abschnitt 5: 'Die Quell-DESCRIPTION enthält nur den
    SpielerPlus-Link und wird verworfen.' Echtes Fixture-VEVENT hat eine
    DESCRIPTION mit exakt diesem Link."""
    vevent = spielerplus_m3["training.76261594"]
    assert "spielerplus.de" in str(vevent["DESCRIPTION"])
    event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert "spielerplus.de" not in event.description
    assert event.description == ""


def test_ortszusatz_wins_over_unreliable_source_location(config, halls):
    """SPEC.md Abschnitt 5 (Fall 1 vs. Fall 2): ein bekannter Ortszusatz im
    Titel geht vor einer vorhandenen LOCATION. Nachgebildet nach einem
    echten Produktionsfall, in dem SpielerPlus fuer M2-Trainings nur die
    unvollstaendige Rohadresse '42 Wülfrath, Deutschland' als LOCATION
    liefert, obwohl der Titel den Ort eindeutig benennt. Nicht aus den
    schlanken Test-Fixtures nachstellbar, da dort kein Training gleichzeitig
    Ortszusatz und LOCATION traegt -- deshalb ein konstruiertes VEVENT wie
    bei den anderen Positivlisten-Tests."""
    from icalendar import Event as IEvent
    from datetime import datetime
    from zoneinfo import ZoneInfo

    vevent = IEvent()
    vevent.add("UID", "training.99999999")
    vevent.add("SUMMARY", "Training - Flehenberg")
    vevent.add("LOCATION", "42 Wülfrath, Deutschland")
    vevent.add("GEO", (51.280284, 7.034961))
    vevent.add("DTSTART", datetime(2026, 1, 1, 19, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    vevent.add("DTEND", datetime(2026, 1, 1, 20, 30, tzinfo=ZoneInfo("Europe/Berlin")))

    event = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == hall_address(_hall(halls, "flehenberg"))


def test_source_location_matching_a_hall_gets_replaced_by_clean_entry(config, halls):
    """SPEC.md Abschnitt 5, Fall 2: eine LOCATION, die zu einer bekannten
    Halle passt, wird durch den einheitlichen Hallentabellen-Eintrag
    ersetzt statt roh übernommen. Verwendet die reale handball.net-Adresse
    aus SPEC.md/den Fixtures fuer die Fliethe ('MTC Arena Wülfrath')."""
    from icalendar import Event as IEvent
    from datetime import datetime
    from zoneinfo import ZoneInfo

    vevent = IEvent()
    vevent.add("UID", "training.99999998")
    vevent.add("SUMMARY", "Training")
    vevent.add("LOCATION", "MTC ARENA WüLFRATH, FORTUNA STR. 30, 42489 WüLFRATH")
    vevent.add("DTSTART", datetime(2026, 1, 1, 19, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    vevent.add("DTEND", datetime(2026, 1, 1, 20, 30, tzinfo=ZoneInfo("Europe/Berlin")))

    event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == hall_address(_hall(halls, "fliethe"))


def test_unknown_ortszusatz_without_location_becomes_raw_text_and_warns(config, halls, caplog):
    """SPEC.md Abschnitt 5, Fall 4: ein unbekannter Ortszusatz ohne LOCATION
    wird als reiner Text übernommen, mit Warnung im Log."""
    from icalendar import Event as IEvent
    from datetime import datetime
    from zoneinfo import ZoneInfo

    vevent = IEvent()
    vevent.add("UID", "training.99999997")
    vevent.add("SUMMARY", "Training - Sonstwo")
    vevent.add("DTSTART", datetime(2026, 1, 1, 19, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    vevent.add("DTEND", datetime(2026, 1, 1, 20, 30, tzinfo=ZoneInfo("Europe/Berlin")))

    with caplog.at_level("WARNING"):
        event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.summary == "Training 3. Herren - Sonstwo"
    assert event.location == "Sonstwo"
    assert event.geo is None
    assert any("Sonstwo" in record.message for record in caplog.records)


def test_m2_training_with_unusable_fragment_location_falls_back_to_fliethe(config, halls, caplog):
    """Echter Produktionsfall: SpielerPlus liefert fuer manche M2-Trainings
    nur das unbrauchbare LOCATION-Fragment '42 Wülfrath, Deutschland' (siehe
    auch event.2428839 in der Fixture) -- ohne Hausnummer und PLZ keine
    verlaessliche Adresse, wird wie keine LOCATION behandelt und faellt auf
    die Standardhalle Fliethe zurueck, mit Warnung im Log."""
    from icalendar import Event as IEvent
    from datetime import datetime
    from zoneinfo import ZoneInfo

    vevent = IEvent()
    vevent.add("UID", "training.88888888")
    vevent.add("SUMMARY", "Training")
    vevent.add("LOCATION", "42 Wülfrath, Deutschland")
    vevent.add("GEO", (51.280284, 7.034961))
    vevent.add("DTSTART", datetime(2026, 1, 1, 19, 0, tzinfo=ZoneInfo("Europe/Berlin")))
    vevent.add("DTEND", datetime(2026, 1, 1, 20, 30, tzinfo=ZoneInfo("Europe/Berlin")))

    with caplog.at_level("WARNING"):
        event = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == hall_address(_hall(halls, "fliethe"))
    assert event.geo == _hall(halls, "fliethe").geo
    assert any("42 Wülfrath" in record.message for record in caplog.records)


def test_plausible_foreign_address_without_hall_match_is_kept(config, halls, spielerplus_m2):
    """Eine LOCATION mit Hausnummer und fuenfstelliger PLZ, die zu keiner
    Halle passt, ist eine echte Fremdadresse (Auswaertstraining) und wird
    nicht durch Fliethe ersetzt."""
    vevent = spielerplus_m2["training.76020476"]
    event = training.transform(vevent, config.teams["m2"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
    assert event.location == "Waldschlösschen 39, 42553 Velbert, Deutschland"
    assert event.geo == (51.303683, 7.079041)


def test_every_hall_matched_training_event_has_geo(config, halls, spielerplus_m3):
    """Alle vier Hallen haben jetzt echte Koordinaten -- jedes VEVENT, dessen
    Ort auf eine bekannte Halle aufgeloest wird, muss ein GEO-Feld bekommen
    (Kartendarstellung im Apple-Kalender)."""
    cases = {
        "training.77001955": "flehenberg",
        "training.77001458": "erbacher_berg",
        "training.77001620": "frankys_gym",
        "training.78506613": "fliethe",
    }
    for source_uid, hall_key in cases.items():
        vevent = spielerplus_m3[source_uid]
        event = training.transform(vevent, config.teams["m3"], halls, config.uid_prefix, config.spielerplus_uid_prefixes)
        assert event.geo is not None, f"{source_uid} ({hall_key}) hat kein GEO"
        assert event.geo == _hall(halls, hall_key).geo


def test_filter_archive_entries_purges_stale_disallowed_prefixes(config):
    """Vor der Positivliste landeten game./absence./tournament.-Praefixe
    faelschlich als Kategorie 'event' im Archiv (siehe data/m2-training.json
    vor diesem Fix). archive.merge laesst nicht mehr gesehene Eintraege
    unbegrenzt stehen -- ohne diese Bereinigung wuerden sie nie
    verschwinden."""
    existing = [
        {"source_uid": "training.1", "uid": "tbw-m2-training-1"},
        {"source_uid": "event.1", "uid": "tbw-m2-event-1"},
        {"source_uid": "game.1", "uid": "tbw-m2-event-2"},
        {"source_uid": "absence.1", "uid": "tbw-m2-event-3"},
        {"source_uid": "tournament.1", "uid": "tbw-m2-event-4"},
    ]
    kept = training.filter_archive_entries(existing, config.spielerplus_uid_prefixes)
    assert [e["source_uid"] for e in kept] == ["training.1", "event.1"]


def test_filter_archive_entries_logs_unknown_prefix(config, caplog):
    existing = [{"source_uid": "tournament.1", "uid": "tbw-m2-event-4"}]
    with caplog.at_level("WARNING"):
        kept = training.filter_archive_entries(existing, config.spielerplus_uid_prefixes)
    assert kept == []
    assert any("tournament.1" in record.message for record in caplog.records)


def test_only_training_and_event_uids_survive_a_mixed_feed(config, halls):
    """Positivliste (SPEC.md Abschnitt 2): von allen vier realen Praefixen
    ueberleben nur training. und event."""
    from icalendar import Event as IEvent
    from datetime import datetime
    from zoneinfo import ZoneInfo

    def _vevent(uid, summary="Training"):
        v = IEvent()
        v.add("UID", uid)
        v.add("SUMMARY", summary)
        v.add("DTSTART", datetime(2026, 1, 1, 10, 0, tzinfo=ZoneInfo("Europe/Berlin")))
        v.add("DTEND", datetime(2026, 1, 1, 12, 0, tzinfo=ZoneInfo("Europe/Berlin")))
        return v

    team = config.teams["m3"]
    kept = [
        prefix
        for prefix in ("training", "event", "game", "absence")
        if training.transform(
            _vevent(f"{prefix}.1"), team, halls, config.uid_prefix, config.spielerplus_uid_prefixes
        )
        is not None
    ]
    assert kept == ["training", "event"]
