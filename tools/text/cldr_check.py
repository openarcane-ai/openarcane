"""DEV TOOL (not imported by the package). Diff our cardinals/ordinals against Unicode CLDR RBNF.

Needs PyICU and a checkout of CLDR's common/rbnf/*.xml (main @ 3d45043, 2026-05-08):
  <python-with-pyicu> -I tools/text/cldr_check.py --rbnf <dir-with-xml> kannada hindi ...
Numbers above 99 crore are skipped (CLDR uses arab/kharab; we recurse crore by design).
"""
import argparse
import os
import random
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))  # repository root
import icu  # noqa: E402

from openarcane.text import langs  # noqa: E402

LOCALE = {"kannada": "kn", "hindi": "hi", "telugu": "te", "tamil": "ta", "malayalam": "ml", "marathi": "mr",
          "bengali": "bn", "gujarati": "gu", "odia": "or", "punjabi": "pa", "nepali": "ne", "urdu": "ur",
          "english": "en_IN", "assamese": "as"}


def formatter(rbnf_dir, loc):
    x = open(os.path.join(rbnf_dir, f"{loc.split('_')[0]}.xml"), encoding="utf-8").read()
    m = re.search(r'type="SpelloutRules">\s*<rbnfRules><!\[CDATA\[(.*?)\]\]>', x, re.S)
    return icu.RuleBasedNumberFormat(m.group(1), icu.Locale(loc.replace("_", "-")))


def samples(seed=0):
    rnd = random.Random(seed)
    ns = list(range(0, 1001)) + [1857, 1998, 2000, 2025, 10**5, 10**5 + 1, 10**7, 10**7 + 1, 123456, 4500000]
    for e in range(4, 10):
        ns += [rnd.randrange(10**(e - 1), 10**e) for _ in range(60)]
    return sorted(set(n for n in ns if n < 10**9))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rbnf", required=True)
    ap.add_argument("--show", type=int, default=15)
    ap.add_argument("languages", nargs="+")
    a = ap.parse_args()
    for name in a.languages:
        L = langs.get(name)
        f = formatter(a.rbnf, LOCALE[name])
        f.setDefaultRuleSet("%spellout-cardinal")
        ns = samples()
        bad = []
        for n in ns:
            ours = L.cardinal(n)
            ref = f.format(n).replace(" ", " ")
            if ours != ref:
                bad.append((n, ref, ours))
        print(f"## {name}: {len(ns) - len(bad)}/{len(ns)} cardinals match CLDR")
        for n, ref, ours in bad[: a.show]:
            print(f"  {n}: CLDR={ref} | ours={ours}")


if __name__ == "__main__":
    main()
