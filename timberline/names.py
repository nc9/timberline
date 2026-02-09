from __future__ import annotations

import random

from timberline.types import NamingScheme, TimberlineError

MINERALS = [
    "obsidian",
    "quartz",
    "jasper",
    "topaz",
    "onyx",
    "opal",
    "amber",
    "cobalt",
    "flint",
    "slate",
    "basalt",
    "granite",
    "pyrite",
    "agate",
    "beryl",
    "garnet",
    "jade",
    "lapis",
    "mica",
    "ruby",
    "zinc",
    "iron",
    "copper",
    "nickel",
    "chrome",
    "titan",
    "bronze",
    "carbon",
    "marble",
    "pumice",
    "shale",
    "gneiss",
    "schist",
    "galena",
    "zircon",
    "spinel",
    "peridot",
    "feldspar",
    "calcite",
    "dolomite",
    "magnetite",
    "hematite",
    "malachite",
    "turquoise",
    "fluorite",
    "celestite",
    "rhodonite",
    "kyanite",
    "bismuth",
    "tungsten",
]

CITIES = [
    "osaka",
    "porto",
    "bruges",
    "kyoto",
    "zurich",
    "cusco",
    "fez",
    "lagos",
    "busan",
    "bergen",
    "tallinn",
    "dubrovnik",
    "granada",
    "hanoi",
    "cartagena",
    "halifax",
    "darwin",
    "hobart",
    "galway",
    "sintra",
    "lucerne",
    "salzburg",
    "seville",
    "valencia",
    "ghent",
    "utrecht",
    "krakow",
    "gdansk",
    "split",
    "kotor",
    "plovdiv",
    "tbilisi",
    "yerevan",
    "muscat",
    "doha",
    "lima",
    "quito",
    "bogota",
    "havana",
    "nassau",
    "kingston",
    "suva",
    "apia",
    "nara",
    "malmo",
    "turku",
    "bath",
]

ADJECTIVES = [
    "swift",
    "bold",
    "keen",
    "wild",
    "calm",
    "dark",
    "bright",
    "sharp",
    "deep",
    "warm",
    "cold",
    "raw",
    "red",
    "pale",
    "rich",
    "prime",
    "rare",
    "pure",
    "clear",
    "stark",
    "vast",
    "twin",
    "lone",
    "true",
    "wry",
]


def _getPool(scheme: NamingScheme) -> list[str]:
    match scheme:
        case NamingScheme.MINERALS:
            return list(MINERALS)
        case NamingScheme.CITIES:
            return list(CITIES)
        case NamingScheme.COMPOUND:
            return [f"{adj}-{noun}" for adj in ADJECTIVES for noun in MINERALS]


def generateName(scheme: NamingScheme, existing: set[str]) -> str:
    pool = _getPool(scheme)
    random.shuffle(pool)

    for name in pool:
        if name not in existing:
            return name

    # fallback: append incrementing number
    base_pool = _getPool(scheme)
    random.shuffle(base_pool)
    base = base_pool[0]
    for i in range(2, 100):
        candidate = f"{base}-{i}"
        if candidate not in existing:
            return candidate

    raise TimberlineError("Could not generate unique name — clean up old worktrees!")
