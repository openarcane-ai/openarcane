"""Public API: normalize(text, language) -> str. Deterministic, standard library only, no network."""
from __future__ import annotations

import bisect
import logging
import os
import re
import unicodedata

from . import langs
from .engine import Engine

LANGUAGES = tuple(langs.LANGUAGE_MODULES)
ALIASES = dict(langs.ALIASES)
_ENGINES: dict[str, Engine] = {}
_log = logging.getLogger("openarcane.text")
# Safety net: if the engine fails on some input, normalize() logs it and returns the text unchanged, so one odd
# input never fails a TTS request. Tests set OPENARCANE_TEXT_STRICT=1 (tests/conftest.py) so errors still raise.
STRICT = os.environ.get("OPENARCANE_TEXT_STRICT") == "1"


def get_engine(language: str) -> Engine:
    name = langs.resolve(language)
    eng = _ENGINES.get(name)
    if eng is None:
        eng = _ENGINES[name] = Engine(langs.get(name))
    return eng


def normalize(text: str, language: str, strict: bool | None = None) -> str:
    """Rewrite numbers, money, dates, times, codes, units, maths, URLs and abbreviations in `text` as words
    of `language`. Everything else (markdown, spacing, line breaks, other words) is copied unchanged.
    An unknown language or a non-string argument raises. Any other error returns `text` unchanged and logs it, unless `strict`
    (default: env OPENARCANE_TEXT_STRICT=1) re-raises it."""
    if not isinstance(text, str):
        raise TypeError(f"text must be a string, got {type(text).__name__}")
    if not isinstance(language, str):
        raise TypeError(f"language must be a string, got {type(language).__name__}")
    if not text:
        return text
    get_engine(language)  # unknown language is a caller error: always raise
    try:
        return _normalize(text, language)
    except Exception:
        if STRICT if strict is None else strict:
            raise
        _log.exception("openarcane.text normalize failed; returning text unchanged (language=%s, %d chars)", language, len(text))
        return text


def _normalize(text: str, language: str) -> str:
    if unicodedata.is_normalized("NFC", text):
        return get_engine(language).run(text)
    # Matching needs NFC, but text that is not rewritten must come back byte for byte. NFC never joins across
    # whitespace, so the NFC text is the NFC of each whitespace-separated piece; the engine copies each untouched
    # piece from the original. A piece the engine rewrites or cuts into comes out in NFC.
    segs = re.split(r"(\s+)", text)
    nfc, spans, pos = [], [], 0
    for seg in segs:
        ns = unicodedata.normalize("NFC", seg)
        spans.append((pos, pos + len(ns), seg))
        nfc.append(ns)
        pos += len(ns)
    nfc_text = "".join(nfc)
    starts = [s for s, _, _ in spans]

    def copy(a: int, b: int) -> str:
        res = []
        k = max(0, bisect.bisect_right(starts, a) - 1)
        while k < len(spans) and spans[k][0] < b:
            s, e, orig = spans[k]
            lo, hi = max(a, s), min(b, e)
            if lo < hi:
                res.append(orig if (lo, hi) == (s, e) else nfc_text[lo:hi])
            k += 1
        return "".join(res)

    return get_engine(language).run(nfc_text, copy)
