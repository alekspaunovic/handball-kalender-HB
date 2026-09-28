import pytest

from handball_kalender.names import clean_handballnet_address, normalize_opponent


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Lüttringhauser TV", "Lüttringhauser TV"),
        ("NEUSSER HV 1M", "Neusser HV"),
        ("DJK GRÜN WEISS WERDEN 2.M", "DJK Grün Weiss Werden"),
        ("SSG WUPPERTAL/HSV WUPPERTAL", "SSG Wuppertal/HSV Wuppertal"),
        ("TB WÜLFRATH IV", "TB Wülfrath IV"),
        ("TUS LINTFORT", "TuS Lintfort"),
        ("MTG Horst Essen", "MTG Horst Essen"),
    ],
)
def test_normalize_opponent_examples(raw, expected):
    assert normalize_opponent(raw, {}) == expected


# Die neun Namen, die in den echten Quellen der sechs Teams daneben lagen.
@pytest.mark.parametrize(
    "raw,expected",
    [
        # Title Case über Bindestrich und Punkt hinweg
        ("WALD-MERSCHEIDER TV", "Wald-Merscheider TV"),
        (
            "INTERAKTIV.HANDBALL DÜSSELDORF/RATINGEN 2M",
            "Interaktiv.Handball Düsseldorf/Ratingen",
        ),
        ("JSG ELLER-GERRESHEIM C1J", "JSG Eller-Gerresheim"),
        # Rechtsform gehört nicht in den Kalendertitel, die römische Zahl schon
        ("DJK UNITAS HAAN E.V.", "DJK Unitas Haan"),
        ("DJK UNITAS HAAN E.V. II", "DJK Unitas Haan II"),
        ("FORTUNA DÜSSELDORF 1895 E.V. 1F", "Fortuna Düsseldorf 1895"),
        # Mannschaftskennungen der Jugend, auch bei gemischt geschriebenen Namen
        ("Solinger TB mA", "Solinger TB"),
        ("Solinger TB mC", "Solinger TB"),
        ("Kettwiger SV 70/86 männl. C-Jugend", "Kettwiger SV 70/86"),
    ],
)
def test_normalize_opponent_real_world_cases(raw, expected):
    assert normalize_opponent(raw, {}) == expected


# Kürzel ohne Vokal werden groß geschrieben, ohne dass sie in der Tabelle
# stehen müssen -- sonst wächst die Tabelle bei jedem neuen Gegner.
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("BTB AACHEN", "BTB Aachen"),
        ("LTV WUPPERTAL", "LTV Wuppertal"),
        ("PSV RECKLINGHAUSEN", "PSV Recklinghausen"),
        ("TSG 1893 LEIHGESTERN", "TSG 1893 Leihgestern"),
        ("BV BORUSSIA 09 DORTMUND II", "BV Borussia 09 Dortmund II"),
        ("1. FSV MAINZ 05 II", "1. FSV Mainz 05 II"),
        ("HC BSDL", "HC BSDL"),
        ("HBD LÖWEN OBERBERG", "HBD Löwen Oberberg"),
        ("HG LTG/HTV REMSCHEID", "HG LTG/HTV Remscheid"),
        ("VOHWINKELER STV", "Vohwinkeler STV"),
        ("TSG MZ-BRETZENHEIM", "TSG MZ-Bretzenheim"),
    ],
)
def test_consonant_abbreviations_stay_uppercase(raw, expected):
    assert normalize_opponent(raw, {}) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Mannschaftsnummer weg, Gründungsjahr bleibt
        ("OHLIGSER TV 1", "Ohligser TV"),
        ("MTV 1861 ELBERFELD 1", "MTV 1861 Elberfeld"),
        ("HSV ÜBERRUHR 1. MÄNNER", "HSV Überruhr"),
        ("TUS 82 OPLADEN", "TuS 82 Opladen"),
        ("MTV KÖLN 1850", "MTV Köln 1850"),
        ("FSV MAINZ 05", "FSV Mainz 05"),
    ],
)
def test_team_number_stripped_but_founding_year_kept(raw, expected):
    assert normalize_opponent(raw, {}) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Römische Zahlen bleiben, sie unterscheiden echte Mannschaften
        ("TB WÜLFRATH II", "TB Wülfrath II"),
        ("TB WÜLFRATH III", "TB Wülfrath III"),
        # "EV" ohne Punkt ist ein Vereinskürzel, keine Rechtsform
        ("EV DUISBURG", "EV Duisburg"),
        ("SG EVERSWINKEL", "SG Everswinkel"),
        # Jahreszahlen im Namen sind keine Mannschaftskennung
        ("TV 1885 ERKRATH", "TV 1885 Erkrath"),
        ("SV 09 MÖNCHENGLADBACH", "SV 09 Mönchengladbach"),
        # Zahlen mit Schrägstrich bleiben unangetastet
        ("SV 70/86 ESSEN", "SV 70/86 Essen"),
    ],
)
def test_normalize_opponent_does_not_overreach(raw, expected):
    assert normalize_opponent(raw, {}) == expected


def test_team_suffix_and_rechtsform_in_any_order():
    # Die Kennung kann vor oder hinter der Rechtsform stehen.
    assert normalize_opponent("TSV BEISPIEL E.V. 2.HERREN", {}) == "TSV Beispiel"
    assert normalize_opponent("TSV BEISPIEL 2.HERREN", {}) == "TSV Beispiel"


def test_normalize_opponent_override_wins_before_rules():
    overrides = {"NEUSSER HV 1M": "Neusser Handverein"}
    assert normalize_opponent("NEUSSER HV 1M", overrides) == "Neusser Handverein"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "BOCKMüHLE, MERCATORSTR., 45143 ESSEN, 45143 ESSEN",
            "Bockmühle, Mercatorstr., 45143 Essen, Deutschland",
        ),
        (
            "MATARé-GYMNASIUM, NIEDERDONKER STR. 34, 40667 MEERBUSCH, 40667 MEERBUSCH",
            "Mataré-Gymnasium, Niederdonker Str. 34, 40667 Meerbusch, Deutschland",
        ),
        # Umbruch auch am Punkt innerhalb eines Wortes, wie bei den Namen.
        (
            "RS.NEUENKAMP, NEUENKAMPER STRASSE 55, 42855 REMSCHEID, 42855 REMSCHEID",
            "Rs.Neuenkamp, Neuenkamper Strasse 55, 42855 Remscheid, Deutschland",
        ),
    ],
)
def test_clean_handballnet_address_examples(raw, expected):
    assert clean_handballnet_address(raw) == expected


def test_address_cleanup_capitalizes_after_a_bracket():
    """str.capitalize schreibt nur das erste Zeichen groß -- steht dort eine
    Klammer, bliebe der Rest klein."""
    assert clean_handballnet_address(
        "VOSS-ARENA (WIPPERFÜRTH.AM MÜHLENBERG), OSTLANDSTRASSE 17, 51688 WIPPERFÜRTH"
    ) == (
        "Voss-Arena (Wipperfürth.Am Mühlenberg), Ostlandstrasse 17, "
        "51688 Wipperfürth, Deutschland"
    )


def test_address_cleanup_keeps_house_number_suffixes_lowercase():
    assert clean_handballnet_address("RAHMER KIRCHWEG 19A, 47647 KERKEN") == (
        "Rahmer Kirchweg 19a, 47647 Kerken, Deutschland"
    )
    assert clean_handballnet_address("MUSTERWEG 7B, 12345 ORT") == (
        "Musterweg 7b, 12345 Ort, Deutschland"
    )


def test_address_cleanup_keeps_street_abbreviations_lowercase_after_the_dot():
    """STR. muss Str. bleiben -- die Konsonantenregel aus dem Namenspfad darf
    hier nicht greifen, sonst entstünde STR."""
    assert clean_handballnet_address("MERCATORSTR., 45143 ESSEN") == (
        "Mercatorstr., 45143 Essen, Deutschland"
    )
    assert clean_handballnet_address("INDUSTRIESTR. 7, 47447 MOERS") == (
        "Industriestr. 7, 47447 Moers, Deutschland"
    )
