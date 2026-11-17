"""Santali (Ol Chiki).

0-99 from data/indic_number_tables.json, every word attested in the Santali training text; where the text has
both a glued and a spaced spelling the glued one is used only if it occurs (ᱜᱮᱞᱢᱤᱛ = 11, ᱵᱟᱨᱜᱮᱞ ᱢᱤᱫ = 21).
Hundreds ᱢᱤᱫᱥᱟᱭ...ᱟᱨᱮᱥᱟᱭ, ᱦᱟᱡᱟᱨ, ᱞᱟᱠᱷ, ᱠᱳᱴᱤ are attested; numbers are built by juxtaposition in the Indian
system (2025 -> ᱵᱟᱨ ᱦᱟᱡᱟᱨ ᱵᱟᱨᱜᱮᱞ ᱢᱚᱲᱮ), which is attested only word by word, not as a whole phrase.
No same-script relative exists: a concept without a word drops that reading.
"""
from __future__ import annotations

from . import cldr_layer
from .indo_aryan import TABLES, IndoAryan

OLCK = "ᱚ-ᱽ"

SAT_LEX = {
    # month names as the training text spells them (CLDR's ᱟᱜᱟᱥᱛ, ᱥᱮᱯᱴᱮᱢᱵᱟᱨ ... never occur): ᱡᱟᱱᱩᱣᱟᱨᱤ 47,
    # ᱯᱷᱮᱵᱨᱩᱣᱟᱨᱤ 54, ᱢᱟᱨᱪ 108, ᱮᱯᱨᱤᱞ 99, ᱢᱮ, ᱡᱩᱱ 64, ᱡᱩᱞᱟᱭ 33, ᱟᱜᱚᱥᱴ 51, ᱥᱮᱯᱴᱮᱢᱵᱚᱨ 55, ᱚᱠᱴᱳᱵᱚᱨ 27,
    # ᱱᱚᱵᱷᱮᱢᱵᱚᱨ 52, ᱰᱤᱥᱮᱢᱵᱚᱨ 58
    "months": ["ᱡᱟᱱᱩᱣᱟᱨᱤ", "ᱯᱷᱮᱵᱨᱩᱣᱟᱨᱤ", "ᱢᱟᱨᱪ", "ᱮᱯᱨᱤᱞ", "ᱢᱮ", "ᱡᱩᱱ", "ᱡᱩᱞᱟᱭ", "ᱟᱜᱚᱥᱴ", "ᱥᱮᱯᱴᱮᱢᱵᱚᱨ", "ᱚᱠᱴᱳᱵᱚᱨ",
               "ᱱᱚᱵᱷᱮᱢᱵᱚᱨ", "ᱰᱤᱥᱮᱢᱵᱚᱨ"],
    "point": "ᱯᱚᱭᱮᱱᱴ", "and": "ᱟᱨ",
    # loans attested in the text (unverified): ᱯᱟᱨᱥᱮᱱᱴ 31, ᱯᱞᱟᱥ 28, ᱟᱫᱷᱟ (half) 187, ᱠᱤᱞᱚᱢᱤᱴᱟᱨ 13
    "percent": "{x} ᱯᱟᱨᱥᱮᱱᱴ", "percent_word": "ᱯᱟᱨᱥᱮᱱᱴ", "plus": "ᱯᱞᱟᱥ", "fractions_special": {(1, 2): "ᱟᱫᱷᱟ"},
    "u_km": "ᱠᱤᱞᱚᱢᱤᱴᱟᱨ", "range": "{a} ᱠᱷᱚᱱ {b} ᱦᱟᱹᱵᱤᱡ",
    "u_hr": "ᱜᱷᱚᱱᱴᱟ", "u_min": "ᱢᱤᱱᱤᱴ", "u_sec": "ᱥᱮᱠᱮᱱᱰ", "u_year": "ᱥᱮᱨᱢᱟ",
    "cur_INR": "ᱴᱟᱠᱟ", "cur_USD": "ᱰᱚᱞᱟᱨ",  # ᱢᱚᱲᱮ ᱰᱚᱞᱟᱨ in the text (ᱰᱚᱞᱟᱨ 31)
    "sub_INR": "ᱯᱚᱭᱥᱟ", "money": "{x} {cur}", "money_join": " ",
    "time_h": "{h}", "time_hm": "{h} {m}", "time_hms": "{h} {m} {s}",  # plain numbers: no clock word is attested
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "scale_thousand": "ᱦᱟᱡᱟᱨ", "scale_lakh": "ᱞᱟᱠᱷ", "scale_crore": "ᱠᱳᱴᱤ",
    "scale_native": {"ᱦᱟᱡᱟᱨ": 1, "ᱞᱟᱠᱷ": 1, "ᱠᱳᱴᱤ": 1},
}


def make(name="santali"):
    t = TABLES["own"]["santali"]
    lang = IndoAryan()
    lang.name, lang.code, lang.script = name, "sat", "Ol Chiki"
    lang.letters = OLCK + "‌‍"
    lang.fallback = ()
    lang.below100 = t["below100"]
    lang.hundreds = list(t["hundreds"])
    lang.thousand, lang.lakh, lang.crore = t["thousand"], t["lakh"], t["crore"]
    assert len(lang.below100) == 100 and all(lang.below100)
    lang.lex = {**cldr_layer("santali"), **SAT_LEX}
    # ᱯᱩᱭᱞᱩ 72, ᱫᱚᱥᱟᱨ 210, ᱛᱮᱥᱟᱨ 33 in the text; dosar/tesar are ordinal adjectives (Hansdah and Murmu dictionary)
    lang.ord_irreg = {1: "ᱯᱩᱭᱞᱩ", 2: "ᱫᱚᱥᱟᱨ", 3: "ᱛᱮᱥᱟᱨ"}
    return lang
