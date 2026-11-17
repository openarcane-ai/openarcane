"""Span scanner: finds verbalisable spans and rewrites only those; everything else is copied as is."""
from __future__ import annotations

import calendar
import re
import threading
import unicodedata
from dataclasses import dataclass
from typing import Callable

from .langs.base import MissingWord
from .numerals import fold_digits, group_digits, split_groups
from .units import ENGLISH_ONLY, TIGHT_ONLY, UNIT_ALIASES

# ---------------------------------------------------------------- shared sub-patterns
# grouped integer: western 1,234,567 | indian 12,34,567 | plain digits
NUMI = r"(?:\d{1,3}(?:,\d{3})+(?![\d]|,\d)|\d{1,2}(?:,\d{2})+,\d{3}(?![\d]|,\d)|\d+)"
NUM = rf"(?:{NUMI}(?:\.\d+)?|(?<![\w.])\.\d+)"
VIRAMAS = "\u094d\u09cd\u0a4d\u0acd\u0b4d\u0bcd\u0c4d\u0ccd\u0d4d"


def _kw_rx(k: str) -> str:
    """a native keyword as written in many ways: पिन कोड / पिनकोड, ପିନ କୋଡ / ପିନ୍‌କୋଡ୍ (optional virama, joiner, space)"""
    parts = [p for p in k.replace("\u200c", " ").replace("\u200d", " ").split() if p]
    parts = [re.escape(p.rstrip(VIRAMAS)) + f"[{VIRAMAS}]?" for p in parts]
    return "[ \\t\u200c\u200d]*".join(parts)


# Indic/Arabic combining marks and joiners: a virama or vowel sign ends a word too (ಕೋವಿಡ್-19 is not minus)
MARKS = "\u0900-\u0DFF\uABC0-\uABFF\u1C50-\u1C7F\u064B-\u065F\u0670\u06D6-\u06ED\u200C\u200D"
SIGN = rf"(?:(?<![\w)\]}}.,{MARKS}])[-−](?=\.?\d))?"
RNUM = rf"(?:(?<=[–—])[-−]|(?<=[–—] )[-−])?{NUM}"  # right endpoint: signed only after an en/em dash
QTY = rf"{SIGN}{NUM}(?:\s?[-–—]\s?{RNUM})?"  # number or number range

LATIN_SCALES = {
    "lakh": "lakh", "lakhs": "lakh", "lac": "lakh", "lacs": "lakh", "L": "lakh",
    "crore": "crore", "crores": "crore", "cr": "crore", "Cr": "crore", "cr.": "crore", "Cr.": "crore",
    "k": "thousand", "K": "thousand", "thousand": "thousand",
    "mn": "million", "M": "million", "million": "million",
    "bn": "billion", "B": "billion", "billion": "billion",
    "tn": "trillion", "trillion": "trillion",
}
# ₹1.5 Lakh, Rs 2 CRORE: alphabetic scale names in any case (unit-like symbols L, K, M, B stay case-sensitive)
LATIN_SCALES.update({v: k2 for k, k2 in list(LATIN_SCALES.items()) if len(k.rstrip(".")) > 2
                     for v in (k.capitalize(), k.upper())})
SCALE_VALUE = {"thousand": 10**3, "lakh": 10**5, "million": 10**6, "crore": 10**7, "billion": 10**9,
               "trillion": 10**12}

CURRENCY_PRE = {
    "₹": "INR", "Rs.": "INR", "Rs": "INR", "RS.": "INR", "RS": "INR", "rs.": "INR", "INR": "INR",
    "Re.": "INR", "Re": "INR",
    "US$": "USD", "$": "USD", "USD": "USD", "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP",
}
CURRENCY_POST = {"INR": "INR", "USD": "USD", "EUR": "EUR", "GBP": "GBP", "₹": "INR", "Rs": "INR", "Rs.": "INR",
                 "rupees": "INR", "rupee": "INR", "dollars": "USD", "dollar": "USD"}

MONTHS_EN = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9,
    "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
MON_RX = r"(?:" + "|".join(sorted(MONTHS_EN, key=len, reverse=True)) + r")"

CODE_KEYWORDS_EN = [
    r"OTP", r"otp", r"PIN", r"[Pp]in ?[Cc]ode", r"PIN ?[Cc]ode", r"[Pp]incode", r"[Pp]asscode",
    r"[Vv]erification [Cc]ode", r"[Cc]ode", r"CVV", r"A/[Cc]", r"a/c", r"[Aa]ccount(?: [Nn]o\.?| [Nn]umber| #)?",
    r"[Aa]cct\.?(?: [Nn]o\.?)?", r"[Cc]ard(?: [Nn]o\.?| [Nn]umber)", r"Aadha?ar(?: [Nn]o\.?| [Nn]umber)?",
    r"PNR(?: [Nn]o\.?)?", r"[Rr]ef(?:erence)?(?: [Nn]o\.?| ID| [Nn]umber)?", r"[Tt]xn(?: ID)?",
    r"[Tt]ransaction(?: ID| [Nn]o\.?)", r"[Oo]rder(?: ID| [Nn]o\.?)", r"ID", r"[Rr]oll [Nn]o\.?",
    r"[Rr]eg(?:istration)?\.? [Nn]o\.?", r"[Tt]icket(?: [Nn]o\.?| ID)", r"[Cc]ustomer ID", r"UAN", r"UPI PIN",
    r"[Cc]onsumer [Nn]o\.?", r"IMEI", r"[Ss]erial [Nn]o\.?", r"[Pp]olicy [Nn]o\.?", r"[Bb]ooking ID",
]

# words in front of a number that make it a phone/dial number even when short (Call 112, Helpline: 1098)
PHONE_CUES_EN = [r"[Cc]all", r"CALL", r"[Dd]ial", r"DIAL", r"[Hh]elpline(?: [Nn]o\.?| [Nn]umber)?", r"[Tt]oll[- ]?[Ff]ree",
                 r"[Pp]hone(?: [Nn]o\.?| [Nn]umber)?", r"[Pp]h\.", r"[Tt]el\.?", r"[Mm]ob\.?", r"[Mm]obile(?: [Nn]o\.?)?",
                 r"WhatsApp", r"[Cc]ontact(?: [Nn]o\.?| [Nn]umber)?"]
DATE_LABEL_EN = r"(?:[Dd]ate[d]?|DATE|DOB|D\.O\.B\.?|[Dd]ate of [Bb]irth)"
RATIO_CUE_EN = r"(?:[Rr]atio|RATIO|[Ii]n the ratio(?: of)?)"
PERMILLE_DEFAULT = None

SUPERSCRIPTS = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
VULGAR = {"½": (1, 2), "¼": (1, 4), "¾": (3, 4), "⅓": (1, 3), "⅔": (2, 3), "⅕": (1, 5), "⅛": (1, 8),
          "⅜": (3, 8), "⅝": (5, 8), "⅞": (7, 8), "⅙": (1, 6), "⅚": (5, 6), "⅖": (2, 5), "⅗": (3, 5), "⅘": (4, 5)}

VULGAR_CHARS = "½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘"
EMPHASIS = re.compile(r"(?<![\w*])(?P<d>\*\*?)(?=[^\s*])[^*\n]*?(?<=[^\s*])(?P=d)(?![\w*])")  # *word*, **word**; not 2*3
OPERAND_L = r"[0-9A-Za-z)\]}²³¹⁰⁴-⁹πθαβγλμσΩ!%‰٪½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘]"
OPERAND_R = r"[0-9A-Za-z(\[{√∛−πθαβγλμσΩ₹$€£.½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘-]"  # ½+¼=¾
MATH_OPS = {"/": "divide", "+": "plus", "−": "minus", "-": "minus", "×": "times", "*": "times", "·": "times", "÷": "divide",
            "=": "equals", "≠": "neq", "<": "lt", ">": "gt", "≤": "le", "≥": "ge", "±": "pm", "≈": "approx",
            "∓": "pm"}
OP_CHARS = "=+×÷*<>≤≥≠"
# script stops too (Urdu ۔), and a stop followed by closing quotes or brackets: “… हैं।”
SENT_END = re.compile(r"[.?!।॥۔؟꯫᱾][”“\"'’‘»«)\]]*(?=[ \t]+\S)|\n")
# a currency, unit or scale word right after a number makes it an amount (9876543210 INR), never a phone number
DATE_AHEAD = (r"(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?|\d{4}[/.-]\d{1,2}[/.-]\d{1,2})(?!\d)"
              rf"|\d{{1,2}}(?i:st|nd|rd|th)?[ \t-]?(?i:of[ \t])?(?i:{MON_RX})\.?(?![A-Za-z])")
MATH_CONTEXT = re.compile(r"[=+×÷≠≤≥±√²³^−]|(?<=\d)\s?\*\s?(?=\d)|(?<=[\w)])[ \t][<>][ \t](?=[\w(−-])"
                          r"|(?<=\d)[<>](?=[\d−-])")


def _cat(ch: str) -> str:
    return unicodedata.category(ch)[0] if ch else ""


@dataclass
class Rule:
    name: str
    rx: re.Pattern
    handler: Callable
    suffix: bool = False  # a native suffix may follow and is joined with sandhi


class Engine:
    def __init__(self, lang):
        self.L = lang
        self.rules = self._build_rules()
        rt = re.search(r"\{b[^}]*\}[ \t]+([^\s{}]+)$", lang.w("range", "") or "")
        self._range_tail = rt.group(1) if rt else None
        trig = r"\.(?=\d)|[0-9₹$€£√∛∜²³¹⁰⁴-⁹½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘#&+−×÷=≠<>≤≥±≈^*·@-]|(?<=\s)/(?=\s)|(?<=[½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘])/|(?<=\d)/(?=[½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘])|(?<![A-Za-z])[A-Za-z]"
        native_starts = "".join(sorted({re.escape(k[0]) for k in self._native_keys()}))
        if native_starts:
            trig += f"|[{native_starts}]"
        self.trigger = re.compile(trig)
        nat = rf"|[{lang.letters}]\.?" if lang.letters else ""  # 5 किलो+3 किलो, 5 रु.+3 रु.
        # a markdown-wrapped operand counts too: *2* + *3* = *5*
        self._operand_before = re.compile(rf"(?:{OPERAND_L}{nat})(?:\*{{1,2}}|_{{1,2}})?[ \t]*$")
        rc, dl = lang.w("ratio_cue", ""), lang.w("date_labels", "")
        self._ratio_cue = re.compile(rf"(?:{RATIO_CUE_EN}{'|' + rc if rc else ''})[ \t]*(?:[:=-][ \t]*)?$")
        self._date_label = re.compile(rf"(?:{DATE_LABEL_EN}{'|' + dl if dl else ''})[ \t]*(?:[:=-][ \t]*)?$")
        units = sorted(set(UNIT_ALIASES) | set(lang.w("unit_abbr", {}) or {}) | set(CURRENCY_POST)
                       | set(lang.w("currency_native", {}) or {}) | set(LATIN_SCALES), key=len, reverse=True)
        self._quantity_after = re.compile(rf"[ \t]*(?:{'|'.join(map(re.escape, units))})"
                                          rf"(?![A-Za-z0-9]|{self._letters_rx() if lang.letters else '(?!x)x'})")
        self._state = threading.local()  # per-call input text: one cached engine may serve many threads
        if lang.letters:
            self._suffix_rx = re.compile(rf"[-‐]?(?P<s>[{lang.letters}]+)")
            if lang.detached_suffixes:
                ds = "|".join(re.escape(s) for s in sorted(lang.detached_suffixes, key=len, reverse=True))
                self._detached_rx = re.compile(rf" (?P<s>{ds})(?![{lang.letters}])")

    @property
    def _text(self) -> str:
        return self._state.text

    # ------------------------------------------------------------ helpers
    def _native_keys(self):
        L = self.L
        keys = list((L.w("abbr_native", {}) or {}).keys()) + list((L.w("unit_abbr", {}) or {}).keys())
        keys += list(L.w("code_keywords", []) or [])
        keys += list(L.w("currency_native", {}) or {})
        keys += [p for p in (L.w("percent_prefix", []) or [])]
        keys += list(L.w("phone_keywords", []) or [])
        if L.code != "en":  # native month names start a month-year date (अगस्त 1998)
            keys += list(L.w("months", []) or []) + list((L.w("month_aliases", {}) or {}).keys())
        return [unicodedata.normalize("NFC", k) for k in keys if k]

    def _num_value(self, s: str):
        """'1,23,456.50' -> (int_str, frac_str)"""
        s = s.replace(",", "")
        if "." in s:
            a, b = s.split(".", 1)
            return a, b
        return s, ""

    def say_num(self, s: str, *, year_ok=False, count=False) -> str:
        """Verbalise a single number string with optional sign, grouping, decimals."""
        L = self.L
        neg = s[:1] in "-−"
        if neg:
            s = s[1:]
        has_comma = "," in s
        ip, fp = self._num_value(s)
        if fp and L.code == "en" and ip and self._indian(s):  # 1,00,000.5 -> one lakh point five
            words = f"{L.say_int(int(ip), indian_grouping=True)} {L.w('point')} {L.say_digits(fp)}"
        elif fp:
            words = L.say_decimal(ip, fp)
        elif len(ip) > 1 and ip[0] == "0":
            words = L.say_digits(ip)
        elif not has_comma and len(ip) >= 9 and not count:
            words = L.comma.join(L.say_digits(g) for g in group_digits(ip))
        elif year_ok and not has_comma and len(ip) == 4 and getattr(L, "year_style", False):
            words = L.year(int(ip))
        else:
            words = L.say_int(int(ip), indian_grouping=self._indian(s)) if L.code == "en" else L.say_int(int(ip))
        if neg:
            words = f"{self.neg_word()} {words}"
        return words

    def neg_word(self):
        return self.L.w("neg", "") or self.L.w("minus")

    @staticmethod
    def _indian(s: str):
        if "," not in s:
            return None
        ip = s.split(".")[0]
        groups = ip.split(",")
        return len(groups) > 2 and len(groups[1]) == 2 or (len(groups) == 2 and len(groups[0]) > 3)

    def say_qty(self, q: str, math: bool = False, **kw) -> str:
        """number or range 'a-b'; on a line with maths, 'a - b' is a subtraction (5 - 2 kg = 3 kg)"""
        m = re.fullmatch(rf"({SIGN}{NUM})(\s?)([-–—])(\s?)({RNUM})", q)
        if m:
            a, b = self.say_num(m.group(1), **kw), self.say_num(m.group(5), **kw)
            if math and m.group(3) == "-":
                return f"{a} {self.L.w('minus')} {b}"
            tpl = (kw.get("count") and self.L.w("range_qty", "")) or self.L.w("range")
            return self.L.fill(tpl, a=a, b=b)
        return self.say_num(q, **kw)

    @staticmethod
    def _is_one(q: str) -> bool:
        return q.replace(",", "") in ("1", "1.0", "1.00")

    # ------------------------------------------------------------ rules
    def _build_rules(self):
        L = self.L
        R = []

        def add(name, pattern, handler, suffix=False, flags=0):
            R.append(Rule(name, re.compile(pattern, flags), handler, suffix))

        # 1. URL / email
        add("email", r"(?<![\w.@])[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w])",
            self.h_url)
        # UPI payment address: ravi@okicici (no dotted domain, so not an email)
        add("upi", r"(?<![\w.@])[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z][A-Za-z0-9]+(?![\w.@-])", self.h_url)
        # Indian vehicle registration KA-01-AB-1234: letters kept, digit runs read digit by digit
        add("vehicle", r"(?<![A-Za-z0-9-])[A-Z]{2}(?P<s1>[ -]?)\d{1,2}(?P=s1)[A-Z]{1,3}(?P=s1)\d{4}(?![A-Za-z0-9])",
            self.h_vehicle)
        add("url", r"(?<![\w@])(?:(?:https?|ftp)://|www\.)[^\s<>()\[\]{}\"'`]*[^\s<>()\[\]{}\"'`.,;:!?*_]", self.h_url)
        add("domain", r"(?<![\w@./])[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:com|in|org|net|gov|edu|co|io|ai|info|app|dev|"
                      r"me|ac\.in|gov\.in|co\.in|nic\.in|org\.in)(?:/[^\s<>()\[\]{}\"'`]*[^\s<>()\[\]{}\"'`.,;:!?*_])?(?![\w])",
            self.h_url)
        # 2. phone numbers
        add("phone_cc", r"(?<![\w+])\+\d{1,3}(?:[\s.-]?\(?\d{2,5}\)?){2,5}(?![\d])", self.h_phone)
        add("phone_mobile", r"(?<![\d.,+])(?:0|91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d])", self.h_phone)
        add("phone_land", r"(?<![\d.,])(?:\(0\d{2,4}\)\s?|0\d{2,4}[\s-])\d{3,4}[\s-]?\d{3,4}(?![\d])", self.h_phone)
        add("phone_tollfree", r"(?<![\d.,])1[89]00[\s-]\d{2,4}[\s-]?\d{3,4}(?![\d])", self.h_phone)
        # 3. keyword-triggered codes (OTP, PIN, account ...)
        kws = CODE_KEYWORDS_EN + [_kw_rx(k) for k in (L.w("code_keywords", []) or [])]
        # label syntax only: "OTP: 1234", "OTP is 1234", "OTP for login is 1234"; never "Account balance: 1250"
        conn = "".join("|" + re.escape(c) for c in (L.w("code_connectors", []) or []))  # Hindi है, Marathi आहे ...
        gap = (rf"(?:[ \t]*(?:(?:[:#=]|:-|[-–—]|is|was{conn})[ \t]*)?"
               r"|(?:[ \t]+(?:for|to|of|your|the|my|login|log|in|sign|verification|transaction|payment|reset|"
               r"registration|password|account|delivery|is)){1,4}[ \t]*(?:[:#=]|:-|is|was)?[ \t]*)")
        add("code", rf"(?<![A-Za-z])(?P<kw>{'|'.join(kws)})(?![A-Za-z])(?P<gap>{gap})"
                    rf"(?P<num>\d+(?:(?:[ \t](?!{DATE_AHEAD})|-)\d+(?![:./]\d))*)(?![\d]|[.,:/]\d|\s?%)", self.h_code)
        cues = PHONE_CUES_EN + [_kw_rx(k) for k in (L.w("phone_keywords", []) or [])]
        self._phone_cue = re.compile(rf"(?<![A-Za-z])(?:{'|'.join(cues)})(?![A-Za-z])[ \t]*(?:[:#-][ \t]*)?(?:\+?[ \t]*)$")
        add("phone_cue", rf"(?<![A-Za-z])(?P<kw>{'|'.join(cues)})(?![A-Za-z])(?P<gap>[ \t]*(?:[:#-][ \t]*)?)"
                         rf"(?P<num>\d{{3,15}})(?=[ \t]*(?:$|\n|[.,;!?)/]|or\b|and\b))", self.h_code)
        post = L.w("phone_cues_after", []) or []
        if post:
            add("phone_cue_post", rf"(?<![\d.,])(?P<num>\d{{3,15}})(?=[ \t]*(?:{'|'.join(map(re.escape, post))}))",
                self.h_code_bare)
        # 4. dates
        add("date_dmy", r"(?<![A-Za-z\d.,/-])(?P<d>\d{1,2})(?P<sep>[/.-]|[ \t]+/[ \t]+)(?P<m>\d{1,2})(?P<sep2>[/.-]|[ \t]+/[ \t]+)(?P<y>\d{4}|\d{2})(?![\d]|[/.-]\d)",
            self.h_date_num, suffix=True)
        add("date_ymd", r"(?<![A-Za-z\d.,/-])(?P<y>\d{4})(?P<sep>[/.-]|[ \t]+/[ \t]+)(?P<m>\d{1,2})(?P<sep2>[/.-]|[ \t]+/[ \t]+)(?P<d>\d{1,2})(?![\d]|[/.-]\d)",
            self.h_date_num, suffix=True)
        add("date_d_mon", rf"(?<![\d.,])(?P<d>\d{{1,2}})(?:st|nd|rd|th)?[\s-]?(?:of\s)?(?P<mon>{MON_RX})\.?(?![A-Za-z])"
                          rf"(?:,?[\s-](?P<y>\d{{4}})(?![\d]))?", self.h_date_mon, suffix=True, flags=re.I)
        add("date_mon_d", rf"(?<![A-Za-z])(?P<mon>{MON_RX})\.?\s(?P<d>\d{{1,2}})(?:st|nd|rd|th)?(?![\d])"
                          rf"(?:,?\s(?P<y>\d{{4}})(?![\d]))?", self.h_date_mon, suffix=True, flags=re.I)
        add("date_mon_y", rf"(?<![A-Za-z])(?P<mon>{MON_RX})\.?,?\s(?P<y>\d{{4}})(?![\d])", self.h_date_mon, suffix=True,
            flags=re.I)
        months = [unicodedata.normalize("NFC", x) for x in (L.w("months", []) or [])]
        aliases = {unicodedata.normalize("NFC", k): v for k, v in (L.w("month_aliases", {}) or {}).items()}
        self._nmon = {mname: i + 1 for i, mname in enumerate(months) if L.code != "en"}
        self._nmon.update(aliases)
        if self._nmon:
            NM = "(?:" + "|".join(re.escape(x) for x in sorted(self._nmon, key=len, reverse=True)) + ")"
            add("date_d_nmon", rf"(?<![\d.,])(?P<d>\d{{1,2}})[ \t-]?(?P<nmon>{NM})(?![{L.letters or 'A-Za-z'}])"
                               rf"(?:,?[ \t-](?P<y>\d{{4}})(?![\d]))?", self.h_date_mon, suffix=True)
            add("date_nmon_y", rf"(?<![{L.letters or 'A-Za-z'}])(?P<nmon>{NM}),?[ \t](?P<y>\d{{4}})(?![\d])",
                self.h_date_mon, suffix=True)
        # 5. times
        add("time", r"(?<![\d.:])(?P<h>[01]?\d|2[0-3])(?P<sep>[:.])(?P<m>[0-5]\d)(?::(?P<s>[0-5]\d))?(?![\d])"
                    r"(?:\s?(?P<ap>[AaPp]\.?\s?[Mm]\.?)(?![A-Za-z]))?(?:\s?(?P<hrs>hrs|Hrs|HRS)(?![A-Za-z]))?"
                    r"(?:(?P<tzsp>\s?)(?P<tz>IST)(?![A-Za-z]))?",
            self.h_time, suffix=True)
        add("time_h", r"(?<![\d.:])(?P<h>1[0-2]|0?[1-9])\s?(?P<ap>[AaPp]\.?\s?[Mm]\.?)(?![A-Za-z])", self.h_time,
            suffix=True)
        # 6. money
        cur_native = L.w("currency_native", {}) or {}
        cpre = sorted(list(CURRENCY_PRE) + list(cur_native), key=len, reverse=True)
        scales = sorted(list(LATIN_SCALES) + list((L.w("scale_native", {}) or {})), key=len, reverse=True)
        SC = "(?:" + "|".join(re.escape(s) for s in scales) + r")(?![A-Za-z])"
        self._scale_rx = SC
        SCI = r"(?:[eE](?P<e>[-+−]?\d{1,3})(?![\w.]))?"
        MORE = rf"(?P<more>(?:[ \t]+\d+(?:\.\d+)?[ \t]?{SC})*)"  # ₹1 crore 25 lakh: further, smaller components
        add("money_pre", rf"(?P<neg>(?<![\w)\]}}.,{MARKS}])[-−])?(?<![A-Za-z])(?P<cur>{'|'.join(re.escape(c) for c in cpre)})\s?(?P<q>{QTY}){SCI}"
                         rf"(?:\s?(?P<sc>{SC}){MORE})?(?P<dash>\s?/-)?", self.h_money, suffix=True)
        cpost = sorted(set(CURRENCY_POST) | set(cur_native), key=len, reverse=True)
        add("money_post", rf"(?P<q>{QTY}){SCI}(?:\s?(?P<sc>{SC}){MORE})?\s?(?P<cur>{'|'.join(re.escape(c) for c in cpost)})"
                          rf"(?![A-Za-z]|{self._letters_rx()})(?P<dash>\s?/-)?", self.h_money, suffix=True)
        # 7. percent
        add("percent", rf"(?P<q>{QTY})\s?(?P<p>%|٪|‰)", self.h_percent, suffix=True)
        pp = L.w("percent_prefix", []) or []
        if pp:
            add("percent_pre", rf"(?<!{self._letters_rx()})(?P<p>{'|'.join(re.escape(p) for p in pp)})\s?(?P<q>{QTY})(?!\s?%)", self.h_percent,
                suffix=True)
        # 7b. mixed numbers, scientific notation, decades
        native_units = dict(L.w("unit_abbr", {}) or {})
        # a written-out unit word that starts with a native abbreviation (Tamil கிலோ = kg) is that word, not the
        # abbreviation plus a suffix: 1 கிலோகிராம், 2 கிலோமீட்டர்
        for key in sorted(set(UNIT_ALIASES.values()) | set(native_units.values())):
            for one in (True, False):
                try:
                    w = L.unit_word(key, one=one)
                except MissingWord:
                    w = None
                if w and "{" not in w and w not in native_units and \
                        any(w.startswith(a) and not a.isascii() for a in native_units):
                    native_units[w] = key
        self._native_units = native_units
        # ... and a native abbreviation never matches the start of a differently spelt unit word (కిలోమీటర్)
        guard = {}
        for w in native_units:
            for a in native_units:
                if w != a and w.startswith(a) and not a.isascii() and not a.endswith("."):
                    guard.setdefault(a, set()).add(re.escape(w[len(a):len(a) + 2]))

        def alt(units):
            return "|".join(re.escape(u) + (f"(?!{'|'.join(sorted(guard[u]))})" if u in guard else "")
                            for u in sorted(units, key=len, reverse=True))
        unit_any = alt(set(UNIT_ALIASES) | set(native_units))
        per = "|".join(re.escape(u) for u in sorted(PER_UNITS, key=len, reverse=True))
        utail = (rf"(?:(?P<usp>[ \t]*)(?P<u>{unit_any})(?:/(?P<uper>{per}))?"
                 rf"(?![A-Za-z0-9]))?")  # a native case ending may follow: 1½kgಗೆ
        add("mixed", rf"(?<![\d/.,])(?P<sg>{SIGN})(?P<w>\d+)[ \t](?P<a>\d{{1,2}})/(?P<b>\d{{1,2}})(?![\d]|/\d|\.\d)"
                     + utail, self.h_mixed, suffix=True)
        add("sci", rf"(?<![\w.])(?P<sg>{SIGN})(?P<m>\d+(?:\.\d+)?)[eE](?P<e>[-+−]?\d{{1,3}})(?![\d.])(?=(?:{unit_any})(?![A-Za-z0-9])|(?![\w.]))(?P<pct>[ \t]?[%٪])?" + utail,
            self.h_sci, suffix=True)
        # 7c. plain quantities with a scale word: 5 lakh, 2.5 crore, 10 million, 5k (money takes ₹5 lakh first)
        add("scaled", rf"(?P<q>{QTY})(?:[ \t]?(?P<sc>(?i:lakhs?|lacs?|crores?)|[Cc]r\.?|(?i:million|billion|trillion|thousand)|mn|bn|tn)"
                      rf"(?![A-Za-z])|(?P<sck>[kK])(?![A-Za-z0-9]))" + utail.replace("(?P<usp>[ \t]*)", "(?P<usp>[ \t]+)"),
            self.h_scaled, suffix=True)
        if L.code == "en":
            add("decade", r"(?<![\w.,])(?P<y>\d{1,3}0)'?s(?![A-Za-z])", self.h_decade)
        # 8. units
        ua = {k: v for k, v in UNIT_ALIASES.items() if L.code == "en" or k not in ENGLISH_ONLY}
        ua.update(self._native_units)
        self._units = ua
        tight = alt(ua)
        spaced = alt(set(ua) - TIGHT_ONLY)
        add("duration", r"(?<![\w.,])(?P<h>\d{1,3})[ \t]?(?:h|hrs?)[ \t]?(?P<m>\d{1,2})[ \t]?(?:m|mins?)"
                        r"(?:[ \t]?(?P<s>\d{1,2})[ \t]?(?:s|secs?))?(?![A-Za-z0-9])", self.h_duration)
        add("unit", rf"(?P<q>{QTY})(?:(?P<u>{tight})|(?P<usp>[ \t]+)(?P<u2>{spaced}))(?:/(?P<per>{per}))?"
                    r"(?![A-Za-z0-9])", self.h_unit, suffix=True)
        # 9. maths
        add("sqrt", r"(?P<r>[√∛∜])\s?", self.h_root)
        add("sup", rf"(?<={OPERAND_L})(?P<sup>[⁰¹²³⁴⁵⁶⁷⁸⁹]+)", self.h_sup)
        add("caret", rf"(?<={OPERAND_L})\s?\^\s?(?P<e>[-−]?\d+|[A-Za-z])(?![\w])", self.h_sup)
        add("times_x", r"(?<=\d)\s?[xX](?=\s?\d)", lambda m: (f" {self.L.w('times')} ", m.end()))
        add("op", rf"(?P<op>[+×÷=≠≤≥<>±≈∓·−]|\*(?!\*)|(?<=\s)[-/](?=\s)|(?<=[\w)\]%{MARKS}])-(?=[ \t]*[(\[])|(?<=[{VULGAR_CHARS}])[-/](?=[\d{VULGAR_CHARS}])|(?<=\d)/(?=[{VULGAR_CHARS}]))"
                  rf"(?P<s2>[ \t]*\n?[ \t]*)(?=(?:\*{{1,2}}|_{{1,2}})?(?:{OPERAND_R}|{self._letters_rx()}))", self.h_op)
        add("unary", rf"(?<![\w)\]}}.,%{MARKS}])(?P<s>[±+])(?=\d)",
            lambda m: (self.L.w("pm" if m.group("s") == "±" else "plus") + " ", m.end()))
        # 10. fractions
        # 1½ and 1 ½ (a space before the glyph is common in recipes) are both mixed numbers
        add("vulgar", rf"(?P<sg>(?<![\w)\]}}.,{MARKS}])[-−](?=\d*[ \t]?[½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘]))?(?:(?P<w>\d+)[ \t]?)?(?P<v>[½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘])"
                      r"(?P<pct>[ \t]?[%٪])?" + utail, self.h_vulgar, suffix=True)
        add("allday", r"(?<![\d/.,])24\s?[/x×]\s?7(?![\d/]|\.\d)",
            lambda m: None if self._math_line(m) else (f"{self.L.say_int(24)} {self.L.say_int(7)}", m.end()),
            suffix=True)
        add("frac", rf"(?<![\d/.,])(?<!/[ \t])(?P<sg>{SIGN})(?P<a>\d+(?:\.\d+)?)\s?/\s?(?P<b>\d+(?:\.\d+)?)(?![\d]|\s?/\s?\d|\.\d)(?P<pct>[ \t]?[%٪])?" + utail,
            self.h_frac, suffix=True)
        # 11. ratio  a:b (not a time)
        add("ratio", r"(?<![\d:.])(?P<a>\d+(?:\.\d+)?)\s?:\s?(?P<b>\d+(?:\.\d+)?)(?![\d:]|\.\d)", self.h_ratio, suffix=True)
        # 12. English ordinal suffixes
        add("ord_en", r"(?<![\d.,])(?P<n>\d+)(?P<s>st|nd|rd|th|ST|ND|RD|TH)(?![A-Za-z])", self.h_ord_en, suffix=True)
        # 13. multi-dot numbers (IP / versions)
        add("multidot", r"(?<![\d.])\d+(?:\.\d+){2,}(?![\d]|\.\d)", self.h_multidot)
        # 14. hash / No. / & / hyphen between letters and digits
        add("hashnum", r"(?<![\w#&])#(?=\d)|(?<![A-Za-z])(?:No|no|NO|Nos)\.\s?(?=\d)",
            lambda m: (self.L.w("number_word") + " ", m.end()))
        add("amp", r"(?<=\s)&(?=\s)", lambda m: (self.L.w("and"), m.end()))
        add("alnum_hyphen", r"(?<=[A-Za-z])-(?=\d)|(?<=\d)-(?=[A-Za-z])", self.h_alnum_hyphen)
        if self.L.letters:  # 5 किलो-3 किलो=2 किलो: a hyphen after a written native quantity on a maths line
            add("native_minus", rf"(?<=[{self.L.letters}{MARKS}.])-(?=[ \t]*\d)", self.h_native_minus)
        # 15. plain numbers and ranges
        add("range", rf"(?P<a>{SIGN}{NUM})(?P<s1>\s?)(?P<dash>[-–—])(?P<s2>\s?)(?P<b>{RNUM})(?![\d]|[-–—/:]\d|\.\d)",
            self.h_range, suffix=True)
        add("number", rf"(?P<q>{SIGN}{NUM})", self.h_number, suffix=True)
        # 16. abbreviations
        abbr = {**ABBR_EN, **(L.w("abbr_native", {}) or {})}
        self._abbr = abbr
        A = "|".join(re.escape(a) for a in sorted(abbr, key=len, reverse=True))
        add("abbr", rf"(?<![\w.])(?P<a>{A})(?=\s|$|[,;:!?)\]])", self.h_abbr)
        return R

    def _letters_rx(self):
        return f"[{self.L.letters}]" if self.L.letters else r"(?!x)x"

    # ------------------------------------------------------------ handlers (return (text, end) or None)
    def h_number(self, m):
        q = m.group("q")
        s, a, e = m.string, m.start(), m.end()
        before, after = s[a - 1:a], s[e:e + 1]
        lat_b, lat_a = before.isascii() and before.isalpha(), after.isascii() and after.isalpha()
        digits = q.lstrip("-−")
        if (lat_b or lat_a) and digits.isdigit():
            # inside an identifier (PAN ABCDE1234F, MH12AB1234): letters on both sides or 4+ digits
            if (lat_b and lat_a) or len(digits) >= 4:
                return self.L.say_digits(digits), e
            return self.say_num(q), e
        # a word after the number makes it a count ("15 करोड़ लोग", "7000000000 records"), except 10+ plain digits
        # that are not round: those are IDs or phone numbers (মোবাইল নম্বৰ 69886799099)
        id_like = re.fullmatch(r"\d{10,}", q) and len(q) - len(q.rstrip("0")) < len(q) // 2
        count = bool(re.match(rf" [{self.L.letters}A-Za-z]", self._text[e:e + 2])) and not id_like
        return self.say_num(q, year_ok=self._year_ctx(s, a, e), count=count), e

    def _year_ctx(self, s, a, e):
        """A bare 4-digit number is read as a year only with a year cue around it ("in 1998", "1990s")."""
        L = self.L
        if not getattr(L, "year_style", False):
            return False
        pre, post = L.w("year_before", ""), L.w("year_after", "")
        if pre and re.search(rf"(?:{pre})[ \t]*$", s[max(0, a - 40):a]):
            return True
        return bool(post and re.match(rf"(?:{post})", s[e:e + 24]))

    def h_range(self, m):
        L = self.L
        spaced = bool(m.group("s1") or m.group("s2"))
        a, b = m.group("a"), m.group("b")
        s = m.string
        nxt = s[m.end():].lstrip(" \t")[:1]
        prv = s[:m.start()].rstrip(" \t")[-1:]
        if m.group("dash") == "-" and ((nxt and nxt in OP_CHARS) or (prv and prv in OP_CHARS)):
            return f"{self.say_num(a)} {L.w('minus')} {self.say_num(b)}", m.end()  # 10-3=7
        if spaced and m.group("dash") == "-" and self._math_line(m):
            return None
        if re.fullmatch(r"\d{4}", a) and re.fullmatch(r"\d{2}", b) and 1900 <= int(a) <= 2099 \
                and int(b) == (int(a) + 1) % 100:  # FY 2025-26, 1999-00: second year is abbreviated
            ya, yb = int(a), (int(a) // 100 + (int(b) == 0)) * 100 + int(b)
            say = L.year if getattr(L, "year_style", False) else L.say_int
            return L.fill(L.w("range"), a=say(ya), b=say(yb)), m.end()
        years = bool(re.fullmatch(r"\d{4}", a) and re.fullmatch(r"\d{4}", b) and 1100 <= int(a) < int(b) <= 2099
                     and int(b) - int(a) <= 100) or self._year_ctx(s, m.start(), m.end())
        return L.fill(L.w("range"), a=self.say_num(a, year_ok=years), b=self.say_num(b, year_ok=years)), m.end()

    @staticmethod
    def _cue_before(m, rx):
        return bool(rx.search(m.string, max(0, m.start() - 40), m.start()))

    def _math_line(self, m):
        """maths symbols in the same clause: from the previous sentence end (. ? ! । followed by a space) or line
        break to the next one. "24/7 support. 2+2=4" keeps 24/7 as a phrase."""
        s = m.string
        ls = 0
        for b in SENT_END.finditer(s, 0, m.start()):
            ls = b.end()
        nb = SENT_END.search(s, m.end())
        line = s[ls: nb.start() if nb else len(s)]
        return bool(MATH_CONTEXT.search(line))

    def h_url(self, m):
        L = self.L
        s = m.group(0)
        s = re.sub(r"^(?:https?|ftp)://", "", s)
        out = []
        sym = {".": L.w("dot"), "/": L.w("slash"), "@": L.w("at"), "-": L.w("hyphen"), "_": L.w("underscore"),
               ":": L.w("colon"), "?": L.w("question"), "=": L.w("equals"), "&": L.w("and"), "#": L.w("hash"),
               "+": L.w("plus"), "%": L.w("percent_word"), "~": L.w("tilde"), ";": L.w("semicolon", ""),
               ",": L.w("comma", ""), "!": L.w("exclamation", ""), "*": L.w("asterisk", ""), "$": L.w("dollar", "")}
        for tok in _url_tokens(s):
            if tok.isdecimal():
                out.append(L.say_digits(tok) if (len(tok) > 4 or tok[0] == "0") else L.say_int(int(tok)))
            elif tok in sym and sym[tok]:
                out.append(sym[tok])
            elif tok.strip():
                out.append(tok)  # letters, and any symbol we have no word for: never silently dropped
        return " ".join(out), m.end()

    def _read_groups(self, groups):
        L = self.L
        return L.comma.join(L.say_digits(g) for g in groups)

    def h_phone(self, m):
        L = self.L
        raw = m.group(0)
        plus = raw.startswith("+")
        groups = split_groups(raw)
        digits = "".join(groups)
        if not 8 <= len(digits) <= 15:
            return None
        if not plus and len(groups) == 1 and digits.endswith("00000"):
            return None  # 7000000000 records: a round quantity, not a phone number
        if not plus and self._quantity_after.match(m.string, m.end()) and not self._cue_before(m, self._phone_cue):
            return None  # 9876543210 INR, 9876543210 kg: an amount, read by the money / unit rules
        if len(groups) == 1 or (len(groups) == 2 and groups[0] in ("0", "91") and len(groups[1]) == 10):
            core = groups[-1]
            groups = groups[:-1] + group_digits(core)
        words = self._read_groups(groups)
        if plus:
            words = f"{L.w('phone_plus', '') or L.w('plus')} {words}"  # +91: the spoken 'plus', not the maths word
        return words, m.end()

    def h_code(self, m):
        num = m.group("num")
        if sum(c.isdigit() for c in num) < 3:
            return None
        written = split_groups(num)
        groups = written if len(written) > 1 else group_digits(written[0])
        return self._orig(m, m.start(), m.start("num")) + self._read_groups(groups), m.end()

    def h_code_bare(self, m):
        num = m.group("num")
        groups = [num] if len(num) <= 4 else group_digits(num)
        return self._read_groups(groups), m.end()

    def _orig(self, m, a, b):
        return self._text[a:b]

    @staticmethod
    def _valid_date(d, mo, y):
        if not 1 <= mo <= 12:
            return False
        yy = y if y >= 100 else 2000 + y
        return 1 <= d <= calendar.monthrange(yy, mo)[1]

    def h_date_num(self, m):
        d, mo, y = int(m.group("d")), int(m.group("m")), m.group("y")
        sep = m.group("sep").strip(" \t")
        if m.group("sep2").strip(" \t") != sep:
            return None  # 15/08-2025: mixed separators are not one date
        if sep != m.group("sep") and (len(y) != 4 or self._math_line(m)):
            return None  # "15 / 08 / 2025" is a date; "6 / 3 / 2" is division
        if sep == "." and len(y) == 2 and not self._cue_before(m, self._date_label):
            return None  # 1.2.34 is more likely a version than a date; "DOB: 15.08.25" is a date
        day_first = m.start("d") < m.start("y")
        if not self._valid_date(d, mo, int(y)):
            if day_first and len(y) == 4 and self._valid_date(mo, d, int(y)) and mo > 12:
                d, mo = mo, d  # mm/dd/yyyy
            else:  # 29/02/2025: not a real date, read what is written
                L = self.L
                sw = {"/": L.w("slash"), ".": L.w("dot"), "-": L.w("hyphen")}[sep]
                order = ("d", "m", "y") if m.start("d") < m.start("y") else ("y", "m", "d")
                parts = [m.group(k) for k in order]
                return f" {sw} ".join(self.say_num(p) for p in parts), m.end()
        return self._say_date(d, mo, int(y), len(y)), m.end()

    def _say_date(self, d, mo, y, ylen=4, month=None):
        L = self.L
        month = month or L.w("months")[mo - 1]
        if y is None:
            return L.fill(L.w("date_dm"), d=L.date_day(d), month=month)
        if ylen == 2:
            yy = L.say_digits(f"{y:02d}") if y < 10 else L.say_int(y)
        else:
            yy = L.year(y)
        if d is None:
            return L.fill(L.w("date_my"), month=month, y=yy)
        return L.fill(L.w("date"), d=L.date_day(d), month=month, y=yy)

    def h_date_mon(self, m):
        gd = m.groupdict()
        L = self.L
        written = None
        if gd.get("nmon"):  # native month name (अगस्त, ಆಗಸ್ಟ್): keep the spelling the writer used
            written = gd["nmon"]
            mon = self._nmon[unicodedata.normalize("NFC", written)]
        else:
            mon = MONTHS_EN[m.group("mon").lower().rstrip(".")]
            if m.group("mon") == "may" and not gd.get("y"):
                return None  # lowercase "may" without a year is the verb
        d = int(gd["d"]) if gd.get("d") else None
        y = int(gd["y"]) if gd.get("y") else None
        if d is not None and not self._valid_date(d, mon, y if y is not None else 2024):
            if not 1 <= d <= 31:
                return None
            # 29 February 2025, 31 April: not a real date. Read what is written, in written order.
            month = written or L.w("months")[mon - 1]
            parts = [(m.start("d"), self.say_num(gd["d"])), (m.start("nmon" if written else "mon"), month)]
            if y is not None:
                parts.append((m.start("y"), self.say_num(gd["y"])))
            return " ".join(w for _, w in sorted(parts)), m.end()
        return self._say_date(d, mon, y, month=written), m.end()

    def h_time(self, m):
        L = self.L
        gd = m.groupdict()
        h = int(gd["h"])
        mi = int(gd["m"]) if gd.get("m") else 0
        s = int(gd["s"]) if gd.get("s") else None
        ap = gd.get("ap")
        absorb = L.w("time_absorb", ()) or ()
        if gd.get("sep") == "." and not ap:
            hw = absorb and re.match(rf"[ \t]?(?:{'|'.join(map(re.escape, absorb))})", m.string[m.end():])
            if not hw:
                return None  # 10.30 alone is a decimal; "1.30 ಗಂಟೆಗೆ" is a time
        if not ap and gd.get("sep") == ":" and self._cue_before(m, self._ratio_cue):
            return None  # "Ratio 12:30" -> ratio rule
        end = m.end()
        tz, tz_words = gd.get("tz"), ""
        if tz:
            tz_words = L.w(f"tz_{tz}", "")
            if not tz_words:  # no word for the zone: leave "IST" in the text as written
                end = m.start("tzsp")
        tail = ""
        if ap:
            if not 1 <= h <= 12:
                return None
            if gd["ap"].endswith(".") and re.match(r"\s*(?:$|\n|[A-Z])", m.string[end:]):
                tail = "."  # "at 10 a.m. The" - the dot also ended the sentence
            ap = "am" if ap[0] in "Aa" else "pm"
        if absorb:  # "10:30 बजे" / "10:30 ಗಂಟೆಗೆ": the hour word is already in our reading
            am = re.match(rf"\s?(?:{'|'.join(map(re.escape, absorb))})(?![{L.letters}])" if not L.glue_unknown_suffix
                          else rf"\s?(?:{'|'.join(map(re.escape, absorb))})", m.string[end:])
            if am:
                end += am.end()
        try:
            words = L.say_time(h, mi, s, ap)
        except MissingWord:  # no clock template: read the numbers plainly, never as a ratio
            if ap:
                try:  # a daypart word is missing: keep the clock reading, AM/PM stays as written
                    return L.say_time(h, mi, s, None), m.start("ap") - (1 if m.string[m.start("ap") - 1] in " \t" else 0)
                except MissingWord:
                    pass
            parts = [L.say_int(h)] + [self.say_num(x) for x in (gd.get("m"), gd.get("s")) if x and int(x)]
            words = " ".join(parts)
            # the AM/PM, hrs or zone text stays as written after the numbers
            return words, m.end("s") if gd.get("s") else (m.end("m") if gd.get("m") else m.end("h"))
        case = L.w("time_absorb_case", {}) or {}
        if case:  # "10:30 గంటలకు" -> "... ముప్పై నిమిషాలకు": the case ending moves to the last word
            cm = re.match(rf"[ \t]?({'|'.join(map(re.escape, sorted(case, key=len, reverse=True)))})(?![{L.letters}])",
                          m.string[end:])
            if cm:
                words, end = L.attach(words, case[cm.group(1)]), end + cm.end()
        elif absorb and not L.glue_unknown_suffix:
            sm = re.match(rf"[ \t]?(?:{'|'.join(map(re.escape, absorb))})([{L.letters}]+)", m.string[end:])
            if sm:  # the clock word with a case ending: the ending joins our reading (সাত বজাত)
                words, end = L.attach(words, sm.group(1)), end + sm.end()
        if tz_words:
            words += " " + tz_words
        return words + tail, end

    def h_money(self, m):
        L = self.L
        cur_tok = m.group("cur")
        cur = CURRENCY_PRE.get(cur_tok) or CURRENCY_POST.get(cur_tok) or (L.w("currency_native", {}) or {}).get(cur_tok)
        if cur is None:
            return None
        q = m.group("q")
        sc = m.group("sc")
        neg = bool(m.groupdict().get("neg"))
        if q[:1] in "-−":
            neg, q = not neg, q[1:]
        if q.replace(",", "").count(".") and q.endswith("."):
            return None
        rng = re.fullmatch(rf"({SIGN}{NUM})\s?[-–—]\s?({RNUM})", q)
        scale_word = self._scale_word(sc) if sc else None
        if sc and scale_word is None:
            return None
        if m.groupdict().get("e"):  # INR 1.2e6
            if rng or sc:
                return None
            out = L.say_money(cur, amount_words=self._sci_words(q, m.group("e")))
            return (f"{self.neg_word()} {out}" if neg else out), m.end()
        more = self._scale_components(m.groupdict().get("more"), sc)
        if more is None:
            return None
        if not rng and not sc:
            ip, fp = self._num_value(q)
            if 1 <= len(fp) <= 2:  # ₹1.5 = one rupee fifty paise; ₹1.05 = one rupee five paise
                main, sub = int(ip or 0), int(fp.ljust(2, "0"))
                try:
                    return L.say_money(cur, main=main, sub=sub, neg=neg,
                                       main_words=self.say_num(q.split(".")[0], count=True) if main else None), m.end()
                except MissingWord:
                    pass  # no word for the minor unit: read a decimal amount with the main currency
        amount = self.say_qty(q, math=self._local_sum(m), count=True)  # more than two decimals: read as a decimal amount, never rounded
        if scale_word:
            amount = L.fill(L.w("scale_tpl", "{x} {s}"), x=amount, s=scale_word, _noadj="." in q)
            for qq, ww in more:
                amount += " " + L.fill(L.w("scale_tpl", "{x} {s}"), x=self.say_num(qq, count=True), s=ww)
        one = self._is_one(q) and not sc
        out = L.say_money(cur, amount_words=amount, one=one, noadj="." in q)
        return (f"{self.neg_word()} {out}" if neg else out), m.end()

    def _scale_components(self, more, first):
        """'₹1 crore 25 lakh' -> [('25', 'lakh word')]; None unless the scales strictly descend."""
        if not more:
            return []
        out, last = [], self._scale_value(first)
        for qq, sc in re.findall(rf"(\d+(?:\.\d+)?)[ \t]?({self._scale_rx})", more):
            v, w = self._scale_value(sc), self._scale_word(sc)
            if v is None or last is None or v >= last or w is None:
                return None
            out.append((qq, w))
            last = v
        return out

    def _scale_value(self, sc):
        native = self.L.w("scale_native", {}) or {}
        key = LATIN_SCALES.get(sc) or LATIN_SCALES.get(sc.rstrip("."))
        if key:
            return SCALE_VALUE[key]
        for k in ("thousand", "lakh", "crore", "million", "billion", "trillion"):
            if sc in native and self.L.w(f"scale_{k}", "") == sc:
                return SCALE_VALUE[k]
        return None

    def _sci_words(self, mant, exp):
        L = self.L
        power = L.fill(L.w("power"), n=self.say_num(exp.lstrip("+")))
        ten = L.say_int(10)
        ten = ten + power[1:] if power.startswith("+") else f"{ten} {power}"  # Nepali दसको तीन घात
        return f"{self.say_num(mant)} {L.w('times')} {ten}"

    def _scale_word(self, sc):
        L = self.L
        native = L.w("scale_native", {}) or {}
        if sc in native:
            return sc  # already a native word, keep it
        key = LATIN_SCALES.get(sc) or LATIN_SCALES.get(sc.rstrip("."))
        return L.w(f"scale_{key}") if key else None

    def h_percent(self, m):
        L = self.L
        x = self.say_qty(m.group("q"), math=self._local_sum(m), count=True)
        if m.groupdict().get("p") == "‰":  # per mille is a tenth of a percent: never read it as percent
            tpl = L.w("permille", "")
            return (L.fill(tpl, x=x), m.end()) if tpl else None
        one = self._is_one(m.group("q")) and L.w("percent_one", "")
        return L.fill(one or L.w("percent"), x=x, _noadj="." in m.group("q")), m.end()

    def unit_phrase(self, key, one):
        """'MB' -> megabytes; 'Mbit/sec' or MB + /s -> megabits per second."""
        L = self.L
        key, _, per = key.partition("/")
        word = L.unit_word(key, one=one)
        if word is None and key == "ton":
            word = L.unit_word("tonne", one=one)  # languages with one word for both
        if word is None:
            return None
        if per:
            pw = L.unit_word(per, one=True)
            if pw is None:
                return None
            word = L.fill(L.w("per", "{u} per {p}"), u=word, p=pw)
        return word

    @staticmethod
    def _clipped(u, end, word, text):
        """a clipped native unit word with a case ending stays as written: 2 கிலோவுக்கு, not கிலோகிராம்வுக்கு"""
        if word and not u.isascii() and word != u and word.startswith(u) and end < len(text) \
                and re.match(rf"[{MARKS}]", text[end]):
            return u
        return word

    def h_unit(self, m):
        L = self.L
        key = self._units[m.group("u") or m.group("u2")]
        if m.group("per"):
            if "/" in key:
                return None
            key = f"{key}/{PER_UNITS[m.group('per')]}"
        word = self._clipped(m.group("u") or m.group("u2"), m.end(),
                             self.unit_phrase(key, one=self._is_one(m.group("q"))), m.string)
        if word is None:
            return None
        x = self.say_qty(m.group("q"), math=self._local_sum(m), count=True)
        if "{x}" in word:  # a rate read around the number: గంటకు అరవై కిలోమీటర్లు
            return L.fill(word, x=x, _noadj="." in m.group("q")), m.end()
        ax = x if "." in m.group("q") else L.adj(x)  # 2.1 kg: the last digit keeps its counting form
        tpl, sp = L.w("unit_tpl", "{x} {u}"), m.group("usp") or " "
        if tpl == "{x} {u}":  # keep the spacing the writer used ("10  km" -> "ten  kilometres")
            return ax + sp + word, m.end()
        return L.fill(tpl, x=x, u=word, _noadj="." in m.group("q")), m.end()

    def h_root(self, m):
        key = {"√": "root", "∛": "cuberoot", "∜": "fourthroot"}[m.group("r")]
        return self.L.w(key) + " ", m.end()

    def h_sup(self, m):
        L = self.L
        gd = m.groupdict()
        e = gd.get("e") or "".join(SUPERSCRIPTS[c] for c in gd["sup"])
        if e == "2":
            word = L.w("squared")
        elif e == "3":
            word = L.w("cubed")
        else:
            ev = self.say_num(e) if e.lstrip("-−").isdecimal() else e
            word = L.fill(L.w("power"), n=ev)
        if word.startswith("+"):  # glued postposition (Nepali को): attach to the base word
            return GLUE + word[1:], m.end()
        return f" {word}", m.end()

    def h_vehicle(self, m):
        L = self.L
        parts = re.findall(r"[A-Z]+|\d+", m.group(0))
        return " ".join(p if p.isalpha() else L.say_digits(p) for p in parts), m.end()

    def h_duration(self, m):
        """1h 30m -> one hour thirty minutes: the hour part makes m mean minutes, not metres"""
        L = self.L
        out = []
        for g, key in (("h", "hr"), ("m", "min"), ("s", "sec")):
            v = m.group(g)
            if v is None:
                continue
            u = self.unit_phrase(key, one=int(v) == 1)
            if u is None:
                return None
            x = L.say_int(int(v))
            tpl = L.w("unit_tpl", "{x} {u}")
            out.append(L.adj(x) + " " + u if tpl == "{x} {u}" else L.fill(tpl, x=x, u=u))
        return " ".join(out), m.end()

    @staticmethod
    def _eq_in_clause(s, a, b):
        """an '=' in the clause around s[a:b]"""
        head = CLAUSE_END.split(s[max(0, a - 120):a])[-1]
        tail = CLAUSE_END.split(s[b:b + 120], 1)[0]
        return "=" in head or "=" in tail

    @staticmethod
    def _emphasis_star(s, i):
        """True when the * at i opens or closes a markdown italic span (*cup*, *2 cups*) on its line"""
        a = s.rfind("\n", 0, i) + 1
        b = s.find("\n", i)
        b = len(s) if b < 0 else b
        for em in EMPHASIS.finditer(s, a, b):
            k = len(em.group("d"))
            if em.start() <= i < em.start() + k or em.end() - k <= i < em.end():
                return True
        return False

    def h_op(self, m):
        L = self.L
        op = m.group("op")
        if not self._operand_before.search(m.string, max(0, m.start() - 64), m.start()):
            return None
        nxt = m.string[m.end():m.end() + 1]
        if nxt and not re.match(OPERAND_R, nxt) and not re.search(r"\d", m.string[max(0, m.start() - 24):m.start()]):
            return None  # a native word on the right is an operand only after a written quantity: राम+श्याम stays
        s1, s2 = m.string[m.start() - 1] in " \t", m.group("s2")
        if op in "<>" and not (s1 and s2.strip(" \t") == "" and s2):
            before = m.string[m.start() - 1]
            after = m.string[m.end()] if m.end() < len(m.string) else ""
            if not (before.isdigit() and after.isdigit()):
                return None
        if op in "-/" and not self._math_line(m):
            return None  # "a - b", "6 / 3" outside maths: a dash or a slash, not an operator
        if op in "-/" and not s1 and (re.match(rf"[{VULGAR_CHARS}]", m.string[m.start() - 1])
                                      or re.match(rf"[{VULGAR_CHARS}]", m.string[m.end():m.end() + 1])) \
                and not self._eq_in_clause(m.string, m.start(), m.end()):
            return None  # ½/¾-inch adapter + 2 washers: a compact fraction slash or dash needs an "="
        if op == "-" and not s1 and not re.match(r"[\d)\]]", m.string[m.start() - 1]) and not re.search(
                rf"(?:[\d{VULGAR_CHARS}][ \t]*(?:%|[^\W\d_][\w{MARKS}]*)|(?<![\w{MARKS}])[^\W\d_])$",
                m.string[max(0, m.start() - 40):m.start()]):
            return None  # 10 kg-(4 kg+2 kg)=4 kg, x-(4+2)=0: before a bracket a number, a quantity or a variable
        if op == "*" and self._emphasis_star(m.string, m.start()):
            return None  # markdown italics: Add ½ *cup* of sugar
        if op == "*" and not (s1 or s2) and not re.match(rf"[\d{VULGAR_CHARS}]", m.string[m.start() - 1]):
            return None
        return ("" if s1 else " ") + L.w(MATH_OPS[op]) + (s2 or " "), m.end()

    def h_vulgar(self, m):
        L = self.L
        a, b = VULGAR[m.group("v")]
        frac = self._frac_or_none(a, b)
        if not m.group("w") and frac is None:
            raise MissingWord(f"{L.name}: fraction")
        if m.group("w"):
            mixed = getattr(L, "mixed_fraction", None)
            special = mixed(int(m.group("w")), a, b) if mixed and not m.group("w").startswith("0") else None
            words = special or self._mixed_template(m.group("w"), a, b, frac)
        else:
            words = frac
        words = self._fraction_tail(m, words, one=not m.group("w"))
        return (self._signed(m, words), m.end()) if words is not None else None

    def _mixed_template(self, whole, a, b, frac):
        """2¼ with the language's mixed-number template; a language without one reads the value as a decimal when
        it ends within three places (Manipuri 2¼ -> two point two five), else the rule is dropped"""
        L = self.L
        if L.has("mixed_fraction") and frac is not None:
            return L.fill(L.w("mixed_fraction"), x=self.say_num(whole), f=frac)
        q = a * 1000 // b
        if q * b != a * 1000:
            raise MissingWord(f"{L.name}: mixed_fraction")
        return L.say_decimal(whole, f"{q:03d}".rstrip("0"))

    def _frac_or_none(self, a, b):
        try:
            return self.L.say_fraction(a, b)
        except MissingWord:
            return None

    def _fraction_tail(self, m, words, one):
        """percent or unit after a fraction: 2½% -> ... percent; 1/2 kg -> one half kilogram (a proper fraction
        takes the singular unit)"""
        if m.group("pct"):
            if m.group("u"):
                return None
            return self.L.fill(self.L.w("percent"), x=words)
        return self._with_unit(m, words, one=one)

    def h_frac(self, m):
        L = self.L
        a, b = m.group("a"), m.group("b")
        if "." in a or "." in b:  # 1/2.5: a division, never a special fraction or a date
            if float(b) == 0:
                return None
            w = self._fraction_tail(m, L.fill(L.w("fraction"), a=self.say_num(a), b=self.say_num(b)), one=False)
            return (self._signed(m, w), m.end()) if w is not None else None
        if int(b) == 0:
            return None
        tailed = bool(m.group("pct") or m.group("u"))
        if tailed:
            w = self._fraction_tail(m, L.say_fraction(int(a), int(b), a_words=self.say_num(a), b_words=self.say_num(b)),
                                    one=int(a) < int(b))
            return (self._signed(m, w), m.end()) if w is not None else None
        # 15/08 (leading-zero month, day-like numerator) or "Date: 15/8" is a date without a year
        if m.group("sg"):
            return self._signed(m, L.say_fraction(int(a), int(b), a_words=self.say_num(a), b_words=self.say_num(b))), m.end()
        if self._valid_date(int(a), int(b), 2024) and not self._math_line(m) and \
                ((len(b) == 2 and b[0] == "0") or self._cue_before(m, self._date_label)):
            return self._say_date(int(a), int(b), None), m.end()
        return L.say_fraction(int(a), int(b), a_words=self.say_num(a), b_words=self.say_num(b)), m.end()

    def _with_unit(self, m, words, one=False, noadj=False):
        """optional unit after a structured number (2 1/2 kg, 1.2e-3 kg); None if the unit has no word"""
        if not m.group("u"):
            return words
        key = self._units.get(m.group("u")) or UNIT_ALIASES.get(m.group("u"), "")
        if m.groupdict().get("uper"):  # 1e3 MB/s
            if "/" in key:
                return None
            key = f"{key}/{PER_UNITS[m.group('uper')]}"
        unit = self._clipped(m.group("u"), m.end(), self.unit_phrase(key, one=one), m.string)
        if unit is None:
            return None
        if "{x}" in unit:  # a rate read around the number: 2½ km/h -> గంటకు రెండున్నర కిలోమీటర్లు
            return self.L.fill(unit, x=words, _noadj=noadj)
        tpl = self.L.w("unit_tpl", "{x} {u}")
        if tpl == "{x} {u}":  # keep the writer's spacing: "-1.2e-3  kg" -> "... three  kilograms"
            return (words if noadj else self.L.adj(words)) + (m.group("usp") or " ") + unit
        return self.L.fill(tpl, x=words, u=unit, _noadj=noadj)

    def _signed(self, m, words):
        return f"{self.neg_word()} {words}" if (m.group("sg") or "") else words

    def h_mixed(self, m):
        L = self.L
        whole, a, b = int(m.group("w")), int(m.group("a")), int(m.group("b"))
        if not 0 < a < b or m.group("w").startswith("0"):
            return None
        mixed = getattr(L, "mixed_fraction", None)
        words = mixed(whole, a, b) if mixed else None
        if not words:
            words = self._mixed_template(m.group("w"), a, b, self._frac_or_none(a, b))
        words = self._with_unit(m, words)
        return (self._signed(m, words), m.end()) if words is not None else None

    def h_sci(self, m):
        L = self.L
        words = self._sci_words(m.group("m"), m.group("e"))
        if m.group("pct"):  # 1e3%
            words = L.fill(L.w("percent"), x=words, _noadj=True)
        words = self._with_unit(m, words, noadj=True)  # 2e1 km/h: the exponent keeps its digit name
        return (self._signed(m, words), m.end()) if words is not None else None

    def h_scaled(self, m):
        sc = m.group("sc") or "k"
        word = self._scale_word(sc)
        if word is None:
            return None
        x = self.say_qty(m.group('q'), math=self._local_sum(m), count=True)
        words = self._with_unit(m, self.L.fill(self.L.w("scale_tpl", "{x} {s}"), x=x, s=word, _noadj="." in m.group("q")))
        return (words, m.end()) if words is not None else None

    def h_decade(self, m):
        n = int(m.group("y"))
        if n in (10, 100, 1000):
            words = {10: "tens", 100: "hundreds", 1000: "thousands"}[n]
        else:
            w = self.L.year(n) if 1100 <= n <= 2099 else self.L.say_int(n)
            words = w[:-1] + "ies" if w.endswith("y") else w + "s"
        return words, m.end()

    def h_alnum_hyphen(self, m):
        s, a = m.string, m.start()
        if s[a - 1:a].isalpha() and not s[a - 2:a - 1].isalpha() and self._math_line(m):
            return f" {self.L.w('minus')} ", m.end()  # x-3=7
        um = re.search(r"\d[ \t]*([A-Za-z]+)$", s[max(0, a - 16):a])
        if um and um.group(1) in self._units and self._math_line(m):
            return f" {self.L.w('minus')} ", m.end()  # 5 kg-3 kg=2 kg: the left operand is a quantity
        return " ", m.end()  # COVID-19, A-1: the hyphen is not read

    def _native_qty_rx(self):
        rx = getattr(self, "_nq_rx", None)
        if rx is None:
            L, words = self.L, set()
            for lex in [L.lex] + [o.lex for o in (L.registry.get(f) for f in L.fallback) if o is not None]:
                for k, v in lex.items():
                    if k.startswith(("u_", "cur_", "sub_")):
                        for x in (v if isinstance(v, tuple) else (v,)):
                            if isinstance(x, str) and "{" not in x:
                                words.add(x)
                    elif k in ("unit_abbr", "currency_native", "qty_words") and isinstance(v, (dict, tuple)):
                        words.update(v)
            words = [w for w in words if w and re.search(f"[{L.letters}]", w)]
            alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) or "(?!)"
            qty = rf"\d[ \t]*(?:[{L.letters}{MARKS}]+[ \t]+){{0,2}}(?:{alt})\.?"
            rx = self._nq_rx = re.compile(qty + "$")
            self._nq_pre = re.compile(rf"{SUM_BEFORE}[\d.,]*{qty}(?:[ \t]*-[ \t]*[\d.,]*{qty})*$")
            lat = "|".join(re.escape(u) for u in sorted(self._units, key=len, reverse=True) if re.fullmatch(r"[A-Za-z°µ/²³]+", u))
            self._nq_one = re.compile(rf"(?P<q>{NUM})(?P<rest>[ \t]*(?:[{L.letters}{MARKS}]+[ \t]+){{0,2}}(?:{alt})\.?)(?![{L.letters}{MARKS}])")
            self._nq_fwd = re.compile(rf"[ \t]*[\d.,]*(?:{qty}|\d[ \t]?(?:{lat or '(?!)'})(?![A-Za-z]))")  # 5 लीटर-500 ml=4.5 लीटर
        return rx

    def h_native_minus(self, m):
        """5 किलो-3 किलो=2 किलो: a hyphen after a written native quantity is minus only when the sum is local, as
        for typed endpoints (_typed_sum). "वजन = 5 किलो- 10 किलो प्रति दिन" and "…; 2+3=5" keep the hyphen."""
        s, a = m.string, m.start()
        rx = self._native_qty_rx()
        w = s[max(0, a - 120):a]
        if not rx.search(w):
            return None  # ಕೋವಿಡ್-19 (also after "5 ಕೋವಿಡ್"): a word hyphen, read as written
        pre = bool(self._nq_pre.search(w))  # x = 5 किलो-3 किलो, also for each later hyphen of the chain
        e, local = m.end(), False
        while True:
            q = self._nq_fwd.match(s, e)
            if not q:
                break
            e = q.end()
            if self._op_after(s, e):
                local = True
                break
            d = NATIVE_CHAIN_DASH.match(s, e)
            if not d:
                break
            e = d.end()
        if local or (pre and not WORD_AFTER.match(s, e)):
            sp = "" if s[m.end():m.end() + 1] in (" ", "\t") else " "
            return f" {self.L.w('minus')}{sp}", m.end()
        return None

    def h_ratio(self, m):
        L = self.L
        return L.fill(L.w("ratio"), a=self.say_num(m.group("a")), b=self.say_num(m.group("b"))), m.end()

    def h_ord_en(self, m):
        return self.L.ordinal(int(m.group("n"))), m.end()

    def h_multidot(self, m):
        L = self.L
        parts = m.group(0).split(".")
        words = [L.say_digits(p) if (len(p) > 1 and p[0] == "0") else L.say_int(int(p)) for p in parts]
        return f" {L.w('dot')} ".join(words), m.end()

    def h_abbr(self, m):
        a, f, L = m.group("a"), m.string, self.L
        if m.start() and unicodedata.category(f[m.start() - 1])[0] in "LM":
            return None  # inside a word: the vowel sign or virama before it is not \w (Telugu కూడా., Bengali ঠান্ডা.)
        key = self._abbr[a]
        if key.startswith("abbr_"):
            word = L.w(key)
            if not word:
                return None
            title = key in TITLE_KEYS
        else:
            word = key  # native table maps straight to the expansion
            title = word == a.rstrip(".") or word in {L.lex.get(k) for k in TITLE_KEYS}
        rest = f[m.end():]
        if title and not re.match(r"[ \t]+\w", rest):
            return None  # a title needs the name after it; "Dr." at a line end is left as written
        return word, m.end()

    # ------------------------------------------------------------ suffixes
    def _take_suffix(self, f, end, words, value):
        L = self.L
        if not L.letters:
            return words, end
        sm = self._suffix_rx.match(f, end)
        if sm:
            suf = sm.group("s")
            if value is not None:
                o = L.ordinal_from_suffix(value, suf)
                if o is not None:
                    return o, sm.end()
            return L.attach(words, suf, value), sm.end()
        if L.detached_suffixes:
            dm = self._detached_rx.match(f, end)
            if dm:
                suf = dm.group("s")
                if value is not None:
                    o = L.ordinal_from_suffix(value, suf)
                    if o is not None:
                        return o, dm.end()
                return L.attach(words, suf, value), dm.end()
        return words, end

    # ------------------------------------------------------------ main loop
    def run(self, text: str, copy=None) -> str:
        """copy(a, b) gives the output for untouched text[a:b] (api.normalize passes one that restores
        the original spelling of whole tokens that were not in NFC)."""
        L = self.L
        copy = copy or (lambda a, b: text[a:b])
        f = fold_digits(text)
        self._state.text = text
        out = []
        i = j = 0  # i: start of text not yet emitted; j: where the next trigger search starts
        n = len(f)
        while j < n:
            t = self.trigger.search(f, j)
            if not t:
                break
            p = t.start()
            res = None
            for rule in self.rules:
                mm = rule.rx.match(f, p)
                if mm and mm.end() > p:
                    try:
                        r = rule.handler(mm)
                    except MissingWord:  # the language lacks a word this reading needs: try a plainer rule
                        r = None
                    if r is not None:
                        res = (r, rule, mm)
                        break
            if res is None:
                j = p + 1  # untouched: copied later as one run, so whole tokens keep their spelling
                continue
            (words, end), rule, mm = res
            grp = self._endpoint_group(rule, f, p, end)
            while grp:  # ₹5–₹10, 10:30–11:30, 5%-10%, ½ kg-1 kg: two typed endpoints joined by a dash
                dm = re.match(r"[ \t]*[–—-][ \t]*", f[end:])
                r2 = dm and self._endpoint_at(f, end + dm.end(), grp)
                if not r2:
                    break
                if end == mm.end():  # first join: a subtraction only when the sum is local, else a range
                    sub_ = dm.group(0).strip(" \t") == "-" and self._typed_sum(f, grp, rule, p, r2[1])
                if sub_:
                    # $5-$3-$1=$1; a language without a minus word keeps the written sign (Manipuri, Santali)
                    op = f" {L.w('minus')} " if L.has("minus") else dm.group(0)
                    words, end = f"{words}{op}{r2[0]}", r2[1]
                    continue  # only a subtraction chains
                words, end = self._fill_range(words, r2[0], rule, mm), r2[1]
                break
            if rule.suffix:
                value = None
                if rule.name in ("number", "ord_en"):
                    g = mm.group("q") if rule.name == "number" else mm.group("n")
                    if re.fullmatch(r"\d+", g or ""):
                        value = int(g)
                words, end = self._take_suffix(f, end, words, value)
                fem = L.lex.get("_ord_fem")
                if fem and f[end - len(fem["marker"]):end] == fem["marker"] and words.endswith(fem["end"][0]):
                    nm = re.match(r"[ \t]+([^\s.,،۔!?:;؛؟\"'’”)\]…]+)", text[end:])
                    if nm and nm.group(1) in fem["nouns"]:
                        words = words[: -len(fem["end"][0])] + fem["end"][1]
            words = self._drop_range_echo(words, text, end)
            obl = L.lex.get("oblique_before")
            if obl and self._obliquable(rule, mm):
                pm = re.match(rf"[ \t]+(?:{'|'.join(obl)})(?![{L.letters}])", text[end:])
                if pm:
                    words = self._oblique_phrase(words)
            if (rule.name in ("number", "range", "scaled") and re.match(rf" [{L.letters or 'A-Za-z'}]", text[end:end + 2])
                    and not re.search(r"\d\.\d", f[p:end])):  # 5.1 కోట్ల: a decimal's last digit keeps its digit name
                words = L.adj(words)  # "5 ಪುಸ್ತಕ", "1 పుస్తకం": number in front of a noun
            if end > p and f[end - 1] == "." and not words.endswith(".") and re.match(r"[ \t]*(?:\n|$)", f[end:]):
                words += "."  # a span ending in an abbreviation dot at a line end: the dot was also the full stop
            out.append(copy(i, p))
            if words.startswith(GLUE):
                words = words[1:]
                while out and not out[-1].rstrip(" \t"):
                    out.pop()
                if out:
                    out[-1] = out[-1].rstrip(" \t")
                out.append(words)
                i = j = end
                continue
            last = next((x for x in reversed(out) if x), None)  # the text actually emitted just before
            prev = last[-1] if last is not None else (text[p - 1] if p else "")
            if words and prev and _cat(prev) in "LMN" and _cat(words[0]) in "LMN":
                words = " " + words
            nxt = text[end:end + 1]
            if words and nxt and _cat(nxt) in "LMN" and _cat(words[-1]) in "LMN" and nxt not in SUPERSCRIPTS:
                words = words + " "
            out.append(words)
            i = j = end
        out.append(copy(i, n))
        return "".join(out)

    def _local_sum(self, m):
        """a range inside one span (₹500-1000, 5-10%, 5-10 kg) is a subtraction only when the sum is local, as
        for typed endpoints: "दैनिक बजट = ₹500-1000 प्रति दिन" and "$5-10 per day + meals" stay ranges."""
        s, p, e = m.string, m.start(), m.end()
        if self._op_after(s, e):
            return True
        return bool(re.search(SUM_BEFORE + "$", s[max(0, p - 30):p])) and not WORD_AFTER.match(s, e)

    def _endpoint_group(self, rule, f, p, end):
        """the rules a second range endpoint may come from, or None when this span is not a typed endpoint"""
        if rule.name in ("money_pre", "money_post"):
            names = ("money_pre", "money_post")
        elif rule.name in ("time", "time_h"):
            names = ("time", "time_h")
        elif rule.name in ("percent", "unit") or (rule.name in ("vulgar", "mixed", "frac") and self._has_tail(f[p:end])):
            names = ("percent", "unit", "vulgar", "mixed", "frac")
        elif rule.name == "vulgar" and re.match(rf"[–—-]\d*[ \t]?[{VULGAR_CHARS}]", f[end:]):
            names = ("vulgar",)  # ½-¾ cup: two bare fraction glyphs joined by a dash
        else:
            return None
        return [r for r in self.rules if r.name in names]

    def _has_tail(self, span):
        """½ kg, 1½%: a fraction with a unit or percent sign is a quantity endpoint; a bare ½ is not"""
        return bool(re.search(rf"[A-Za-z%٪{self.L.letters}]", span))

    def _endpoint_at(self, f, pos, grp):
        """(words, end) for a typed endpoint at pos, or None. A quantity endpoint may also be a number with a
        written native quantity word (वजन 5 kg-10 किलो); that word is kept as written."""
        for r in grp:
            m2 = r.rx.match(f, pos)
            if not m2 or m2.end() <= pos:
                continue
            if len(grp) > 1 and r.name in ("vulgar", "mixed", "frac") and not self._has_tail(f[pos:m2.end()]):
                continue
            try:
                res = r.handler(m2)
            except MissingWord:
                res = None
            if res is not None:
                return res
        if grp[0].name in ("percent", "unit", "vulgar", "mixed", "frac") and self.L.letters:
            self._native_qty_rx()
            nm = self._nq_one.match(f, pos)
            if nm:
                x, rest = self.say_num(nm.group("q"), count=True), self._text[nm.start("rest"):nm.end()]
                if "." not in nm.group("q") and re.match(r"[ \t]", rest):
                    x = self.L.adj(x)  # before the noun, like a lone number: ½ l-1 లీటరు -> ... ఒక లీటరు
                return f"{x}{rest}", nm.end()
        return None

    def _fill_range(self, a, b, rule, mm):
        """the range template; before a postposition the first endpoint's noun takes its oblique form
        (Hindi 1 hr-2 hr → एक घंटे से दो घंटे)"""
        L = self.L
        tpl = L.w("range")
        obl = L.lex.get("oblique_before")
        pm = re.match(r"\{a\}[ \t]+(\S+)", tpl)
        if obl and pm and pm.group(1) in obl and (self._obliquable(rule, mm) or rule.name == "vulgar"):
            a = self._oblique_phrase(a)  # ½-¾ कप -> आधे से तीन चौथाई कप
        return L.fill(tpl, a=a, b=b)

    def _drop_range_echo(self, words, text, end):
        """a range template that ends in a word (Malayalam {a} മുതൽ {b} വരെ) drops it when the writer wrote that
        word within the next two words: -5°C–-2°C വരെ, 5-10 ദിവസം വരെ"""
        tail = self._range_tail
        if tail is None or not words.endswith(" " + tail):
            return words
        nm = re.match(rf"(?:[ \t]+[^\s\d.,;:!?।॥۔]+){{0,2}}?[ \t]+{re.escape(tail)}(?![\w{MARKS}])", text[end:])
        return words[: -len(tail) - 1] if nm else words

    @staticmethod
    def _obliquable(rule, mm):
        """a quantity with a noun: money, units, durations, scale words, and fractions with a unit (½ hr में)"""
        return rule.name in OBLIQUE_RULES or (rule.name in ("vulgar", "frac", "mixed") and bool(mm.groupdict().get("u")))

    def _oblique_phrase(self, words):
        """the noun takes its oblique form, and so does an inflecting fraction word before it: आधा घंटा → आधे घंटे"""
        L = self.L
        head, sp, last = words.rpartition(" ")
        adj = L.lex.get("oblique_adj") or {}
        head = " ".join(adj.get(w, w) for w in head.split(" ")) if adj and head else head
        return head + sp + (adj.get(last) or L.oblique(last))

    @staticmethod
    def _op_after(s, e, clock=False):
        """right after a sum's last endpoint: '=', or another operator and operand with an '=' later in the
        same clause ($10-$4+$2=$8). "Delivery costs $5-$10 + $2 handling." is a range plus a charge. A clock
        difference needs the '=' (10:30-11:30 + 14:30-15:30 are two intervals)."""
        m = LOCAL_OP_AFTER.match(s, e)
        if not m:
            return False
        if m.group("eq"):
            return True
        if clock:
            return False
        clause = CLAUSE_END.split(s[m.end():], 1)[0]
        return "=" in clause

    def _typed_sum(self, f, grp, rule, p, e):
        """$5-$3=$2, $5-$3-$1=$1, $10-$4+$2=$8, (($10-$4))=$6: an operator after the chain of typed endpoints.
        x = $5-$3: an operator before it, when nothing but the chain follows ("Daily budget = $5-$10 per day" and
        "hours = 10:30-11:30" stay ranges). "$5-$10 per day + meals" stays a range."""
        clock = rule.name in ("time", "time_h")
        pre = not clock and re.search(SUM_BEFORE + "$", f[max(0, p - 30):p])
        while True:
            if self._op_after(f, e, clock):
                return True
            dm = re.match(r"[ \t]*-[ \t]*", f[e:])
            m3 = dm and self._endpoint_at(f, e + dm.end(), grp)
            if not m3:
                break
            e = m3[1]
        return bool(pre) and not WORD_AFTER.match(f, e)


OBLIQUE_RULES = frozenset({"money_pre", "money_post", "unit", "duration", "scaled"})
GLUE = "\x00"  # handler output starting with this joins the previous word without a space
# right after the last endpoint of a sum, closing brackets allowed: =, or an operator before a number, bracket,
# currency sign, sign or one-letter variable ($10-$4+$2=$8, ($10-$4)=$6, $10-$4 + -$2, 5 किलो-3 किलो + x = 2 किलो)
_OPERAND = rf"(?:[\d(\[₹$€£¥\-−]|[^\W\d_](?![\w{MARKS}]))"
LOCAL_OP_AFTER = re.compile(rf"(?:[ \t]*[)\]])*[ \t]*(?:(?P<eq>=)|[+×÷*/−][ \t]*{_OPERAND}|[ \t]*-[ \t]*{_OPERAND})")
CLAUSE_END = re.compile(r"[;!?\n।॥۔؟؛،꯫᱾]|[.,](?!\d)")  # script full stops end a clause too (Urdu ۔)
# just before the first endpoint, opening brackets allowed: an operator, or = after a one-letter variable, a
# number or a bracket (x = $5-$3, 2+3=$5-$0); "Daily budget = …" is a label, not a sum
# what a bracketed sum holds: numbers, fractions, one-letter variables, currency signs and operators: (2+3), (½+¼),
# (x+y); never (Mon-Fri) or (3-5 days)
_ARITH = r"(?:[\d.,₹$€£¥%‰ \t+×÷*/−½¼¾⅓⅔⅕⅛⅜⅝⅞⅙⅚⅖⅗⅘-]|(?<![^\W\d_])[^\W\d_](?![^\W\d_]))"
SUM_BEFORE = (rf"(?:[+×÷*/−]|(?:(?<![\w{MARKS}])[^\W\d_]|[\d²³]|\((?=[^()\n]*[+×÷*/−-]){_ARITH}*\)|\[(?=[^\[\]\n]*[+×÷*/−-]){_ARITH}*\])"
              rf"[ \t]*=)(?:[ \t]*[(\[])*[ \t]*")  # "(2+3) = …" counts; "Daily budget (USD) = …", "Rate (2026) = …" are labels
WORD_AFTER = re.compile(r"[ \t]+[^\W\d_]")  # x = $5-$10 per day: a word after the chain
NATIVE_CHAIN_DASH = re.compile(r"[ \t]*-(?=[ \t]*\d)")


def _url_tokens(s: str):
    """letter+mark runs of any script, digit runs, single other characters: उदाहरण.भारत -> उदाहरण . भारत"""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        j = i + 1
        if c.isdecimal():
            while j < len(s) and s[j].isdecimal():
                j += 1
        elif unicodedata.category(c)[0] in "LM":
            while j < len(s) and (unicodedata.category(s[j])[0] in "LM" or s[j] in "\u200c\u200d"):
                j += 1
        out.append(s[i:j])
        i = j
    return out


# rate denominators accepted after a unit: 5 MB/s, 3 m/min, 10 g/l
PER_UNITS = {"s": "sec", "sec": "sec", "h": "hr", "hr": "hr", "min": "min", "kg": "kg", "g": "g", "l": "l",
             "L": "l", "m": "m", "km": "km", "ml": "ml",
             "dL": "dl", "dl": "dl"}

TITLE_KEYS = frozenset({"abbr_dr", "abbr_mr", "abbr_mrs", "abbr_ms", "abbr_prof"})  # need a following name

ABBR_EN = {
    "Dr.": "abbr_dr", "Mr.": "abbr_mr", "Mrs.": "abbr_mrs", "Ms.": "abbr_ms", "Prof.": "abbr_prof",
    "etc.": "abbr_etc", "vs.": "abbr_vs", "vs": "abbr_vs", "Govt.": "abbr_govt", "approx.": "abbr_approx",
    "e.g.": "abbr_eg", "i.e.": "abbr_ie", "Jr.": "abbr_jr", "Sr.": "abbr_sr", "Ltd.": "abbr_ltd",
    "Pvt.": "abbr_pvt", "Dept.": "abbr_dept", "St.": "abbr_st",
}
