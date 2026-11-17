"""DEV TOOL (not imported by the package). Extract number-word tables from Unicode CLDR RBNF
(common/rbnf/*.xml, main @ 3d45043) for the table-driven languages. Writes openarcane/text/data/cldr_numbers.json:
  {language: {"below100": [100 words], "hundreds": [[standalone, combining] x 10], "thousand": ..., ...}}
Combining forms are read off CLDR by formatting X and X+1 and stripping the trailing "one".

Usage: <python-with-pyicu> -I tools/text/extract_cldr_numbers.py --rbnf <dir>
"""
import argparse
import json
import os
import re

import icu

LOCALES = {"marathi": "mr", "bengali": "bn", "gujarati": "gu", "punjabi": "pa", "odia": "or", "nepali": "ne",
           "urdu": "ur", "hindi": "hi"}


def fmt_factory(rbnf, loc):
    x = open(os.path.join(rbnf, f"{loc}.xml"), encoding="utf-8").read()
    m = re.search(r'type="SpelloutRules">\s*<rbnfRules><!\[CDATA\[(.*?)\]\]>', x, re.S)
    f = icu.RuleBasedNumberFormat(m.group(1), icu.Locale(loc))
    f.setDefaultRuleSet("%spellout-cardinal")
    return lambda n: f.format(n).replace(" ", " ")


def pair(F, n):
    """(standalone, combining) for round number n: combining = F(n+1) minus the trailing F(1)."""
    one = F(1)
    nxt = F(n + 1)
    comb = nxt[: -len(one)].rstrip() if nxt.endswith(one) else None
    return [F(n), comb]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rbnf", required=True)
    a = ap.parse_args()
    out = {"_meta": {"source": "Unicode CLDR RBNF, common/rbnf @ 3d45043 (2026-05-08), %spellout-cardinal",
                     "license": "Unicode License v3 (https://www.unicode.org/license.txt)"}}
    for lang, loc in LOCALES.items():
        F = fmt_factory(a.rbnf, loc)
        d = {"locale": loc, "below100": [F(n) for n in range(100)],
             "hundreds": [None] + [pair(F, h * 100) for h in range(1, 10)],
             "thousand_1": pair(F, 1000), "thousand_2": pair(F, 2000),
             "lakh_1": pair(F, 10**5), "lakh_2": pair(F, 2 * 10**5),
             "crore_1": pair(F, 10**7), "crore_2": pair(F, 2 * 10**7)}
        out[lang] = d
        print(lang, d["hundreds"][1], d["thousand_1"], d["thousand_2"], d["lakh_1"], d["lakh_2"], d["crore_2"])
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "openarcane", "text", "data", "cldr_numbers.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
