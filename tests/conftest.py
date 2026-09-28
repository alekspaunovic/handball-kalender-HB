from pathlib import Path

import pytest

from handball_kalender import ics_io
from handball_kalender.config import load_config

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"
# Die Fixtures stammen aus dem Ursprungsrepository (M2, M3, MC). Die Tests
# laufen deshalb gegen dessen Konfiguration, nicht gegen config.yaml im
# Wurzelverzeichnis -- die gehoert den 1. Herren (siehe test_config.py).
TEST_CONFIG = REPO_ROOT / "tests" / "config.yaml"


@pytest.fixture(scope="session")
def config():
    return load_config(TEST_CONFIG, REPO_ROOT / "halls.yaml")


@pytest.fixture(scope="session")
def halls(config):
    return config.halls


def _vevents(filename):
    cal = ics_io.parse_calendar((FIXTURES_DIR / filename).read_bytes())
    return {str(v["UID"]): v for v in ics_io.iter_vevents(cal)}


@pytest.fixture(scope="session")
def spielerplus_m2():
    return _vevents("spielerplus-m2.ics")


@pytest.fixture(scope="session")
def spielerplus_m3():
    return _vevents("spielerplus-m3.ics")


@pytest.fixture(scope="session")
def handballnet_m2():
    return _vevents("handballnet-m2.ics")


@pytest.fixture(scope="session")
def handballnet_m3():
    return _vevents("handballnet-m3.ics")


@pytest.fixture(scope="session")
def handballnet_mc():
    return _vevents("handballnet-mc.ics")
