"""Digit folding and small numeric helpers (standard library only)."""
from __future__ import annotations

# Zero code point of every decimal-digit block we accept as input.
DIGIT_ZEROS = {
    "ascii": 0x0030,
    "arabic_indic": 0x0660,
    "ext_arabic_indic": 0x06F0,
    "nko": 0x07C0,
    "devanagari": 0x0966,
    "bengali": 0x09E6,
    "gurmukhi": 0x0A66,
    "gujarati": 0x0AE6,
    "odia": 0x0B66,
    "tamil": 0x0BE6,
    "telugu": 0x0C66,
    "kannada": 0x0CE6,
    "malayalam": 0x0D66,
    "sinhala_lith": 0x0DE6,
    "thai": 0x0E50,
    "lao": 0x0ED0,
    "tibetan": 0x0F20,
    "myanmar": 0x1040,
    "limbu": 0x1946,
    "ol_chiki": 0x1C50,
    "meetei_mayek": 0xABF0,
    "fullwidth": 0xFF10,
}

_FOLD = {}
for _z in DIGIT_ZEROS.values():
    if _z != 0x30:
        for _i in range(10):
            _FOLD[_z + _i] = 0x30 + _i
# Arabic decimal and thousands separators fold to ASCII '.' and ','.
_FOLD[0x066B] = ord(".")
_FOLD[0x066C] = ord(",")
# Unicode minus, fullwidth plus/minus etc. are kept as is (handled by the engine).


def fold_digits(text: str) -> str:
    """Map every native decimal digit to ASCII, 1:1 (offsets are preserved)."""
    return text.translate(_FOLD)


def native_digits(script_zero: int, s: str) -> str:
    return "".join(chr(script_zero + int(c)) if c.isdigit() else c for c in s)


def group_digits(digits: str) -> list[str]:
    """Natural grouping for a code read digit by digit when no grouping was written."""
    n = len(digits)
    if n <= 5:
        return [digits]
    if n == 6:
        return [digits[:3], digits[3:]]
    if n == 7:
        return [digits[:3], digits[3:]]
    if n == 10:
        return [digits[:5], digits[5:]]
    groups = [digits[i:i + 4] for i in range(0, n, 4)]
    if len(groups[-1]) == 1 and len(groups) > 1:  # avoid a lone trailing digit
        groups[-2:] = [groups[-2][:3], groups[-2][3:] + groups[-1]]
    return groups


def split_groups(raw: str) -> list[str]:
    """Split a written digit string on spaces / hyphens / dots into its groups."""
    out, cur = [], []
    for ch in raw:
        if ch.isdigit():
            cur.append(ch)
        elif cur:
            out.append("".join(cur))
            cur = []
    if cur:
        out.append("".join(cur))
    return out
