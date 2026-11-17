"""Per-language goldens: the same 35 inputs for all 26 languages.

These outputs were read and checked by hand, language by language, against the training text (see REPORT.md for
which words are verified, attested, digit fallback or unverified). They are a regression snapshot: a change here
must be a deliberate, reviewed change. Regenerate only after checking the new outputs.
"""
import json
from pathlib import Path

import pytest

from openarcane.text import normalize

GOLDENS = json.loads((Path(__file__).with_name("goldens.json")).read_text(encoding="utf-8"))
CASES = [(lang, text, out) for lang, rows in sorted(GOLDENS.items()) for text, out in rows.items()]


def test_all_languages_present():
    from openarcane.text.langs import LANGUAGE_MODULES
    assert set(GOLDENS) == set(LANGUAGE_MODULES) and len(GOLDENS) == 26


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_golden(lang, text, expected):
    assert normalize(text, lang) == expected


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_golden_idempotent(lang, text, expected):
    assert normalize(expected, lang) == expected
