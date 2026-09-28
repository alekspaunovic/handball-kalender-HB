from handball_kalender import spiele


def test_m2_spiel_gegen_luettringhauser_tv_exact_title(config, halls, handballnet_m2):
    vevent = handballnet_m2["spiel-380455@mmcc-news"]
    event = spiele.transform(
        vevent, config.teams["m2"], halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    assert event.summary == "2. Herren Heim Lüttringhauser TV"


def test_mc_turnierspiel_heimseite_in_summary_is_actually_auswaerts(config, halls, handballnet_mc):
    """Voss-Arena Wipperfuerth ist ein Turnier: TB Wuelfrath steht in der
    SUMMARY auf der Heimseite, die Halle ist aber nicht Fliethe -- also
    Auswaerts (Heim/Auswaerts wird ausschliesslich ueber die Halle
    bestimmt, siehe SPEC.md Abschnitt 6)."""
    vevent = handballnet_mc["spiel-677568@mmcc-news"]
    event = spiele.transform(
        vevent, config.teams["mc"], halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    assert "Auswärts" in event.summary
    assert event.summary == "C-Jugend Auswärts MTG Horst Essen"


def test_wuelfrath_iii_vs_iv_resolves_correct_opponent_all_day_and_result(config, halls, handballnet_m3):
    vevent = handballnet_m3["spiel-674195@mmcc-news"]
    event = spiele.transform(
        vevent, config.teams["m3"], halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    assert event.summary == "3. Herren Auswärts TB Wülfrath IV"
    assert event.all_day is True
    assert event.description == "Uhrzeit noch offen\nErgebnis: 34:25"


def test_retirado_gets_abgesagt_prefix(config, halls, handballnet_m3):
    vevent = handballnet_m3["spiel-677881@mmcc-news"]
    event = spiele.transform(
        vevent, config.teams["m3"], halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    assert event.summary.startswith("ABGESAGT ")
    assert event.cancelled is True


def test_unknown_location_gets_generic_cleanup_and_is_auswaerts(config, halls, handballnet_m3):
    vevent = handballnet_m3["spiel-645397@mmcc-news"]
    event = spiele.transform(
        vevent, config.teams["m3"], halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    assert event.location == "Bockmühle, Mercatorstr., 45143 Essen, Deutschland"
    assert "Auswärts" in event.summary
    assert event.geo is None


def test_no_location_is_auswaerts(config, halls, handballnet_m3):
    vevent = handballnet_m3["spiel-680658@mmcc-news"]
    event = spiele.transform(
        vevent, config.teams["m3"], halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    assert "Auswärts" in event.summary
    assert event.location is None


def test_heimhalle_fliethe_gets_treffpunkt_notiz(config, halls, handballnet_m2):
    vevent = handballnet_m2["spiel-380455@mmcc-news"]
    event = spiele.transform(
        vevent, config.teams["m2"], halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    # Anwurf 15:50, Vorlauf m2 = 75 Minuten
    assert event.description == "Treffpunkt: 14:35"


def test_opponent_override_applied(config, halls, handballnet_m2):
    vevent = handballnet_m2["spiel-681302@mmcc-news"]
    overrides = {"NEUSSER HV 1M": "Neusser Handballverein"}
    event = spiele.transform(
        vevent, config.teams["m2"], halls, overrides, config.uid_prefix, config.timezone
    )
    assert "Neusser Handballverein" in event.summary
