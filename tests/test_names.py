from __future__ import annotations

from timberline.models import NamingScheme
from timberline.names import ADJECTIVES, CITIES, MINERALS, generateName


def test_generateName_minerals():
    name = generateName(NamingScheme.MINERALS, set())
    assert name in MINERALS


def test_generateName_cities():
    name = generateName(NamingScheme.CITIES, set())
    assert name in CITIES


def test_generateName_compound():
    name = generateName(NamingScheme.COMPOUND, set())
    parts = name.split("-")
    assert len(parts) == 2
    assert parts[0] in ADJECTIVES
    assert parts[1] in MINERALS


def test_generateName_avoids_existing():
    existing = set(MINERALS[:-1])  # all but one
    name = generateName(NamingScheme.MINERALS, existing)
    assert name not in existing


def test_generateName_fallback_numbering():
    existing = set(MINERALS)  # exhaust all
    name = generateName(NamingScheme.MINERALS, existing)
    assert "-" in name
    base, num = name.rsplit("-", 1)
    assert num.isdigit()
    assert int(num) >= 2
