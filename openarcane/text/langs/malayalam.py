"""Malayalam. Numbers below 100 are single words as in CLDR RBNF ml (main @ 3d45043): ഇരുപത്തിയഞ്ച്.
Larger numbers keep CLDR's combining forms (നൂറ്റി, ആയിരത്തി, ലക്ഷത്തി) but put a space between scale groups
(ആയിരത്തി എണ്ണൂറ്റി അമ്പത്തിയേഴ്) instead of one long compound; both styles occur in the training text
(ആയിരത്തി alone: 352 hits). Spellings chosen by corpus frequency: അമ്പത് (55) over CLDR അൻപത് (4),
മൂവായിരം/അയ്യായിരം (CLDR's prefix rule would give മൂന്നായിരം/അഞ്ചായിരം, 0 hits). Crore recurses."""
from __future__ import annotations

from . import cldr_layer
from .base import Lang

UNITS = ["പൂജ്യം", "ഒന്ന്", "രണ്ട്", "മൂന്ന്", "നാല്", "അഞ്ച്", "ആറ്", "ഏഴ്", "എട്ട്", "ഒൻപത്"]
TEENS = ["പത്ത്", "പതിനൊന്ന്", "പന്ത്രണ്ട്", "പതിമൂന്ന്", "പതിനാല്", "പതിനഞ്ച്", "പതിനാറ്", "പതിനേഴ്",
         "പതിനെട്ട്", "പത്തൊൻപത്"]
TENS = ["", "", "ഇരുപത്", "മുപ്പത്", "നാൽപ്പത്", "അമ്പത്", "അറുപത്", "എഴുപത്", "എൺപത്", "തൊണ്ണൂറ്"]
# unit forms glued after the tens combining form ...ത്തി / ...റ്റി (CLDR %%spellout-prefix-compound + ്)
UNIT_COMPOUND = ["", "യൊന്ന്", "രണ്ട്", "മൂന്ന്", "നാല്", "യഞ്ച്", "യാറ്", "യേഴ്", "യെട്ട്", "യൊൻപത്"]
HUNDREDS = ["", "നൂറ്", "ഇരുനൂറ്", "മുന്നൂറ്", "നാന്നൂറ്", "അഞ്ഞൂറ്", "അറുനൂറ്", "എഴുന്നൂറ്", "എണ്ണൂറ്",
            "തൊള്ളായിരം"]
THOUSANDS = ["", "ആയിരം", "രണ്ടായിരം", "മൂവായിരം", "നാലായിരം", "അയ്യായിരം", "ആറായിരം", "ഏഴായിരം", "എട്ടായിരം",
             "ഒൻപതിനായിരം", "പതിനായിരം"]

VIRAMA = "്"
VOWEL_SIGNS = set("ാിീുൂൃെേൈൊോൌ")


def _comb(w: str) -> str:
    """ഇരുപത് -> ഇരുപത്തി, നൂറ് -> നൂറ്റി, ആയിരം -> ആയിരത്തി, കോടി -> കോടി."""
    if w.endswith("ത്"):
        return w + "തി"
    if w.endswith("റ്"):
        return w + "റി"
    if w.endswith("ം"):
        return w[:-1] + "ത്തി"
    return w


def below100(n: int) -> str:
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEENS[n - 10]
    t, o = divmod(n, 10)
    return TENS[t] if not o else _comb(TENS[t]) + UNIT_COMPOUND[o]


def _thousand_compound(w: str) -> str:
    """11..99 + ആയിരം as one word: ഇരുപത് -> ഇരുപതിനായിരം, പന്ത്രണ്ട് -> പന്ത്രണ്ടായിരം,
    മുപ്പത്തിനാല് -> മുപ്പത്തിനാലായിരം. REVIEW_NEEDED for the forms not seen in the training text."""
    if w.endswith("ത്"):
        return w[:-1] + "ിനായിരം"
    if w.endswith("്"):
        return w[:-1] + "ായിരം"
    return f"{w} ആയിരം"


class Malayalam(Lang):
    name, code, script = "malayalam", "ml", "Malayalam"
    letters = "ഀ-ൿ‌‍"
    glue_unknown_suffix = True
    detached_suffixes = ("ആം",)

    def adj(self, words: str) -> str:
        return words[: -len("ഒന്ന്")] + "ഒരു" if words == "ഒന്ന്" else words

    def cardinal(self, n: int) -> str:  # noqa: C901
        if n < 100:
            return below100(n)
        parts = []
        cr, rest = divmod(n, 10**7)
        if cr:
            w = "ഒരു കോടി" if cr == 1 else f"{self.cardinal(cr)} കോടി"
            parts.append((w, w))
        lk, rest = divmod(rest, 10**5)
        if lk:
            w = "ഒരു ലക്ഷം" if lk == 1 else f"{below100(lk)} ലക്ഷം"
            parts.append((w, _comb(w)))
        th, rest = divmod(rest, 1000)
        if th:
            if th <= 10:
                w = THOUSANDS[th]
            else:
                w = _thousand_compound(below100(th))  # ഇരുപതിനായിരം (16 hits, spaced form 0), പന്ത്രണ്ടായിരം (3)
            parts.append((w, _comb(w)))
        h, rest = divmod(rest, 100)
        if h:
            parts.append((HUNDREDS[h], _comb(HUNDREDS[h])))
        if rest:
            parts.append((below100(rest), below100(rest)))
        return " ".join([c for _, c in parts[:-1]] + [parts[-1][0]])

    def digit(self, d: int) -> str:
        return UNITS[d]

    def attach(self, words: str, suffix: str, n: int | None = None) -> str:
        if suffix in ("ആം", "-ാം", "ാമത്തെ", "ആമത്തെ", "-ആം"):
            suffix = "ാം" if "ത്തെ" not in suffix else "ാമത്തെ"
        if suffix in ("ൽ", "ന്", "ന്റെ", "നു", "ക്ക്") and "ക" <= words[-1:] <= "ഹ":
            # a noun ending in an inherent a (രൂപ): രൂപയ്ക്ക്, രൂപയിൽ, രൂപയുടെ
            return words + {"ൽ": "യിൽ", "ന്": "യ്ക്ക്", "ന്റെ": "യുടെ", "നു": "യ്ക്ക്", "ക്ക്": "യ്ക്ക്"}[suffix]
        if suffix == "ക്ക്" and words[-1:] in VOWEL_SIGNS and words[-1:] != "ാ":
            return words + suffix  # a noun ending in -i or -u takes ക്ക് as written: മണിക്ക് (41 in the text), കോടിക്ക്
        if suffix in ("ൽ", "ന്", "ന്റെ", "നു", "ക്ക്"):  # case endings written straight after the digits
            suffix = {"ൽ": "ിൽ", "ന്": "ിന്", "ന്റെ": "ിന്റെ", "നു": "ിന്", "ക്ക്": "ിന്"}[suffix]
        if words.endswith("ം") and suffix.startswith("ത്ത"):  # ശതമാനം + ത്തിന് -> ശതമാനത്തിന്
            return words[:-1] + suffix
        if suffix[:1] in VOWEL_SIGNS:
            if words.endswith("ാം") and suffix != "ാം":  # കിലോഗ്രാം + ിന് -> കിലോഗ്രാമിന് (loan noun)
                return words[:-1] + "മ" + suffix
            if words.endswith(VIRAMA):  # രണ്ട് + ിൽ -> രണ്ടിൽ ; മൂന്ന് + ാം -> മൂന്നാം
                return words[:-1] + suffix
            if words.endswith("ം"):  # ആയിരം + ിൽ -> ആയിരത്തിൽ ; ആയിരം + ാം -> ആയിരാം
                return words[:-1] + ("ത്ത" if suffix != "ാം" else "") + suffix
            if words[-1:] in VOWEL_SIGNS:  # കോടി + ിൽ -> കോടിയിൽ
                return words + "യ" + suffix
            return words + suffix
        return words + suffix

    def ordinal(self, n: int) -> str:
        return "ഒന്നാം" if n == 1 else self.attach(self.say_int(n), "ാം")

    def mixed_fraction(self, whole, a, b):
        w = self.say_int(whole)
        if (a, b) == (1, 2) and w.endswith(VIRAMA):
            return w[:-1] + "ര"  # രണ്ടര, ഒന്നര
        if (a, b) == (1, 4) and w.endswith(VIRAMA):
            return w[:-1] + "േകാൽ"  # രണ്ടേകാൽ (Malayalam: A University Course, lesson 17)
        return None


MALAYALAM_LEX = {
    "point": "ദശാംശം", "minus": "മൈനസ്", "plus": "പ്ലസ്", "times": "ഗുണം", "divide": "ഹരണം", "equals": "സമം",
    "neq": "സമമല്ല", "lt": "ലെസ് ദാൻ", "gt": "ഗ്രേറ്റർ ദാൻ", "le": "ലെസ് ദാൻ ഓർ ഈക്വൽ ടു",
    "ge": "ഗ്രേറ്റർ ദാൻ ഓർ ഈക്വൽ ടു", "pm": "പ്ലസ് മൈനസ്", "approx": "ഏകദേശം", "squared": "സ്ക്വയർ",
    "cubed": "ക്യൂബ്", "power": "പവർ {n}", "root": "റൂട്ട്", "cuberoot": "ക്യൂബ് റൂട്ട്", "fourthroot": "ഫോർത്ത് റൂട്ട്",
    "fraction": "{b+ിൽ} {a}", "mixed_fraction": "{x} പൂർണ്ണം {f}",
    "fractions_special": {(1, 2): "അര", (1, 4): "കാൽ", (3, 4): "മുക്കാൽ"},
    "per": "{u} പെർ {p}", "percent": "{x} ശതമാനം", "percent_word": "ശതമാനം", "range": "{a} മുതൽ {b} വരെ", "ratio": "{a} അനുപാതം {b}",
    "dot": "ഡോട്ട്", "slash": "സ്ലാഷ്", "at": "അറ്റ്", "hyphen": "ഹൈഫൻ", "underscore": "അണ്ടർസ്കോർ", "colon": "കോളൻ",
    "question": "ചോദ്യചിഹ്നം", "hash": "ഹാഷ്", "tilde": "ടിൽഡ്", "semicolon": "സെമികോളൻ", "comma": "കോമ", "exclamation": "ആശ്ചര്യചിഹ്നം",
    "permille": "ആയിരത്തിൽ {x}", "dp_evening_until": 7, "ratio_cue": "അനുപാതം", "date_labels": "തീയതി",
    "phone_keywords": ["ഫോൺ നമ്പർ", "ഫോൺ", "മൊബൈൽ നമ്പർ", "മൊബൈൽ", "ഹെൽപ്‌ലൈൻ"], "and": "ഒപ്പം", "number_word": "നമ്പർ",
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} മണി", "time_hm": "{h} മണി {m} മിനിറ്റ്", "time_hms": "{h} മണി {m} മിനിറ്റ് {s} സെക്കൻഡ്",
    "time_ap": "{dp} {t}", "time_absorb": ("മണി",), "dp_morning": "രാവിലെ", "dp_noon": "ഉച്ചയ്ക്ക്",
    "dp_evening": "വൈകുന്നേരം", "dp_night": "രാത്രി",
    "money": "{x} {cur}", "money_join": " ",
    "cur_INR": "രൂപ", "sub_INR": "പൈസ", "cur_USD": "ഡോളർ", "sub_USD": "സെന്റ്", "cur_EUR": "യൂറോ",
    "sub_EUR": "സെന്റ്", "cur_GBP": "പൗണ്ട്", "sub_GBP": "പെൻസ്",
    "scale_thousand": "ആയിരം", "scale_lakh": "ലക്ഷം", "scale_crore": "കോടി", "scale_million": "മില്യൺ",
    "scale_billion": "ബില്യൺ", "scale_trillion": "ട്രില്യൺ",
    "scale_native": {"ആയിരം": 1, "ലക്ഷം": 1, "കോടി": 1},
    "currency_native": {"രൂ.": "INR", "രൂ": "INR"},
    "code_connectors": ["നമ്പർ"],
    "code_keywords": ["ഒടിപി", "ഒ.ടി.പി", "പിൻ കോഡ്", "പിൻകോഡ്", "പിൻ", "അക്കൗണ്ട് നമ്പർ", "ആധാർ നമ്പർ", "കോഡ്"],
    "unit_abbr": {"കി.മീ.": "km", "കി.മീ": "km", "കിമീ": "km", "കി.ഗ്രാം": "kg", "കിലോ": "kg", "ഗ്രാം": "g",
                  "സെ.മീ.": "cm", "മി.മീ.": "mm", "മീ.": "m", "ലി.": "l"},
    "abbr_native": {"ഡോ.": "ഡോക്ടർ", "കി.മീ.": "കിലോമീറ്റർ"},
    "abbr_dr": "ഡോക്ടർ", "abbr_mr": "മിസ്റ്റർ", "abbr_mrs": "മിസിസ്", "abbr_ms": "മിസ്", "abbr_prof": "പ്രൊഫസർ",
    "abbr_etc": "തുടങ്ങിയവ", "abbr_vs": "വേഴ്സസ്", "abbr_govt": "സർക്കാർ", "abbr_approx": "ഏകദേശം",
    "abbr_eg": "ഉദാഹരണത്തിന്", "abbr_ie": "അതായത്", "abbr_jr": "ജൂനിയർ", "abbr_sr": "സീനിയർ", "abbr_ltd": "ലിമിറ്റഡ്",
    "abbr_pvt": "പ്രൈവറ്റ്", "abbr_dept": "വകുപ്പ്",
    "u_hr": "മണിക്കൂർ", "u_min": "മിനിറ്റ്", "u_sec": "സെക്കൻഡ്", "u_year": "വർഷം", "u_kmph": "മണിക്കൂറിൽ {x} കിലോമീറ്റർ",
    "u_quintal": "ക്വിന്റൽ", "u_kmpl": "കിലോമീറ്റർ പെർ ലിറ്റർ", "u_bhp": "ബിഎച്ച്പി", "u_rpm": "ആർപിഎം",
    "u_dB": "ഡെസിബൽ", "u_kl": "കിലോലിറ്റർ", "u_cc": "സിസി", "u_Wh": "വാട്ട് മണിക്കൂർ", "u_kV": "കിലോവോൾട്ട്",
    "u_mAh": "മില്ലിആമ്പിയർ മണിക്കൂർ",
}


def make(name="malayalam"):
    lang = Malayalam()
    lang.lex = {**cldr_layer("malayalam"), **MALAYALAM_LEX}
    return lang
