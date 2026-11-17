"""Kannada. Number composition follows CLDR RBNF kn (main @ 3d45043) except above 99 crore, where crore
recurses (ನೂರು ಕೋಟಿ) instead of using ಅರಬ್/ಖರಬ್."""
from __future__ import annotations

from . import cldr_layer
from .base import Lang

UNITS = ["ಸೊನ್ನೆ", "ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ಐದು", "ಆರು", "ಏಳು", "ಎಂಟು", "ಒಂಬತ್ತು"]
TEENS = ["ಹತ್ತು", "ಹನ್ನೊಂದು", "ಹನ್ನೆರಡು", "ಹದಿಮೂರು", "ಹದಿನಾಲ್ಕು", "ಹದಿನೈದು", "ಹದಿನಾರು", "ಹದಿನೇಳು", "ಹದಿನೆಂಟು",
         "ಹತ್ತೊಂಬತ್ತು"]
TENS_STEM = ["", "", "ಇಪ್ಪತ್ತ", "ಮೂವತ್ತ", "ನಲವತ್ತ", "ಐವತ್ತ", "ಅರವತ್ತ", "ಎಪ್ಪತ್ತ", "ಎಂಬತ್ತ", "ತೊಂಬತ್ತ"]
UNIT_SUFFIX = ["", "ೊಂದು", "ೆರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ೈದು", "ಾರು", "ೇಳು", "ೆಂಟು", "ೊಂಬತ್ತು"]
HUNDREDS = ["", "ನೂರು", "ಇನ್ನೂರು", "ಮುನ್ನೂರು", "ನಾನೂರು", "ಐನೂರು", "ಆರುನೂರು", "ಏಳುನೂರು", "ಎಂಟುನೂರು", "ಒಂಬೈನೂರು"]

U, VIRAMA, ZWNJ = "ು", "್", "‌"
I_E_ENDINGS = ("ಿ", "ೆ", "ೇ", "ೈ", "ಇ", "ಎ", "ಏ", "ಐ")  # ಿ ೆ ೇ ೈ + independents


def below100(n: int) -> str:
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEENS[n - 10]
    t, o = divmod(n, 10)
    if o in (3, 4):  # corpus: ಇಪ್ಪತ್ಮೂರು 22 / ಇಪ್ಪತ್ತಮೂರು 2, ಇಪ್ಪತ್ನಾಲ್ಕು 30 / ಇಪ್ಪತ್ತನಾಲ್ಕು 1 (CLDR has the latter)
        return TENS_STEM[t][:-1] + UNITS[o]
    return TENS_STEM[t] + (UNIT_SUFFIX[o] if o else U)


class Kannada(Lang):
    name, code, script = "kannada", "kn", "Kannada"
    letters = "ಀ-೿‌‍"
    detached_suffixes = ("ರ", "ರಲ್ಲಿ", "ರಂದು", "ರಿಂದ", "ರವರೆಗೆ", "ರ ವರೆಗೆ", "ನೇ", "ನೆಯ", "ಕ್ಕೆ", "ರಷ್ಟು", "ರಂತೆ",
                         "ರೊಳಗೆ", "ರಲ್ಲೂ", "ಕ್ಕೂ")
    glue_unknown_suffix = True

    # ---------------------------------------------------------------- cardinals
    def cardinal(self, n: int) -> str:
        if n < 100:
            return below100(n)
        parts = []  # (full form, combining form used when something follows)
        cr, rest = divmod(n, 10**7)
        if cr:
            w = "ಒಂದು ಕೋಟಿ" if cr == 1 else f"{self.cardinal(cr)} ಕೋಟಿ"
            parts.append((w, w + "ಯ"))
        lk, rest = divmod(rest, 10**5)
        if lk:
            w = f"{below100(lk)} ಲಕ್ಷ"
            parts.append((w, w + "ದ"))
        th, rest = divmod(rest, 1000)
        if th:
            w = "ಸಾವಿರ" if th == 1 else f"{below100(th)} ಸಾವಿರ"
            parts.append((w, w + "ದ"))
        h, rest = divmod(rest, 100)
        if h:
            parts.append((HUNDREDS[h], HUNDREDS[h][:-1]))
        if rest:
            parts.append((below100(rest), below100(rest)))
        return " ".join([c for _, c in parts[:-1]] + [parts[-1][0]])

    def digit(self, d: int) -> str:
        return UNITS[d]

    # ---------------------------------------------------------------- suffix sandhi
    def attach(self, words: str, suffix: str, n: int | None = None) -> str:
        if not suffix:
            return words
        if suffix.startswith(" "):
            return words + suffix
        last = words[-1]
        if last == U:  # ಎಂಟು + ರಲ್ಲಿ -> ಎಂಟರಲ್ಲಿ ; ಮೂರು + ನೇ -> ಮೂರನೇ
            stem = words[:-1]
            if suffix == "ಗೆ":
                suffix = "ಕ್ಕೆ"
            return stem + suffix
        if last == "ಂ" and suffix in ("ಕ್ಕೆ", "ಗೆ"):  # ಕಿಲೋಗ್ರಾಂ + ಗೆ -> ಕಿಲೋಗ್ರಾಂಗೆ
            return words + "ಗೆ"
        if last == VIRAMA:  # ಕಿಲೋಮೀಟರ್ + ಗೆ -> ಕಿಲೋಮೀಟರ್‌ಗೆ
            if suffix == "ಕ್ಕೆ":
                suffix = "ಗೆ"
            if suffix.startswith("ರ") and len(suffix) > 1:
                suffix = "ನ" + suffix[1:]
            return words + ZWNJ + suffix
        if words.endswith(I_E_ENDINGS):  # ಕೋಟಿ + ರಲ್ಲಿ -> ಕೋಟಿಯಲ್ಲಿ ; ಕೋಟಿ + ಕ್ಕೆ -> ಕೋಟಿಗೆ
            if suffix in ("ಕ್ಕೆ", "ಗೆ"):
                return words + "ಗೆ"
            if suffix == "ಕ್ಕೂ":
                return words + "ಗೂ"
            if suffix.startswith("ರ"):
                return words + "ಯ" + suffix[1:]
            return words + suffix
        # inherent-a ending (ಸಾವಿರ, ಲಕ್ಷ, ನಿಮಿಷ): ರ-initial case suffixes take ದ, dative is ಕ್ಕೆ
        if suffix == "ಗೆ":
            return words + "ಕ್ಕೆ"
        if suffix.startswith("ರ") and len(suffix) > 1:
            return words + "ದ" + suffix[1:]
        if suffix == "ರ":
            return words + "ದ"
        return words + suffix

    def ordinal(self, n: int) -> str:
        return self.attach(self.say_int(n), "ನೇ")

    def mixed_fraction(self, whole, a, b):
        w = self.say_int(whole)
        if not w.endswith(U):
            return None
        if (a, b) == (1, 2):
            return w[:-1] + "ೂವರೆ"  # ಎರಡೂವರೆ
        if (a, b) == (1, 4):
            return w[:-1] + "ೂಕಾಲು"  # ಎರಡೂಕಾಲು
        if (a, b) == (3, 4):
            return w[:-1] + "ೂಮುಕ್ಕಾಲು"
        return None


KANNADA_LEX = {
    "point": "ಪಾಯಿಂಟ್", "minus": "ಮೈನಸ್", "plus": "ಪ್ಲಸ್", "times": "ಇಂಟು", "divide": "ಭಾಗಿಸು", "equals": "ಈಕ್ವಲ್ ಟು",
    "neq": "ಸಮವಲ್ಲ", "lt": "ಲೆಸ್ ದ್ಯಾನ್", "gt": "ಗ್ರೇಟರ್ ದ್ಯಾನ್", "le": "ಲೆಸ್ ದ್ಯಾನ್ ಆರ್ ಈಕ್ವಲ್ ಟು",
    "ge": "ಗ್ರೇಟರ್ ದ್ಯಾನ್ ಆರ್ ಈಕ್ವಲ್ ಟು", "pm": "ಪ್ಲಸ್ ಮೈನಸ್", "approx": "ಸುಮಾರು", "squared": "ವರ್ಗ",
    "cubed": "ಘನ", "power": "ಟು ದ ಪವರ್ {n}", "root": "ರೂಟ್", "cuberoot": "ಕ್ಯೂಬ್ ರೂಟ್", "fourthroot": "ಫೋರ್ತ್ ರೂಟ್",
    "fraction": "{b+ರಲ್ಲಿ} {a}", "mixed_fraction": "{x} ಪೂರ್ಣಾಂಕ {f}",
    "fractions_special": {(1, 2): "ಅರ್ಧ", (1, 4): "ಕಾಲು", (3, 4): "ಮುಕ್ಕಾಲು"},
    "per": "{u} ಪ್ರತಿ {p}", "percent": "ಶೇಕಡ {x}", "percent_word": "ಪರ್ಸೆಂಟ್", "percent_prefix": ["ಶೇಕಡಾ", "ಶೇಕಡ", "ಶೇ.", "ಶೇ"],
    "range": "{a+ರಿಂದ} {b}", "ratio": "{a} ಅನುಪಾತ {b}",
    "dot": "ಡಾಟ್", "slash": "ಸ್ಲ್ಯಾಶ್", "at": "ಅಟ್", "hyphen": "ಹೈಫನ್", "underscore": "ಅಂಡರ್‌ಸ್ಕೋರ್", "colon": "ಕೋಲನ್",
    "question": "ಪ್ರಶ್ನಾರ್ಥಕ ಚಿಹ್ನೆ", "hash": "ಹ್ಯಾಶ್", "tilde": "ಟಿಲ್ಡ್", "semicolon": "ಸೆಮಿಕೋಲನ್", "comma": "ಕಾಮಾ", "exclamation": "ಆಶ್ಚರ್ಯಸೂಚಕ ಚಿಹ್ನೆ",
    "permille": "ಸಾವಿರಕ್ಕೆ {x}", "ratio_cue": "ಅನುಪಾತ", "date_labels": "ದಿನಾಂಕ",
    "phone_keywords": ["ಫೋನ್ ನಂಬರ್", "ಫೋನ್", "ಮೊಬೈಲ್ ನಂಬರ್", "ಮೊಬೈಲ್", "ಸಹಾಯವಾಣಿ"], "and": "ಮತ್ತು", "number_word": "ಸಂಖ್ಯೆ",
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} ಗಂಟೆ", "time_hm": "{h} ಗಂಟೆ {m} ನಿಮಿಷ", "time_hms": "{h} ಗಂಟೆ {m} ನಿಮಿಷ {s} ಸೆಕೆಂಡ್",
    "time_ap": "{dp} {t}", "time_absorb": ("ಗಂಟೆ",), "dp_morning": "ಬೆಳಿಗ್ಗೆ", "dp_noon": "ಮಧ್ಯಾಹ್ನ", "dp_evening": "ಸಂಜೆ", "dp_night": "ರಾತ್ರಿ",
    "money": "{x} {cur}", "money_join": " ",
    "cur_INR": "ರೂಪಾಯಿ", "sub_INR": "ಪೈಸೆ", "cur_USD": "ಡಾಲರ್", "sub_USD": "ಸೆಂಟ್", "cur_EUR": "ಯೂರೋ",
    "sub_EUR": "ಸೆಂಟ್", "cur_GBP": "ಪೌಂಡ್", "sub_GBP": "ಪೆನ್ಸ್",
    "scale_thousand": "ಸಾವಿರ", "scale_lakh": "ಲಕ್ಷ", "scale_crore": "ಕೋಟಿ", "scale_million": "ಮಿಲಿಯನ್",
    "scale_billion": "ಬಿಲಿಯನ್", "scale_trillion": "ಟ್ರಿಲಿಯನ್",
    "scale_native": {"ಸಾವಿರ": 1, "ಲಕ್ಷ": 1, "ಕೋಟಿ": 1},
    "currency_native": {"ರೂ.": "INR", "ರೂ": "INR"},
    "code_connectors": ["ಸಂಖ್ಯೆ"],
    "code_keywords": ["ಒಟಿಪಿ", "ಓಟಿಪಿ", "ಪಿನ್ ಕೋಡ್", "ಪಿನ್‌ಕೋಡ್", "ಪಿನ್", "ಖಾತೆ ಸಂಖ್ಯೆ", "ಆಧಾರ್ ಸಂಖ್ಯೆ", "ಕೋಡ್"],
    "unit_abbr": {"ಕಿ.ಮೀ.": "km", "ಕಿ.ಮೀ": "km", "ಕಿಮೀ": "km", "ಕೆಜಿ": "kg", "ಕೆ.ಜಿ.": "kg", "ಕೆ.ಜಿ": "kg",
                  "ಕಿ.ಗ್ರಾಂ": "kg", "ಗ್ರಾಂ": "g", "ಸೆಂ.ಮೀ.": "cm", "ಸೆಂ.ಮೀ": "cm", "ಮಿ.ಮೀ.": "mm", "ಮಿ.ಮೀ": "mm",
                  "ಮೀ.": "m", "ಲೀ.": "l", "ಮಿ.ಲೀ.": "ml"},
    "abbr_native": {"ಡಾ.": "ಡಾಕ್ಟರ್", "ಕಿ.ಮೀ.": "ಕಿಲೋಮೀಟರ್", "ಸಂ.": "ಸಂಖ್ಯೆ"},
    "abbr_dr": "ಡಾಕ್ಟರ್", "abbr_mr": "ಮಿಸ್ಟರ್", "abbr_mrs": "ಮಿಸೆಸ್", "abbr_ms": "ಮಿಸ್", "abbr_prof": "ಪ್ರೊಫೆಸರ್",
    "abbr_etc": "ಇತ್ಯಾದಿ", "abbr_vs": "ವರ್ಸಸ್", "abbr_govt": "ಸರ್ಕಾರ", "abbr_approx": "ಸುಮಾರು",
    "abbr_eg": "ಉದಾಹರಣೆಗೆ", "abbr_ie": "ಅಂದರೆ", "abbr_jr": "ಜೂನಿಯರ್", "abbr_sr": "ಸೀನಿಯರ್", "abbr_ltd": "ಲಿಮಿಟೆಡ್",
    "abbr_pvt": "ಪ್ರೈವೇಟ್", "abbr_dept": "ಇಲಾಖೆ",
    # CLDR spellings replaced by the text's: ಡಿಗ್ರಿ (CLDR ಡಿಗ್ರಿಯು is a case form), ಸೆಲ್ಸಿಯಸ್ 13 vs ಸೆಲ್ಶಿಯಸ್ 4
    "u_deg": "ಡಿಗ್ರಿ", "u_degC": "ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್",
    "u_min": "ನಿಮಿಷ", "u_hr": "ಗಂಟೆ", "u_year": "ವರ್ಷ", "u_kmph": "ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಗಂಟೆ", "u_quintal": "ಕ್ವಿಂಟಾಲ್",
    "u_kmpl": "ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಲೀಟರ್", "u_bhp": "ಬಿಎಚ್‌ಪಿ", "u_rpm": "ಆರ್‌ಪಿಎಂ", "u_dB": "ಡೆಸಿಬಲ್",
    "u_kl": "ಕಿಲೋಲೀಟರ್", "u_cc": "ಸಿಸಿ", "u_Wh": "ವ್ಯಾಟ್ ಗಂಟೆ", "u_kV": "ಕಿಲೋವೋಲ್ಟ್", "u_mAh": "ಮಿಲಿಆಂಪಿಯರ್ ಗಂಟೆ",
}


def make(name="kannada"):
    lang = Kannada()
    lang.lex = {**cldr_layer("kannada"), **KANNADA_LEX}
    return lang
