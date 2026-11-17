"""Bodo (Devanagari) and Manipuri (Meetei Mayek).

0-99 come from data/indic_number_tables.json, kept only where the word occurs in that language's training text.
Bodo: larger numbers are read digit by digit; हाजार and जौसे (= 100) occur but how a multiplier combines with them
is not attested. Bodo 100 alone is जौसे.
Manipuri puts the noun before the number, and the training text does the same with scale words, units, money and
the clock: ꯂꯤꯁꯤꯡ ꯑꯅꯤ ꯇꯔꯥꯃꯥꯊꯣꯏ (2011), ꯂꯥꯈ ꯑꯃ ꯂꯤꯁꯤꯡ ꯌꯥꯡꯈꯩ ꯃꯉꯥ ..., ꯂꯨꯄꯥ ꯀꯣꯇꯤ ꯌꯥꯡꯈꯩꯍꯨꯝꯗꯣꯢ, ꯂꯨꯄꯥ ꯵꯰꯰,
ꯄꯨꯡ ꯶ꯇ, ꯃꯤꯅꯤꯠ ꯇꯔꯥꯃꯉꯥ, ꯀꯤꯂꯣꯃꯤꯇꯔ ꯇꯔꯥꯃꯉꯥ. Hundreds (ꯆꯥꯇ꯭ꯔꯨꯛ, ꯆꯥꯅꯤꯄꯥꯟ ...) are spelt too irregularly to build,
so a number with a non-zero hundreds digit is read digit by digit. Concepts without a word fall back to Hindi for Bodo (same script, logged); Manipuri has no
same-script relative, so a missing concept drops that reading (e.g. a clock time is read as plain numbers).
"""
from __future__ import annotations

from . import cldr_layer
from .indo_aryan import DEVA, TABLES, ZW, IndoAryan, _Gap

MEETEI = "ꯀ-꯭ꫠ-꫶"


class SmallTable(IndoAryan):
    hundred_only = ""  # word for exactly 100

    def cardinal(self, n: int) -> str:
        if n < 100:
            return self._w(n)
        if n == 100 and self.hundred_only:
            return self.hundred_only
        raise _Gap(n)


# exact multiples attested in the Bodo text (number + जौ hundred, + रोजा thousand); no composition with a remainder
BRX_EXACT = {200: "नैजौ", 300: "थामजौ", 400: "ब्रैजौ", 500: "बाजौ", 600: "दजौ", 700: "स्निजौ", 900: "गुजौ",
             1000: "सेरोजा", 2000: "नैरोजा", 3000: "थामरोजा", 4000: "ब्रैरोजा", 5000: "बारोजा", 7000: "स्निरोजा",
             9000: "गुरोजा"}  # 27 24 16 25 5 11 12; 10 273 2 5 3 3 5
BRX_SIXTIES = {60: "दजि", 61: "दजिसे", 62: "दजिनै", 63: "दजिथाम", 65: "दजिबा", 66: "दजिद", 67: "दजिस्नि",
               69: "दजिगु"}  # 5 3 1 2 1 7 2 2 in the text
# Manipuri exact hundreds attested in the text: ꯆꯥꯃ 16, ꯆꯥꯃꯔꯤ 7, ꯆꯥꯃꯉꯥ 11, ꯆꯥꯇ꯭ꯔꯨꯛ 32, ꯆꯥꯅꯤꯄꯥꯟ 10, ꯆꯥꯃꯥꯄꯟ 2
MNI_HUNDREDS = {1: "ꯆꯥꯃ", 4: "ꯆꯥꯃꯔꯤ", 5: "ꯆꯥꯃꯉꯥ", 6: "ꯆꯥꯇ꯭ꯔꯨꯛ", 8: "ꯆꯥꯅꯤꯄꯥꯟ", 9: "ꯆꯥꯃꯥꯄꯟ"}


class Bodo(SmallTable):
    def cardinal(self, n: int) -> str:
        if n in BRX_EXACT:
            return BRX_EXACT[n]
        return super().cardinal(n)

    def ordinal(self, n: int) -> str:
        """गिबि (first, 516 in the text); otherwise cardinal + थि (नैथि 165, थामथि 76, ब्रैथि 35, जिथि 20)."""
        if n == 1:
            return "गिबि"
        try:
            return self.cardinal(n).replace("'", "").replace("’", "") + "थि"
        except Exception:
            return self.say_int(n)


class Manipuri(SmallTable):
    def ordinal(self, n: int) -> str:
        """ꯑꯍꯥꯟꯕ first (222); otherwise cardinal + ꯁꯨꯕ (ꯑꯅꯤꯁꯨꯕ 83, ꯑꯍꯨꯝꯁꯨꯕ 27); Pettigrew's grammar"""
        if n == 1:
            return "ꯑꯍꯥꯟꯕ"
        try:
            return self.cardinal(n) + "ꯁꯨꯕ"
        except _Gap:
            return self.say_int(n)

    def mixed_fraction(self, whole, a, b):
        """2½ -> ꯑꯅꯤꯒ ꯃꯈꯥꯏ (ani-ga makhai, cited; ꯑꯅꯤꯒ 74, ꯃꯈꯥꯏ 11 in the text)"""
        if (a, b) == (1, 2) and whole < 100 and self.below100[whole] is not None:
            return f"{self._w(whole)}ꯒ ꯃꯈꯥꯏ"
        return None

    def cardinal(self, n: int) -> str:
        if n < 100:
            return self._w(n)
        if n >= 10**9:
            raise _Gap(n)
        cr, rest = divmod(n, 10**7)
        lk, rest = divmod(rest, 10**5)
        th, rest = divmod(rest, 1000)
        h, rest = divmod(rest, 100)
        if h:
            if n == h * 100 and h in MNI_HUNDREDS:  # an exact hundred on its own: ꯆꯥꯃꯔꯤ (400)
                return MNI_HUNDREDS[h]
            raise _Gap(n)
        parts = [f"{word} {self._w(k)}" for word, k in (("ꯀꯣꯇꯤ", cr), ("ꯂꯥꯈ", lk), ("ꯂꯤꯁꯤꯡ", th)) if k]
        if rest:
            parts.append(self._w(rest))
        return " ".join(parts)


BRX_LEX = {
    "and": "आरो", "range": "{a} निफ्राय {b} सिम",  # निफ्राय 19, सिम 81 in the text; construction unverified
    "u_hr": "घन्टा", "u_min": "मिनिट", "u_sec": "सेकेन्ड", "u_year": "बोसोर",
    "cur_INR": "रां", "sub_INR": "पैसा",  # पैसा 6, पैसे 0
    "percent": "{x} जौखोन्दो", "percent_word": "जौखोन्दो",  # 62 in the text, प्रतिशत 0; govt text 25 जौखोन्दो
    "fractions_special": {(1, 2): "खावसे"},
    "mixed_fraction": "{x} आरो {f}",  # ब्रै आरो खावसे in the text; unverified  # half: 35 in the text (ब्रै आरो खावसे = four and a half); unverified
}

MNI_LEX = {
    "and": "ꯑꯃꯁꯨꯡ", "range": "{a} ꯗꯒꯤ {b} ꯐꯥꯎꯕ", "point": "ꯄꯣꯏꯟꯠ",
    "plus": "ꯄ꯭ꯂꯁ",  # English loan, 17 in the text (not in maths use there); unverified
    "fractions_special": {(1, 2): "ꯇꯪꯈꯥꯏ"},  # half, 20 in the text; unverified
    "percent": "{x} ꯄꯔꯁꯦꯟꯠ", "percent_word": "ꯄꯔꯁꯦꯟꯠ",  # English loan, number first: ꯊꯔꯇꯤ ꯄꯔꯁꯦꯟꯠ
    "unit_tpl": "{u} {x}", "u_hr": "ꯄꯨꯡ", "u_min": "ꯃꯤꯅꯤꯠ", "u_year": "ꯆꯍꯤ", "u_km": "ꯀꯤꯂꯣꯃꯤꯇꯔ",
    "cur_INR": "ꯂꯨꯄꯥ", "cur_USD": "ꯗꯣꯂꯔ", "sub_INR": "ꯄꯩꯁꯥ",  # ꯄꯩꯁꯥ 74 (Pettigrew money table)
    "u_kg": "ꯀꯤꯂꯣꯒ꯭ꯔꯥꯝ",  # 4 in the text  # ꯗꯣꯂꯔ ꯑꯅꯤ in the text (ꯗꯣꯂꯔ 9)
    "money": "{cur} {x}", "money_join": " ",
    "time_h": "ꯄꯨꯡ {h}", "time_hm": "ꯄꯨꯡ {h} ꯃꯤꯅꯤꯠ {m}",
    # month names as the training text spells them; dates are month first: ꯃꯥꯔꯆ ꯇꯔꯥ ꯃꯔꯤ, ꯃꯥꯔꯆ ꯲꯲, ꯲꯰꯲꯲
    "months": ["ꯖꯅꯨꯋꯥꯔꯤ", "ꯐꯦꯕ꯭ꯔꯨꯋꯥꯔꯤ", "ꯃꯥꯔꯆ", "ꯑꯦꯄ꯭ꯔꯤꯜ", "ꯃꯦ", "ꯖꯨꯟ", "ꯖꯨꯂꯥꯏ", "ꯑꯣꯒꯁꯠ", "ꯁꯦꯞꯇꯦꯝꯕꯔ",
               "ꯑꯣꯛꯇꯣꯕꯔ", "ꯅꯕꯦꯝꯕꯔ", "ꯗꯤꯁꯦꯝꯕꯔ"],
    "date": "{month} {d} {y}", "date_dm": "{month} {d}", "date_my": "{month} {y}",
    "scale_thousand": "ꯂꯤꯁꯤꯡ", "scale_lakh": "ꯂꯥꯈ", "scale_crore": "ꯀꯣꯇꯤ", "scale_tpl": "{s} {x}",
}


def make(name: str):
    lang = Manipuri() if name == "manipuri" else Bodo()
    t = TABLES["own"][name]
    lang.name = name
    lang.below100 = list(t["below100"])
    lang.hundred_only = t.get("hundred_only", "")
    if name == "bodo":
        for k, v in BRX_SIXTIES.items():
            lang.below100[k] = lang.below100[k] or v
    else:
        lang.below100[90] = lang.below100[90] or "ꯃꯔꯤꯐꯨꯇꯔꯥ"  # mari-phu-tara, Pettigrew (0 in the text)
    if name == "bodo":
        lang.code, lang.script, lang.letters, lang.fallback = "brx", "Devanagari", DEVA + ZW, ("hindi",)
        lex = {**cldr_layer("bodo"), **BRX_LEX}
        lex.setdefault("money", "{x} {cur}")
    else:
        lang.code, lang.script, lang.letters, lang.fallback = "mni", "Meetei Mayek", MEETEI + ZW, ()
        lex = dict(MNI_LEX)  # CLDR months for mni are in Bengali script: not used
    assert len(lang.below100) == 100 and all(lang.below100[:10]), name
    lang.lex = lex
    return lang
