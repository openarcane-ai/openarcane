"""DEV TOOL (not imported by the package). Check that our number/lexicon words are attested in the TTS training
text of each language, and pick between spelling variants by frequency. It needs the Volt-TTS training text, which is not
public; using the package does not need this tool.

  uv run --no-project --with pyarrow python tools/text/corpus_check.py --rows <full_rows.parquet> build
  uv run --no-project --with pyarrow python tools/text/corpus_check.py words hindi पंद्रह पन्द्रह
  uv run --no-project --with pyarrow python tools/text/corpus_check.py audit hindi     # every word we can emit

`build` writes a word-frequency cache (one JSON per language) next to the parquet under ./corpus_counts/
or --cache. Only word counts are stored, never sentences.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))  # repository root

WORD = re.compile(r"[^\W\d_][\ẁ-ًͯ-ٰٟۖ-ۭऀ-෿᱐-᱿ꯀ-꯿‌‍]*")
DEFAULT_CACHE = os.path.join(os.environ.get("TMPDIR", "/tmp"), "openarcane_text_corpus_counts")


def build(rows, cache):
    import pyarrow.parquet as pq
    os.makedirs(cache, exist_ok=True)
    counts: dict[str, Counter] = {}
    pf = pq.ParquetFile(rows)
    for batch in pf.iter_batches(columns=["language", "text"], batch_size=50000):
        d = batch.to_pydict()
        for lang, text in zip(d["language"], d["text"]):
            counts.setdefault(lang, Counter()).update(WORD.findall(text or ""))
    for lang, c in counts.items():
        with open(os.path.join(cache, f"{lang}.json"), "w", encoding="utf-8") as fh:
            json.dump(dict(c), fh, ensure_ascii=False)
        print(lang, sum(c.values()), "tokens", len(c), "types")


def load(cache, lang):
    with open(os.path.join(cache, f"{lang}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def emitted_words(name):
    """Every word the normaliser can produce for `name` (numbers 0-999 + scales + lexicon strings)."""
    from openarcane.text import langs
    L = langs.get(name)
    out = Counter()
    for n in list(range(0, 1000)) + [1000, 2000, 10**5, 2 * 10**5, 10**7, 2 * 10**7]:
        out.update(L.cardinal(n).split())
    for k, v in L.lex.items():
        vals = v if isinstance(v, (list, tuple)) else (v.values() if isinstance(v, dict) and k.startswith("abbr_n")
                                                         else [v] if isinstance(v, str) else [])
        for s in vals:
            if isinstance(s, str):
                out.update(w for w in WORD.findall(re.sub(r"\{[^}]*\}", " ", s)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--rows")
    ap.add_argument("cmd", choices=["build", "words", "audit"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.rows, a.cache)
        return
    lang, words = a.args[0], a.args[1:]
    c = load(a.cache, lang)
    if a.cmd == "words":
        for w in words:
            print(f"{c.get(w, 0):>8}  {w}")
        return
    ew = emitted_words(lang)
    missing = sorted((w for w in ew if c.get(w, 0) == 0), key=lambda w: -ew[w])
    rare = sorted((w for w in ew if 0 < c.get(w, 0) < 5))
    print(f"## {lang}: {len(ew)} distinct emitted words; {len(missing)} unattested; {len(rare)} with <5 hits")
    print("unattested:", " ".join(missing[:200]))
    print("rare:", " ".join(f"{w}({c[w]})" for w in rare[:100]))


if __name__ == "__main__":
    main()
