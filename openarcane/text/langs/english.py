from __future__ import annotations

from .base import Lang, MAX_CARDINAL

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
ORD_IRREG = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
             "twelve": "twelfth"}


def _below100(n):
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + (f"-{ONES[o]}" if o else "")


def _below1000(n):
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(f"{ONES[h]} hundred")
    if r:
        parts.append(_below100(r))
    return " ".join(parts)


class English(Lang):
    name, code, script = "english", "en", "Latin"
    year_style = True

    def cardinal(self, n: int, indian: bool = False) -> str:
        if n == 0:
            return "zero"
        if indian:
            parts = []
            cr, r = divmod(n, 10**7)
            if cr:
                parts.append(f"{self.cardinal(cr, True)} crore")
            lk, r = divmod(r, 10**5)
            if lk:
                parts.append(f"{_below100(lk)} lakh")
            th, r = divmod(r, 1000)
            if th:
                parts.append(f"{_below100(th)} thousand")
            if r:
                parts.append(_below1000(r))
            return " ".join(parts)
        parts = []
        for value, word in ((10**12, "trillion"), (10**9, "billion"), (10**6, "million"), (1000, "thousand")):
            q, n = divmod(n, value)
            if q:
                parts.append(f"{self.cardinal(q)} {word}")
        if n:
            parts.append(_below1000(n))
        return " ".join(parts)

    def say_int(self, n: int, indian_grouping=None) -> str:
        if n >= MAX_CARDINAL:
            return self.say_digits(str(n))
        return self.cardinal(n, bool(indian_grouping))

    def digit(self, d: int) -> str:
        return ONES[d]

    def ordinal(self, n: int) -> str:
        words = self.cardinal(n)
        head, sep, last = words.rpartition(" ")
        pre, dash, unit = last.rpartition("-")
        if unit in ORD_IRREG:
            unit = ORD_IRREG[unit]
        elif unit.endswith("y"):
            unit = unit[:-1] + "ieth"
        else:
            unit += "th"
        return f"{head}{sep}{pre}{dash}{unit}"

    def date_day(self, d: int) -> str:
        return self.ordinal(d)

    def year(self, n: int) -> str:
        if 2000 <= n <= 2009 or n < 1010 or n > 2099 or n % 1000 == 0:
            return self.cardinal(n)
        hi, lo = divmod(n, 100)
        if lo == 0:
            return f"{_below100(hi)} hundred"
        if lo < 10:
            return f"{_below100(hi)} oh {ONES[lo]}"
        return f"{_below100(hi)} {_below100(lo)}"

    def say_time(self, h, m, s, ap):
        hw = self.cardinal(h)
        if m == 0 and s is None and not ap and h == 0:
            t = "midnight"
        elif m == 0 and s is None and not ap and h > 12:
            t = f"{hw} hundred hours"  # 24-hour clock: never "thirteen o'clock"
        elif m == 0 and s is None:
            t = f"{hw} o'clock" if not ap else hw
        elif m < 10:
            t = f"{hw} oh {ONES[m]}"
        else:
            t = f"{hw} {_below100(m)}"
        if s is not None:
            t += f" and {self.cardinal(s)} {'second' if s == 1 else 'seconds'}"
        if ap:
            t += " a m" if ap == "am" else " p m"
        return t


# a bare 4-digit number is a year only next to one of these cues ("in 1998", "1990s", "1998 AD")
YEAR_BEFORE_EN = (r"(?i:\b(?:in|since|from|until|till|by|of|during|year|years|before|after|around|circa|c\.|born|"
                  r"early|late|mid-?|summer|winter|spring|autumn|monsoon|batch|class|session|census|election|"
                  r"elections|copyright|©|FY|AY|CY)|\b\d{4}[ \t]+(?:to|and|or|till|until)|\b\d{4}[ \t]*[,/])")
YEAR_AFTER_EN = r"(?:[ \t]*,?[ \t]*(?:AD|BC|BCE|CE|A\.D\.|B\.C\.)(?![A-Za-z])|[ \t]+(?:to|and|or)[ \t]+\d{4}(?!\d))"

ENGLISH_LEX = {
    "point": "point", "minus": "minus", "plus": "plus", "times": "times", "divide": "divided by",
    "tz_IST": "Indian Standard Time", "equals": "equals", "neq": "is not equal to", "lt": "is less than", "gt": "is greater than",
    "le": "is less than or equal to", "ge": "is greater than or equal to", "pm": "plus or minus",
    "approx": "is approximately", "squared": "squared", "cubed": "cubed", "power": "to the power of {n}", "per": "{u} per {p}",
    "year_before": YEAR_BEFORE_EN, "year_after": YEAR_AFTER_EN,
    "root": "square root of", "cuberoot": "cube root of", "fourthroot": "fourth root of",
    "fraction": "{a} by {b}", "mixed_fraction": "{x} and {f}",
    "fractions_special": {(1, 2): "one half", (1, 4): "one quarter", (3, 4): "three quarters",
                          (1, 3): "one third", (2, 3): "two thirds"},
    "percent": "{x} percent", "percent_word": "percent", "range": "{a} to {b}", "ratio": "{a} is to {b}",
    "dot": "dot", "slash": "slash", "at": "at", "hyphen": "hyphen", "underscore": "underscore", "colon": "colon",
    "question": "question mark", "hash": "hash", "tilde": "tilde", "semicolon": "semicolon", "comma": "comma", "exclamation": "exclamation mark", "permille": "{x} per mille", "and": "and", "number_word": "number",
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "money": "{x} {cur}", "money_join": " and ",
    "cur_INR": ("rupee", "rupees"), "sub_INR": ("paisa", "paise"), "cur_USD": ("dollar", "dollars"),
    "sub_USD": ("cent", "cents"), "cur_EUR": ("euro", "euros"), "sub_EUR": ("cent", "cents"),
    "cur_GBP": ("pound", "pounds"), "sub_GBP": ("penny", "pence"),
    "scale_thousand": "thousand", "scale_lakh": "lakh", "scale_crore": "crore", "scale_million": "million",
    "scale_billion": "billion", "scale_trillion": "trillion",
    "abbr_dr": "Doctor", "abbr_mr": "Mister", "abbr_mrs": "Missus", "abbr_ms": "Miz", "abbr_prof": "Professor",
    "abbr_etc": "et cetera", "abbr_vs": "versus", "abbr_govt": "government", "abbr_approx": "approximately",
    "abbr_eg": "for example", "abbr_ie": "that is", "abbr_jr": "Junior", "abbr_sr": "Senior",
    "abbr_ltd": "Limited", "abbr_pvt": "Private", "abbr_dept": "Department",
    "u_kmpl": ("kilometre per litre", "kilometres per litre"), "u_quintal": ("quintal", "quintals"),
    "u_bhp": "b h p", "u_rpm": "r p m", "u_dB": ("decibel", "decibels"), "u_kl": ("kilolitre", "kilolitres"), "u_dl": ("decilitre", "decilitres"), "u_ton": ("ton", "tons"),
    "u_cc": "c c", "u_Wh": ("watt hour", "watt hours"), "u_kV": ("kilovolt", "kilovolts"),
    "u_mAh": ("milliampere hour", "milliampere hours"), "u_kPa": ("kilopascal", "kilopascals"),
}


def make(name="english"):
    from . import cldr_layer
    lang = English()
    lang.lex = {**cldr_layer("english"), **ENGLISH_LEX}
    return lang
