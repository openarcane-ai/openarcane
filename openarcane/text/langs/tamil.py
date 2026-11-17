"""Tamil. Standalone counting forms follow CLDR RBNF ta %spellout-numbering (main @ 3d45043): இருபத்து மூன்று,
நூற்று ஐந்து, ஆயிரத்து எண்ணூற்று ஐம்பத்து ஏழு. Changes: எண்ணூறு (corpus 6 / CLDR எண்நூறு 0), crore recursion
instead of அரபம்/கரபம், and the adjectival ஒரு in front of nouns and scale words."""
from __future__ import annotations

from . import cldr_layer
from .base import Lang

UNITS = ["பூஜ்யம்", "ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து", "ஆறு", "ஏழு", "எட்டு", "ஒன்பது"]
TEENS = ["பத்து", "பதினொன்று", "பன்னிரண்டு", "பதின்மூன்று", "பதினான்கு", "பதினைந்து", "பதினாறு", "பதினேழு",
         "பதினெட்டு", "பத்தொன்பது"]
TENS = ["", "", "இருபது", "முப்பது", "நாற்பது", "ஐம்பது", "அறுபது", "எழுபது", "எண்பது", "தொண்ணூறு"]
HUNDREDS = ["", "நூறு", "இருநூறு", "முந்நூறு", "நானூறு", "ஐநூறு", "அறுநூறு", "எழுநூறு", "எண்ணூறு", "தொள்ளாயிரம்"]

U, VIRAMA = "ு", "்"
VOWEL_SIGN = {"அ": "", "ஆ": "ா", "இ": "ி", "ஈ": "ீ", "உ": "ு", "ஊ": "ூ", "எ": "ெ",
              "ஏ": "ே", "ஐ": "ை", "ஒ": "ொ", "ஓ": "ோ"}
SUFFIX_NORMAL = {"ல்": "இல்", "ம்": "ஆம்", "வது": "ஆவது", "ஆம்": "ஆம்", "ஆவது": "ஆவது", "இல்": "இல்"}


def _comb(w: str) -> str:
    """combining form: இருபது -> இருபத்து, நூறு -> நூற்று, ஆயிரம் -> ஆயிரத்து."""
    if w.endswith("து"):
        return w[:-1] + "்து"
    if w.endswith("று"):
        return w[:-1] + "்று"
    if w.endswith("ம்"):
        return w[:-2] + "த்து"
    return w


def below100(n: int) -> str:
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEENS[n - 10]
    t, o = divmod(n, 10)
    return TENS[t] if not o else f"{_comb(TENS[t])} {UNITS[o]}"


class Tamil(Lang):
    name, code, script = "tamil", "ta", "Tamil"
    letters = "஀-௿‌‍"
    glue_unknown_suffix = True
    detached_suffixes = ("ஆம்", "ஆவது", "வது", "இல்", "க்கு", "ஆக")

    def adj(self, words: str) -> str:
        if words.endswith("ஒன்று"):
            return words[: -len("ஒன்று")] + "ஒரு"
        if words.endswith("பதினொன்று"):
            return words[: -len("பதினொன்று")] + "பதினொரு"
        return words

    def cardinal(self, n: int) -> str:
        if n < 100:
            return below100(n)
        parts = []
        cr, rest = divmod(n, 10**7)
        if cr:
            w = f"{self.adj(self.cardinal(cr))} கோடி"
            parts.append((w, w + "யே"))
        lk, rest = divmod(rest, 10**5)
        if lk:
            w = f"{self.adj(below100(lk))} லட்சம்"
            parts.append((w, _comb(w)))
        th, rest = divmod(rest, 1000)
        if th:
            if th == 1:
                w = "ஆயிரம்"
            else:
                pre = below100(th)
                w = (pre[:-1] if pre.endswith(U) else pre) + "ாயிரம்"  # இரண்டாயிரம், பத்தாயிரம்
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
        suffix = SUFFIX_NORMAL.get(suffix, suffix)
        first = suffix[:1]
        if first in VOWEL_SIGN:
            sign, rest = VOWEL_SIGN[first], suffix[1:]
            if words.endswith(U):  # மூன்று + ஆம் -> மூன்றாம், + இல் -> மூன்றில்
                return words[:-1] + sign + rest
            if words.endswith("ாம்"):  # கிலோகிராம் + இல் -> கிலோகிராமில் (loan noun, not ஆயிரம்-type)
                return words[:-1] + sign + rest
            if words.endswith("ம்"):
                if suffix in ("ஆம்", "ஆவது"):  # ஆயிரம் + ஆவது -> ஆயிரமாவது
                    return words[:-1] + sign + rest
                return words[:-2] + "த்த" + sign + rest  # ஆயிரம் + இல் -> ஆயிரத்தில்
            if words[-1:] in ("ி", "ீ", "ெ", "ே", "ை"):  # கோடி + இல் -> கோடியில்
                return words + "ய" + sign + rest
            if words.endswith(VIRAMA):
                return words[:-1] + sign + rest
            return words + suffix
        if words.endswith("ாம்") and suffix.startswith("க்கு"):  # கிலோகிராம் + க்கு -> கிலோகிராமுக்கு
            return words[:-1] + "ு" + suffix
        if words.endswith("ம்") and suffix.startswith("க்கு"):  # ஆயிரம் + க்கு -> ஆயிரத்துக்கு
            return words[:-2] + "த்து" + suffix
        return words + suffix

    def ordinal(self, n: int) -> str:
        return "முதல்" if n == 1 else self.attach(self.say_int(n), "ஆவது")

    def mixed_fraction(self, whole, a, b):
        w = self.say_int(whole)
        if not w.endswith(U):
            return None
        stem = w[:-1]
        if (a, b) == (1, 2):
            return stem + "ரை"  # இரண்டரை, ஒன்றரை
        if (a, b) == (1, 4):
            return stem + "ே கால்"  # இரண்டே கால்
        if (a, b) == (3, 4):
            return stem + "ே முக்கால்"
        return None


TAMIL_LEX = {
    "point": "புள்ளி", "minus": "கழித்தல்", "neg": "மைனஸ்", "dp_evening_until": 7,  # negative sign: மைனஸ் பதினைந்து (கழித்தல் is subtraction) REVIEW_NEEDED
     "plus": "கூட்டல்", "times": "பெருக்கல்", "divide": "வகுத்தல்",
    "equals": "சமம்", "neq": "சமமில்லை", "lt": "லெஸ் தேன்", "gt": "கிரேட்டர் தேன்",
    "le": "லெஸ் தேன் ஆர் ஈக்வல் டு", "ge": "கிரேட்டர் தேன் ஆர் ஈக்வல் டு", "pm": "கூட்டல் கழித்தல்",
    "approx": "தோராயமாக", "squared": "ஸ்கொயர்", "cubed": "க்யூப்", "power": "பவர் {n}", "root": "ரூட்",
    "cuberoot": "க்யூப் ரூட்", "fourthroot": "ஃபோர்த் ரூட்",
    "fraction": "{b+இல்} {a}", "mixed_fraction": "{x} முழு {f}",
    "fractions_special": {(1, 2): "அரை", (1, 4): "கால்", (3, 4): "முக்கால்"},
    "per": "{u} பெர் {p}", "percent": "{x} சதவீதம்", "percent_word": "சதவீதம்", "range": "{a} முதல் {b}", "ratio": "{a+க்கு} {b}",
    "dot": "டாட்", "slash": "ஸ்லாஷ்", "at": "அட்", "hyphen": "ஹைஃபன்", "underscore": "அண்டர்ஸ்கோர்",
    "colon": "கோலன்", "question": "கேள்விக்குறி", "hash": "ஹேஷ்", "tilde": "டில்டு", "semicolon": "செமிகோலன்", "comma": "காற்புள்ளி", "exclamation": "ஆச்சரியக்குறி",
    "permille": "ஆயிரத்துக்கு {x}", "phone_plus": "பிளஸ்", "ratio_cue": "விகிதம்", "date_labels": "தேதி",
    "phone_keywords": ["தொலைபேசி எண்", "தொலைபேசி", "போன்", "மொபைல் எண்", "மொபைல்", "உதவி எண்"], "and": "மற்றும்",
    "number_word": "எண்",
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} மணி", "time_hm": "{h} மணி {m} நிமிடம்", "time_hms": "{h} மணி {m} நிமிடம் {s} வினாடி",
    "time_ap": "{dp} {t}", "time_absorb": ("மணி",), "dp_morning": "காலை", "dp_noon": "மதியம்", "dp_evening": "மாலை",
    "dp_night": "இரவு",
    "money": "{x} {cur}", "money_join": " ",
    "cur_INR": "ரூபாய்", "sub_INR": "பைசா", "cur_USD": "டாலர்", "sub_USD": "சென்ட்", "cur_EUR": "யூரோ",
    "sub_EUR": "சென்ட்", "cur_GBP": "பவுண்டு", "sub_GBP": "பென்ஸ்",
    "scale_thousand": "ஆயிரம்", "scale_lakh": "லட்சம்", "scale_crore": "கோடி", "scale_million": "மில்லியன்",
    "scale_billion": "பில்லியன்", "scale_trillion": "டிரில்லியன்",
    "scale_native": {"ஆயிரம்": 1, "லட்சம்": 1, "கோடி": 1},
    "currency_native": {"ரூ.": "INR", "ரூ": "INR"},
    "code_connectors": ["எண்"],
    "code_keywords": ["ஓடிபி", "ஓ.டி.பி", "பின் கோடு", "பின்கோடு", "பின்", "கணக்கு எண்", "ஆதார் எண்", "குறியீடு"],
    "unit_abbr": {"கி.மீ.": "km", "கி.மீ": "km", "கிமீ": "km", "கி.கி.": "kg", "கி.கி": "kg", "கிலோ": "kg",
                  "செ.மீ.": "cm", "மி.மீ.": "mm", "மீ.": "m", "லி.": "l", "கி.": "g"},
    "abbr_native": {"டாக்.": "டாக்டர்", "கி.மீ.": "கிலோமீட்டர்"},
    "abbr_dr": "டாக்டர்", "abbr_mr": "மிஸ்டர்", "abbr_mrs": "மிஸஸ்", "abbr_ms": "மிஸ்", "abbr_prof": "பேராசிரியர்",
    "abbr_etc": "முதலியன", "abbr_vs": "எதிர்", "abbr_govt": "அரசு", "abbr_approx": "தோராயமாக",
    "abbr_eg": "உதாரணமாக", "abbr_ie": "அதாவது", "abbr_jr": "ஜூனியர்", "abbr_sr": "சீனியர்", "abbr_ltd": "லிமிடெட்",
    "abbr_pvt": "பிரைவேட்", "abbr_dept": "துறை",
    "u_hr": "மணிநேரம்", "u_min": "நிமிடம்", "u_sec": "வினாடி", "u_year": "ஆண்டு", "u_kmph": "மணிக்கு {x} கிலோமீட்டர்",
    "u_quintal": "குவிண்டால்", "u_kmpl": "கிலோமீட்டர் பெர் லிட்டர்", "u_bhp": "பி.எச்.பி", "u_rpm": "ஆர்.பி.எம்",
    "u_dB": "டெசிபல்", "u_kl": "கிலோலிட்டர்", "u_cc": "சிசி", "u_Wh": "வாட் மணிநேரம்", "u_kV": "கிலோவோல்ட்",
    "u_mAh": "மில்லிஆம்பியர் மணிநேரம்",
}


def make(name="tamil"):
    lang = Tamil()
    lang.lex = {**cldr_layer("tamil"), **TAMIL_LEX}
    return lang
