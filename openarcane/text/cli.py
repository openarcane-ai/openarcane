"""CLI: python -m openarcane.text -l kannada "text"   (or pipe text on stdin)."""
from __future__ import annotations

import argparse
import sys

from . import LANGUAGES, normalize
from .langs import resolve


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m openarcane.text",
                                 description="Normalise written text into speakable text.")
    ap.add_argument("-l", "--language", required=True, help="TTS language name or ISO code: " + ", ".join(LANGUAGES))
    ap.add_argument("--show", action="store_true", help="print input and output side by side")
    ap.add_argument("text", nargs="*", help="text to normalise; read from stdin when omitted")
    a = ap.parse_args(argv)
    try:
        resolve(a.language)
    except ValueError as e:
        ap.error(str(e))
    lines = [" ".join(a.text)] if a.text else sys.stdin.read().splitlines()
    for line in lines:
        out = normalize(line, a.language)
        print(f"{line}\n  -> {out}" if a.show else out)


if __name__ == "__main__":
    main()
