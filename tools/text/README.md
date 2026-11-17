# Developer tools

These scripts were used to build and check the normaliser's word data. The package never imports them, and
you don't need them to use or test it.

| Tool | What it does | Needs |
|---|---|---|
| `extract_cldr_numbers.py` | Writes `openarcane/text/data/cldr_numbers.json` from CLDR number rules | PyICU and a CLDR checkout (`common/rbnf`) |
| `extract_cldr_lexicon.py` | Writes `openarcane/text/data/cldr_lexicon.json` (month and unit names) | PyICU built against ICU 78 or newer |
| `cldr_check.py` | Compares the normaliser's cardinals and ordinals with CLDR | PyICU and a CLDR checkout |
| `corpus_check.py` | Checks that output words occur in each language's Volt-TTS training text | The training text, which is not public |

Each script's docstring shows how to run it.
