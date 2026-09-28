from handball_kalender.textnorm import normalize


def test_normalize_lowercases_and_transliterates_umlauts():
    assert normalize("Wülfrath") == "wuelfrath"
    assert normalize("WÜLFRATH") == "wuelfrath"


def test_normalize_strips_spaces_and_punctuation():
    assert normalize("MTC Arena Wülfrath") == "mtcarenawuelfrath"
    assert normalize("Franky's Gym") == "frankysgym"
    assert normalize("Franky’s Gym") == "frankysgym"


def test_normalize_handles_eszett():
    assert normalize("Straße") == "strasse"
