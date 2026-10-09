import dataclasses

from handball_kalender import ics_io, spiele

# Ein Heimspiel der 2. Herren, nachdem handball.net das Team umbenannt hat:
# X-WR-CALNAME und SUMMARY tragen den neuen Namen, config.yaml noch den alten.
_UMBENANNT = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MMCC-News//Spielplan//DE
X-WR-CALNAME:TB WÜLFRATH M2
BEGIN:VEVENT
UID:spiel-380470@mmcc-news
DTSTAMP:20261001T094827Z
DTSTART:20261003T154500
DTEND:20261003T174500
SUMMARY:TB WÜLFRATH M2 - HSG Wesel
DESCRIPTION:Verbandsliga MÄNNLICH\\nSpieltag 3\\nPendiente
URL:https://www.handball.net/match/380470
LOCATION:MTC ARENA WüLFRATH\\, FORTUNA STR. 30\\, 42489 WüLFRATH
END:VEVENT
END:VCALENDAR
"""


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
    assert event.description == "Uhrzeit noch offen\nErgebnis: 34:25 (Gewonnen)"


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


def test_eigenname_aus_calname_nach_umbenennung(config, halls):
    """handball.net hat die Teams im Herbst 2026 umbenannt ("TB Wülfrath II"
    -> "TB WÜLFRATH M2"). Mit nur dem Namen aus config.yaml stand das eigene
    Team als Gegner im Titel ("2. Herren Heim TB Wülfrath M2"). Der
    X-WR-CALNAME zieht mit und zählt deshalb immer mit (SPEC.md Abschnitt 4)."""
    cal = ics_io.parse_calendar(_UMBENANNT.encode("utf-8"))
    vevent = next(iter(ics_io.iter_vevents(cal)))
    team = spiele.resolve_own_name(config.teams["m2"], cal)
    assert team.eigennamen == ("TB Wülfrath II", "TB WÜLFRATH M2")
    event = spiele.transform(
        vevent, team, halls, config.opponent_overrides, config.uid_prefix, config.timezone
    )
    assert event.summary == "2. Herren Heim HSG Wesel"


def test_eigenname_aus_config_gilt_weiter(config, halls, handballnet_m3):
    """Auch wenn der X-WR-CALNAME einmal nicht passt, erkennt der Name aus
    config.yaml das eigene Team weiter."""
    cal = ics_io.parse_calendar(
        _UMBENANNT.replace("X-WR-CALNAME:TB WÜLFRATH M2", "X-WR-CALNAME:Spielplan").encode("utf-8")
    )
    team = spiele.resolve_own_name(config.teams["m3"], cal)
    assert team.eigennamen == ("TB Wülfrath III", "Spielplan")
    event = spiele.transform(
        handballnet_m3["spiel-674195@mmcc-news"],
        team,
        halls,
        config.opponent_overrides,
        config.uid_prefix,
        config.timezone,
    )
    assert event.summary == "3. Herren Auswärts TB Wülfrath IV"


def test_kein_eigenname_auf_beiden_seiten_wird_geloggt(config, caplog):
    team = spiele.resolve_own_name(config.teams["m2"], ics_io.parse_calendar(_UMBENANNT.encode("utf-8")))
    with caplog.at_level("WARNING"):
        gegner = spiele.resolve_opponent("TV Beispiel", "HSG Wesel", team)
    assert gegner == "TV Beispiel"
    assert "Eigenname" in caplog.text


# --- Wertung hinter dem Ergebnis ---------------------------------------------

def _spiel_aus(config, halls, datei, team_key, teil_der_summary):
    """Ein Spiel aus einer Fixture, mit Eigennamen wie im echten Lauf."""
    from conftest import FIXTURES_DIR

    cal = ics_io.parse_calendar((FIXTURES_DIR / datei).read_bytes())
    team = spiele.resolve_own_name(config.teams[team_key], cal)
    vevent = next(v for v in ics_io.iter_vevents(cal) if teil_der_summary in str(v["SUMMARY"]))
    return spiele.transform(vevent, team, halls, config.opponent_overrides, config.uid_prefix, config.timezone)


def test_auswaerts_gewonnen_wenn_gast_mehr_tore_hat(config, halls):
    """TSG 1893 LEIHGESTERN - TB WÜLFRATH (23:34): Heim:Gast, Wülfrath ist Gast."""
    event = _spiel_aus(config, halls, "handballnet-1-damen.ics", "1-damen", "LEIHGESTERN")
    assert event.description.endswith("Ergebnis: 23:34 (Gewonnen)")


def test_auswaerts_verloren(config, halls):
    """BTB AACHEN - TB WÜLFRATH (42:20)."""
    event = _spiel_aus(config, halls, "handballnet-a-jugend.ics", "a-jugend", "BTB AACHEN")
    assert event.description.endswith("Ergebnis: 42:20 (Verloren)")


def test_heim_verloren(config, halls):
    """TB WÜLFRATH - PSV RECKLINGHAUSEN (37:40)."""
    event = _spiel_aus(config, halls, "handballnet-1-damen.ics", "1-damen", "RECKLINGHAUSEN")
    assert event.description.endswith("Ergebnis: 37:40 (Verloren)")


def test_unentschieden(config):
    team = spiele.resolve_own_name(config.teams["m2"], ics_io.parse_calendar(_UMBENANNT.encode("utf-8")))
    seite = spiele.eigene_seite("HSG Wesel", "TB WÜLFRATH M2", team)
    assert seite == "gast"
    assert spiele.wertung("27:27", seite) == "Unentschieden"


def test_turnier_seite_zaehlt_nicht_die_halle(config, halls, handballnet_mc):
    """Beim Turnier am 19.09. in Wipperfürth stand TB Wülfrath auf der
    Heimseite, gespielt wurde aber auswärts (Titel "Auswärts"). Für die
    Wertung zählt die Seite in der SUMMARY, denn nach ihr richtet sich die
    Reihenfolge des Ergebnisses."""
    import copy

    vevent = copy.deepcopy(handballnet_mc["spiel-677568@mmcc-news"])
    vevent["SUMMARY"] = f"{vevent['SUMMARY']} (16:10)"
    team = dataclasses.replace(config.teams["mc"], eigennamen=("TB Wülfrath", "TB WÜLFRATH"))
    event = spiele.transform(vevent, team, halls, config.opponent_overrides, config.uid_prefix, config.timezone)
    assert event.summary == "C-Jugend Auswärts MTG Horst Essen"
    assert event.description.endswith("Ergebnis: 16:10 (Gewonnen)")


def test_null_zu_null_ist_kein_unentschieden():
    """handball.net führt beim Freundschaftsspiel M4 - M3 am 19.09. ein 0:0 --
    ein Platzhalter, kein Ergebnis."""
    assert spiele.wertung("0:0", "gast") is None


def test_ohne_erkannte_seite_keine_wertung(config):
    team = spiele.resolve_own_name(config.teams["m2"], ics_io.parse_calendar(_UMBENANNT.encode("utf-8")))
    assert spiele.eigene_seite("TV Beispiel", "HSG Wesel", team) is None
    assert spiele.wertung("30:20", None) is None
