"""The 36 rows of NATIVE_REVIEW_kn_hi.md, approved as written by a native Kannada and Hindi speaker on 2026-11-15.
A fix must never change them; read from the sheet so the test and the sheet cannot drift apart."""
from pathlib import Path

import pytest

from openarcane.text import normalize

SHEET = Path(__file__).resolve().parents[2] / "docs" / "text" / "NATIVE_REVIEW_kn_hi.md"


def _rows():
    lang, rows = None, []
    for line in SHEET.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Kannada"):
            lang = "kannada"
        elif line.startswith("## Hindi"):
            lang = "hindi"
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if lang and len(cells) == 5 and cells[0].isdigit():
            rows.append((lang, cells[2], cells[3]))
    return rows


ROWS = _rows()


def test_sheet_has_36_rows():
    assert len(ROWS) == 36


@pytest.mark.parametrize("lang,text,approved", ROWS)
def test_native_approved(lang, text, approved):
    assert normalize(text, lang) == approved
