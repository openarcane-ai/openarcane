"""Indo-Aryan languages other than Hindi.

Number words:
- CLDR RBNF (data/cldr_numbers.json) for marathi, bengali, gujarati, punjabi, odia, nepali, urdu, with a CLDR
  spelling replaced only where it never occurs in the language's training text and an attested spelling does
  (data/indic_number_tables.json, `cldr_overrides`).
- Own tables for assamese, konkani, dogri, sindhi, kashmiri (`own`), kept only where attested; a gap (null)
  makes the whole number read digit by digit, never borrowed from another language.
- Hindi words for maithili, bhojpuri, magahi, chhattisgarhi, whose own text attests them, with attested local
  forms where the Hindi word does not occur (`hindi_belt_overrides`).

Other concepts (operators, units, abbreviations) come from the language's own lexicon; a gap may be filled from
a same-script relative (`fallback`), which is counted in base.FALLBACK_HITS and listed in REPORT.md.
"""
from __future__ import annotations

import json
import os
from collections import Counter

from . import cldr_layer
from .base import Lang
from .hindi import BELOW100 as HINDI_BELOW100, ORD_IRREG, Hindi

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
with open(os.path.join(_DIR, "cldr_numbers.json"), encoding="utf-8") as _fh:
    CLDR_NUM = json.load(_fh)
with open(os.path.join(_DIR, "indic_number_tables.json"), encoding="utf-8") as _fh:
    TABLES = json.load(_fh)

# (language, number) -> count of numbers read digit by digit because a word is missing. Report only.
DIGIT_FALLBACK_HITS: Counter = Counter()

DEVA = "ऀ-ॣ॰-ॿ꣠-ꣿ"
BENG = "ঀ-ৣৰ-৾"
GUJR = "઀-ૣ૰-૿"
GURU = "਀-੥ੰ-੿"
ORYA = "଀-୥୰-୿"
ARAB = "؀-ٟٮ-ۯۺ-ۿݐ-ݿ"
ZW = "‌‍"


class _Gap(Exception):
    pass


def _ending(suffix: str) -> str:
    """ending of a gendered ordinal marker = the marker minus its first consonant:
    ला -> ा, ल्या -> ्या, ઠ્ઠો -> ્ઠો (stem છઠ), ਵਾਂ -> ਾਂ, ویں -> یں."""
    return suffix[1:]


def _join(stem: str, end: str) -> str:
    if stem.endswith("र") and end.startswith("्"):  # Marathi दुसर + ्या -> दुसऱ्या
        return stem[:-1] + "ऱ" + end
    return stem + end


class IndoAryan(Lang):
    detached_suffixes: tuple = ()
    below100: list = []
    hundreds: list | None = None  # [(standalone, combining)] for 1..9, or None -> "<n> <hundred>"
    hundred = ""
    thousand = lakh = crore = ""
    year_hundred = ""  # "{x}शे": years 1100-1999 read in hundreds when a year cue is present
    ord_irreg: dict = {}  # n -> stem (+ ending) or full word
    ord_markers: dict = {}  # suffix -> allowed n (set) or "regular" (n not in ord_irreg)
    ord_regular = ""  # template for regular ordinals: "{x}वा", "{x}তম"
    ord_gendered = False  # irregular stems take the marker's vowel ending (पहिल + ा/ी/े)
    glue_pairs: dict = {}  # (last word, suffix) -> glued form (দুই+টি -> দুটি)
    joined_thousand: dict = {}  # multiplier -> one written word (Bengali দুহাজার)
    glue_merge: tuple = ()  # suffixes whose first letter merges with the same final letter (একুশ + শে)
    mixed: dict = {}  # half1, half2, half_pre, quarter_pre, three_q_pre

    # ------------------------------------------------------------ numbers
    def _w(self, n: int) -> str:
        w = self.below100[n]
        if w is None:
            raise _Gap(n)
        return w

    def _hundreds(self, h: int, last: bool) -> str:
        if self.hundreds:
            v = self.hundreds[h - 1]
            if isinstance(v, (list, tuple)):
                return v[0] if last else v[1]
            return v
        return f"{self._w(h)} {self.hundred}"

    def cardinal(self, n: int) -> str:
        if n < 100:
            return self._w(n)
        parts = []
        cr, rest = divmod(n, 10**7)
        if cr:
            parts.append(f"{self.cardinal(cr)} {self.crore}")
        lk, rest = divmod(rest, 10**5)
        if lk:
            parts.append(f"{self._w(lk)} {self.lakh}")
        th, rest = divmod(rest, 1000)
        if th:
            parts.append(self.joined_thousand.get(th) or f"{self._w(th)} {self.thousand}")
        h, rest = divmod(rest, 100)
        if h:
            parts.append(self._hundreds(h, last=not rest))
        if rest:
            parts.append(self._w(rest))
        return " ".join(parts)

    def say_int(self, n: int, **_):
        try:
            return super().say_int(n)
        except _Gap:
            DIGIT_FALLBACK_HITS[(self.name, n)] += 1
            return self.say_digits(str(n))

    def digit(self, d: int) -> str:
        return self.below100[d]

    @property
    def year_style(self):  # noqa: D401 - attribute read by the engine
        return bool(self.year_hundred)

    def year(self, n: int) -> str:
        if self.year_hundred and 1100 <= n <= 1999:
            hi, lo = divmod(n, 100)
            try:
                x = self.fill(self.year_hundred, x=self._w(hi))
                return x + (f" {self._w(lo)}" if lo else "")
            except _Gap:
                pass
        return self.say_int(n)

    # ------------------------------------------------------------ ordinals
    ord_regular_fn = None  # callable(words) -> ordinal, used instead of the template when set

    def _regular(self, n: int) -> str:
        words = self.say_int(n)
        if self.ord_regular_fn:
            return self.ord_regular_fn(words)
        return self.fill(self.ord_regular, x=words) if self.ord_regular else words

    def ordinal(self, n: int) -> str:
        if n in self.ord_irreg:
            if not self.ord_gendered:
                return self.ord_irreg[n]
            for suf, allowed in self.ord_markers.items():  # first marker listed = masculine direct form
                if allowed != "regular" and n in allowed:
                    return _join(self.ord_irreg[n], _ending(suf))
            return self.ord_irreg[n] + self.lex.get("_ord_default_end", "")
        return self._regular(n)

    def ordinal_from_suffix(self, n: int, suffix: str):
        allowed = self.ord_markers.get(suffix)
        if allowed is None:
            return None
        if allowed == "regular":
            if n in self.ord_irreg:  # 6औँ -> छैटौँ, 1واں -> پہلا: the regular marker on an irregular number
                v = self.ord_irreg[n]
                if not self.ord_gendered:
                    return v
                vow = _ending(suffix).rstrip("ंँਂੰں")[-1:]
                for suf2, allowed2 in self.ord_markers.items():  # 6મો -> છઠ્ઠો: the irregular marker's own form
                    if allowed2 != "regular" and n in allowed2 and vow and suf2.rstrip("ંंँਂੰں").endswith(vow):
                        return _join(v, _ending(suf2))
                end = self.lex.get("_ord_suffix_end", {}).get(suffix) or _ending(suffix).rstrip("ंँਂੰں")
                return _join(v, end)  # ਵਾਂ -> ਾ, واں -> ا; Urdu ویں -> ے (lex _ord_suffix_end)
            base = self._regular(n)
            if self.ord_gendered and self.ord_regular:
                default = self.ord_regular[4:]  # "{x}वा" -> "ा"
                if base.endswith(default):
                    return base[: len(base) - len(default)] + _ending(suffix)
            return base
        if n not in allowed or n not in self.ord_irreg:
            return None
        v = self.ord_irreg[n]
        if not self.ord_gendered and v.endswith("ो") and suffix.endswith("ी"):
            return v[:-1] + "ी"  # Nepali 2री -> दोस्री: the written feminine marker
        return _join(v, _ending(suffix)) if self.ord_gendered else v

    # ------------------------------------------------------------ suffixes
    def attach(self, words: str, suffix: str, n: int | None = None) -> str:
        head, sp, last = words.rpartition(" ")
        if self.lex.get("oblique_attach"):
            last = self.oblique(last)
            words = head + sp + last
        cls = self.lex.get("classifier")
        if cls and suffix.startswith(cls):
            if last.endswith(cls):  # পাঁচটা + টায় -> পাঁচটায়
                return head + sp + last + suffix[len(cls):]
            if last in (self.w("u_min", ""), self.w("u_sec", ""), self.lex.get("time_h_1")):  # the clock word ends the time
                am = self.lex.get("after_minute", {}).get(suffix)  # ত্রিশ মিনিট + টায় -> ত্রিশ মিনিটে
                return head + sp + last + (am if am is not None else suffix[len(cls):])  # ମିନିଟ + ଟାରେ -> ମିନିଟରେ
        glued = self.glue_pairs.get((last, suffix))
        if glued:
            return head + sp + glued
        if suffix in self.glue_merge and last.endswith(suffix[0]):  # একুশ + শে -> একুশে, not একুশশে
            return head + sp + last + suffix[1:]
        return super().attach(words, suffix, n)

    def mixed_fraction(self, whole, a, b):
        mx = self.mixed
        if not mx:
            return None
        if (a, b) == (1, 2):
            if whole == 1 and mx.get("half1"):
                return mx["half1"]
            if whole == 2 and mx.get("half2"):
                return mx["half2"]
            if mx.get("half_pre"):
                return f"{mx['half_pre']} {self.say_int(whole)}"
        if (a, b) == (1, 4) and mx.get("quarter_pre"):
            return f"{mx['quarter_pre']} {self.say_int(whole)}"
        if (a, b) == (3, 4) and mx.get("three_q_pre"):
            return f"{mx['three_q_pre']} {self.say_int(whole + 1)}"
        return None


def _cldr_below100(name: str) -> list:
    words = list(CLDR_NUM[name]["below100"])
    for k, v in TABLES["cldr_overrides"].get(name, {}).items():
        words[int(k)] = v
    return words


def _cldr_hundreds(name: str) -> list:
    """CLDR gives (standalone, combining) for 100..900."""
    out = [tuple(x) for x in CLDR_NUM[name]["hundreds"][1:]]
    for k, v in TABLES.get("cldr_hundreds_overrides", {}).get(name, {}).items():
        out[int(k) - 1] = (v, v)
    return out


def _cldr_scale(name: str, key: str) -> str:
    two = CLDR_NUM[name][f"{key}_2"][0]  # "दोन हजार" -> "हजार"
    return two.split(" ", 1)[1]


def _symbols(dot, slash, at, hyphen, underscore, colon, question, hash_, tilde, semicolon, comma, excl):
    return {"dot": dot, "slash": slash, "at": at, "hyphen": hyphen, "underscore": underscore, "colon": colon,
            "question": question, "hash": hash_, "tilde": tilde, "semicolon": semicolon, "comma": comma,
            "exclamation": excl}


# ---------------------------------------------------------------------------------------------- Marathi
MR_LEX = {
    "point": "पूर्णांक", "plus": "अधिक", "phone_plus": "प्लस", "minus": "वजा", "neg": "उणे", "times": "गुणिले", "divide": "भागिले",
    "equals": "बरोबर", "neq": "बरोबर नाही", "lt": "लेस दॅन", "gt": "ग्रेटर दॅन", "le": "लेस दॅन ऑर इक्वल टू",
    "ge": "ग्रेटर दॅन ऑर इक्वल टू", "pm": "अधिक वजा", "approx": "सुमारे", "squared": "चा वर्ग", "cubed": "चा घन",
    "power": "चा घात {n}", "root": "वर्गमूळ", "cuberoot": "घनमूळ", "fourthroot": "चतुर्थमूळ",
    "fraction": "{a} बटे {b}", "mixed_fraction": "{x} पूर्णांक {f}",
    "fractions_special": {(1, 2): "अर्धा", (1, 4): "पाव", (3, 4): "पाऊण"},
    "per": "{u} प्रति {p}", "percent": "{x} टक्के", "percent_word": "टक्के", "permille": "दर हजारी {x}",
    "range": "{a} ते {b}", "ratio": "{a} ला {b}", "ratio_cue": "गुणोत्तर", "date_labels": "दिनांक|तारीख",
    "year_before": r"(?:सन|साल|वर्ष|इ\.स\.)", "year_after": rf"\s?(?:मध्ये|साली|सालापासून|पासून|पर्यंत|चा|ची|चे|च्या|ला)(?![{DEVA}])",
    **_symbols("डॉट", "स्लॅश", "ॲट", "हायफन", "अंडरस्कोर", "कोलन", "प्रश्नचिन्ह", "हॅश", "टिल्ड", "सेमीकोलन",
               "स्वल्पविराम", "उद्गारवाचक चिन्ह"),
    "and": "आणि", "number_word": "क्रमांक",
    "phone_keywords": ["फोन नंबर", "फोन क्रमांक", "फोन", "मोबाईल नंबर", "मोबाईल", "हेल्पलाइन"],
    "code_connectors": ["आहे"], "phone_cues_after": ["वर फोन करा", "वर कॉल करा"],
    "code_keywords": ["ओटीपी", "पिन कोड", "पिनकोड", "पिन", "खाते क्रमांक", "आधार क्रमांक", "कोड"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} वाजता", "time_hm": "{h} वाजून {m} मिनिटे", "time_hms": "{h} वाजून {m} मिनिटे {s} सेकंद",
    "time_ap": "{dp} {t}", "time_absorb": ("वाजता", "वाजले"), "dp_morning": "सकाळी", "dp_noon": "दुपारी",
    "dp_evening": "संध्याकाळी", "dp_night": "रात्री",
    "money": "{x} {cur}", "cur_INR": ("रुपया", "रुपये"), "sub_INR": ("पैसा", "पैसे"), "cur_USD": "डॉलर",
    "sub_USD": "सेंट", "cur_EUR": "युरो", "sub_EUR": "सेंट", "cur_GBP": "पाउंड", "sub_GBP": "पेन्स",
    "scale_thousand": "हजार", "scale_lakh": "लाख", "scale_crore": "कोटी", "scale_million": "दशलक्ष",
    "scale_billion": "अब्ज", "scale_trillion": "ट्रिलियन",
    "scale_native": {"हजार": 1, "हज़ार": 1, "लाख": 1, "कोटी": 1},
    "currency_native": {"रु.": "INR", "रू.": "INR"},
    "abbr_native": {"डॉ.": "डॉक्टर"},
    "abbr_dr": "डॉक्टर", "abbr_mr": "मिस्टर", "abbr_mrs": "मिसेस", "abbr_prof": "प्राध्यापक", "abbr_etc": "इत्यादी",
    "abbr_vs": "विरुद्ध", "abbr_govt": "सरकार", "abbr_approx": "सुमारे", "abbr_eg": "उदाहरणार्थ",
    "abbr_ie": "म्हणजे", "abbr_ltd": "लिमिटेड", "abbr_pvt": "प्रायव्हेट",
    "u_hr": "तास", "u_min": ("मिनिट", "मिनिटे"), "u_sec": "सेकंद", "u_year": "वर्षे",
    "time_hm_1": "{h} वाजून {m} मिनिट", "percent_one": "{x} टक्का",  # मिनिट 13, टक्का 15
}
MR_ORD = {1: "पहिल", 2: "दुसर", 3: "तिसर", 4: "चौथ", 9: "नवव", 20: "विसाव"}  # नवव्या 13, विसाव्या 34
_mr_end = ("ा", "ी", "े", "्या")
MR_MARKERS = {**{"ल" + e: {1} for e in _mr_end}, **{"र" + e: {2, 3} for e in _mr_end},
              **{"ऱ" + e: {2, 3} for e in _mr_end}, **{"थ" + e: {4} for e in _mr_end},
              **{"व" + e: "regular" for e in _mr_end}}

# ---------------------------------------------------------------------------------------------- Bengali
BN_LEX = {
    # ডিগ্রি 95 vs CLDR ডিগ্রী 21 in the text
    "u_deg": "ডিগ্রি", "u_degC": "ডিগ্রি সেলসিয়াস", "u_degF": "ডিগ্রি ফারেনহাইট",
    "classifier": "টা", "after_minute": {"টায়": "ে", "টার": "ের", "টাতে": "ে"},  # ৫:০০টায় -> পাঁচটায়; ৩০ মিনিটে
    "point": "দশমিক", "plus": "যোগ", "minus": "বিয়োগ", "neg": "মাইনাস", "phone_plus": "প্লাস", "times": "গুণ", "divide": "ভাগ",
    "equals": "সমান", "neq": "সমান নয়", "lt": "লেস দ্যান", "gt": "গ্রেটার দ্যান", "le": "লেস দ্যান অর ইকুয়াল টু",
    "ge": "গ্রেটার দ্যান অর ইকুয়াল টু", "pm": "যোগ বিয়োগ", "approx": "প্রায়", "squared": "এর বর্গ",
    "cubed": "এর ঘন", "power": "এর ঘাত {n}", "root": "বর্গমূল", "cuberoot": "ঘনমূল", "fourthroot": "চতুর্থ মূল",
    "fraction": "{b} ভাগের {a}", "mixed_fraction": "{x} পূর্ণ {f}",
    "fractions_special": {(1, 2): "অর্ধেক"},
    "per": "{u} প্রতি {p}", "percent": "{x} শতাংশ", "percent_word": "শতাংশ", "permille": "প্রতি হাজারে {x}",
    "range": "{a} থেকে {b}", "ratio": "{a} অনুপাত {b}", "ratio_cue": "অনুপাত", "date_labels": "তারিখ",
    "year_before": r"(?:সাল|সন)", "year_after": rf"\s?(?:সালে|সালের|সাল|খ্রিস্টাব্দে|খ্রিস্টাব্দ|থেকে|পর্যন্ত)(?![{BENG}])",
    **_symbols("ডট", "স্ল্যাশ", "অ্যাট", "হাইফেন", "আন্ডারস্কোর", "কোলন", "প্রশ্নবোধক চিহ্ন", "হ্যাশ", "টিল্ডা",
               "সেমিকোলন", "কমা", "বিস্ময়সূচক চিহ্ন"),
    "and": "এবং", "number_word": "নম্বর",
    "phone_keywords": ["ফোন নম্বর", "ফোন", "মোবাইল নম্বর", "মোবাইল", "হেল্পলাইন"],
    "code_connectors": ["হল", "হলো"],
    "code_keywords": ["ওটিপি", "পিন কোড", "পিন", "অ্যাকাউন্ট নম্বর", "কোড"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h+টা}", "time_hm": "{h+টা} বেজে {m} মিনিট", "time_hms": "{h+টা} বেজে {m} মিনিট {s} সেকেন্ড",
    "time_ap": "{dp} {t}", "time_absorb": ("বাজে",), "dp_morning": "সকাল", "dp_noon": "দুপুর",
    "dp_evening": "বিকেল", "dp_dusk": "সন্ধ্যা", "dp_dusk_from": 6,  # বিকেল পাঁচটা 11; সন্ধ্যা সাতটা 6 vs রাত সাতটা 4
    "dp_night": "রাত",
    "money": "{x} {cur}", "cur_INR": "টাকা", "sub_INR": "পয়সা", "cur_USD": "ডলার", "sub_USD": "সেন্ট",
    "cur_EUR": "ইউরো", "sub_EUR": "সেন্ট", "cur_GBP": "পাউন্ড", "sub_GBP": "পেন্স",
    "scale_thousand": "হাজার", "scale_lakh": "লাখ", "scale_crore": "কোটি", "scale_million": "মিলিয়ন",
    "scale_billion": "বিলিয়ন", "scale_trillion": "ট্রিলিয়ন",
    "scale_native": {"হাজার": 1, "লাখ": 1, "লক্ষ": 1, "কোটি": 1},
    "abbr_native": {"ডা.": "ডাক্তার"},
    "abbr_dr": "ডাক্তার", "abbr_mr": "মিস্টার", "abbr_mrs": "মিসেস", "abbr_prof": "অধ্যাপক", "abbr_etc": "ইত্যাদি",
    "abbr_vs": "বনাম", "abbr_govt": "সরকার", "abbr_approx": "প্রায়", "abbr_eg": "যেমন", "abbr_ie": "অর্থাৎ",
    "abbr_ltd": "লিমিটেড", "abbr_pvt": "প্রাইভেট",
    "u_hr": "ঘণ্টা", "u_min": "মিনিট", "u_sec": "সেকেন্ড", "u_year": "বছর",
}
BN_SANSKRIT_ORD = {1: "প্রথম", 2: "দ্বিতীয়", 3: "তৃতীয়", 4: "চতুর্থ", 5: "পঞ্চম", 6: "ষষ্ঠ", 7: "সপ্তম",
                   8: "অষ্টম", 9: "নবম", 10: "দশম"}
BN_MARKERS = {"ম": {1, 5, 7, 8, 9, 10}, "\u09df": {2, 3}, "\u09af\u09bc": {2, 3}, "র্থ": {4}, "ষ্ঠ": {6}, "তম": "regular"}
# date forms: ১লা পয়লা, ২রা দোসরা, ৩রা তেসরা, ৪ঠা চৌঠা, ২০শে বিশে; other শে dates merge: একুশ + শে -> একুশে
BN_GLUE = {("এক", "লা"): "পয়লা", ("দুই", "রা"): "দোসরা", ("তিন", "রা"): "তেসরা", ("চার", "ঠা"): "চৌঠা",
           ("কুড়ি", "শে"): "বিশে", ("দুই", "টি"): "দুটি", ("দুই", "টা"): "দুটো", ("দুই", "জন"): "দুজন", ("তিন", "টা"): "তিনটে",
           ("চার", "টা"): "চারটে", ("ছয়", "টা"): "ছটা", ("নয়", "টা"): "নটা"}

# ---------------------------------------------------------------------------------------------- Assamese
AS_LEX = {
    "time_absorb": ("বজা",),  # 7 PM বজাত -> সন্ধিয়া সাত বজাত: the ending stays on our clock word (বজাত 115)
    "range_qty": "{a+ৰ} পৰা {b}",  # 5-10 kg: পাঁচৰ পৰা দহ কিলোগ্ৰাম; unverified
    "point": "দশমিক", "plus": "যোগ", "minus": "বিয়োগ", "neg": "মাইনাছ",  # sign, not subtraction (মাইনাছ attested once; unverified)
    "u_kmph": "কিলোমিটাৰ প্ৰতি ঘণ্টা",  # CLDR has ঘণ্টা প্ৰতি কিলোমিটাৰ; text: প্ৰতি ঘণ্টা 7, ঘণ্টা প্ৰতি 0
    "dp_dusk": "সন্ধিয়া", "dp_dusk_from": 6,
    "phone_plus": "প্লাছ", "times": "পূৰণ", "divide": "হৰণ",
    "equals": "সমান", "neq": "সমান নহয়", "lt": "লেছ দেন", "gt": "গ্ৰেটাৰ দেন", "le": "লেছ দেন অৰ ইকুৱেল টু",
    "ge": "গ্ৰেটাৰ দেন অৰ ইকুৱেল টু", "pm": "যোগ বিয়োগ", "approx": "প্ৰায়", "squared": "ৰ বৰ্গ",
    "cubed": "ৰ ঘন", "power": "ৰ ঘাত {n}", "root": "বৰ্গমূল", "cuberoot": "ঘনমূল", "fourthroot": "চতুৰ্থ মূল",
    "fraction": "{b} ভাগৰ {a} ভাগ", "mixed_fraction": "{x} পূৰ্ণ {f}",
    "fractions_special": {(1, 2): "আধা"},
    "per": "{u} প্ৰতি {p}", "percent": "{x} শতাংশ", "percent_word": "শতাংশ",
    "range": "{a+ৰ} পৰা {b+লৈ}", "ratio": "{a} অনুপাত {b}", "ratio_cue": "অনুপাত", "date_labels": "তাৰিখ",
    **_symbols("ডট", "শ্লেছ", "এট", "হাইফেন", "আণ্ডাৰস্কোৰ", "কলন", "প্ৰশ্নবোধক চিহ্ন", "হেচ", "টিল্ড", "ছেমিকলন",
               "কমা", "বিস্ময়সূচক চিহ্ন"),
    "and": "আৰু", "number_word": "নম্বৰ",
    "phone_keywords": ["ফোন নম্বৰ", "ফোন", "মোবাইল নম্বৰ", "মোবাইল", "মবাইল", "হেল্পলাইন"],
    "code_keywords": ["অটিপি", "পিন কোড", "পিন", "কোড"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    # text: "পুৱা ৬ বাজি ২৫ মিনিট", "ছয় বজাত" (ছয় বজা 6 vs ছয়টা বজা 1)
    "time_h": "{h} বজা", "time_hm": "{h} বাজি {m} মিনিট", "time_hms": "{h} বাজি {m} মিনিট {s} ছেকেণ্ড",
    "time_ap": "{dp} {t}", "dp_morning": "পুৱা", "dp_noon": "দুপৰীয়া", "dp_evening": "আবেলি", "dp_night": "ৰাতি",
    "money": "{x} {cur}", "cur_INR": "টকা", "sub_INR": "পইচা", "cur_USD": "ডলাৰ", "sub_USD": "চেণ্ট",
    "cur_EUR": "ইউৰো", "sub_EUR": "চেণ্ট", "cur_GBP": "পাউণ্ড", "sub_GBP": "পেন্স",
    "scale_thousand": "হাজাৰ", "scale_lakh": "লাখ", "scale_crore": "কোটি", "scale_million": "মিলিয়ন",
    "scale_billion": "বিলিয়ন", "scale_trillion": "ট্ৰিলিয়ন",
    "scale_native": {"হাজাৰ": 1, "লাখ": 1, "কোটি": 1},
    "abbr_dr": "ডাক্তৰ", "abbr_etc": "ইত্যাদি", "abbr_govt": "চৰকাৰ",
    "u_hr": "ঘণ্টা", "u_min": "মিনিট", "u_sec": "ছেকেণ্ড", "u_year": "বছৰ",
}
AS_ORD = {1: "প্ৰথম", 2: "দ্বিতীয়", 3: "তৃতীয়", 4: "চতুৰ্থ", 5: "পঞ্চম", 6: "ষষ্ঠ", 7: "সপ্তম", 8: "অষ্টম",
          9: "নৱম", 10: "দশম"}
AS_MARKERS = {"ম": {1, 5, 7, 8, 9, 10}, "\u09df": {2, 3}, "\u09af\u09bc": {2, 3}, "ৰ্থ": {4}, "ষ্ঠ": {6}, "তম": "regular"}
AS_GLUE = {("এক", "টা"): "এটা", ("এক", "জন"): "এজন", ("এক", "খন"): "এখন", ("এক", "টি"): "এটি",
           ("দুই", "টা"): "দুটা", ("দুই", "জন"): "দুজন", ("দুই", "টি"): "দুটি"}

# ---------------------------------------------------------------------------------------------- Gujarati
GU_LEX = {
    "oblique_attach": True,  # ₹1માં -> એક રૂપિયામાં (રૂપિયામાં 10, રૂપિયોમાં 0)
    "oblique_before": ("માંથી", "માં", "નો", "ની", "નું", "ને", "થી", "માટે", "પર", "સુધી", "વાળો", "વાળી", "વાળા"),  # spaced: એક રૂપિયા માં; unverified. No spaced ના: it is also the negator (₹1 ના આપો)
    "point": "પોઈન્ટ", "plus": "વત્તા", "phone_plus": "પ્લસ", "minus": "ઓછા", "neg": "માઇનસ", "times": "ગુણ્યા", "divide": "ભાગ્યા",
    "equals": "બરાબર", "neq": "બરાબર નથી", "lt": "લેસ ધેન", "gt": "ગ્રેટર ધેન", "le": "લેસ ધેન ઓર ઇક્વલ ટુ",
    "ge": "ગ્રેટર ધેન ઓર ઇક્વલ ટુ", "pm": "વત્તા ઓછા", "approx": "આશરે", "squared": "નો વર્ગ", "cubed": "નો ઘન",
    "power": "ની ઘાત {n}", "root": "વર્ગમૂળ", "cuberoot": "ઘનમૂળ", "fourthroot": "ચતુર્થ મૂળ",
    "fraction": "{a} ભાગ્યા {b}", "mixed_fraction": "{x} પૂર્ણાંક {f}",
    "fractions_special": {(1, 2): "અડધું"},
    "per": "{u} પ્રતિ {p}", "percent": "{x} ટકા", "percent_word": "ટકા", "permille": "{x} પ્રતિ હજાર",
    "range": "{a+થી} {b}", "ratio": "{a} ગુણોત્તર {b}", "ratio_cue": "ગુણોત્તર", "date_labels": "તારીખ",
    "year_before": r"(?:સન|સાલ|વર્ષ)", "year_after": rf"\s?(?:માં|ના|ની|નું|થી|સુધી|ઈ\.સ\.)(?![{GUJR}])",
    **_symbols("ડોટ", "સ્લેશ", "એટ", "હાઇફન", "અંડરસ્કોર", "કોલન", "પ્રશ્નાર્થ ચિહ્ન", "હેશ", "ટિલ્ડ", "સેમિકોલન",
               "અલ્પવિરામ", "ઉદ્ગાર ચિહ્ન"),
    "and": "અને", "number_word": "નંબર",
    "phone_keywords": ["ફોન નંબર", "ફોન", "મોબાઇલ નંબર", "મોબાઇલ", "હેલ્પલાઇન"],
    "code_connectors": ["છે"], "phone_cues_after": ["પર ફોન કરો", "પર કૉલ કરો"],
    "code_keywords": ["ઓટીપી", "પિન કોડ", "પિન", "ખાતા નંબર", "કોડ"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} વાગ્યે", "time_hm": "{h} વાગીને {m} મિનિટ", "time_hms": "{h} વાગીને {m} મિનિટ {s} સેકન્ડ",
    "time_ap": "{dp} {t}", "time_absorb": ("વાગ્યે",), "dp_morning": "સવારે", "dp_noon": "બપોરે",
    "dp_evening": "સાંજે", "dp_night": "રાત્રે",
    "money": "{x} {cur}", "cur_INR": ("રૂપિયો", "રૂપિયા"), "sub_INR": ("પૈસો", "પૈસા"), "cur_USD": "ડોલર",
    "sub_USD": "સેન્ટ", "cur_EUR": "યુરો", "sub_EUR": "સેન્ટ", "cur_GBP": "પાઉન્ડ", "sub_GBP": "પેન્સ",
    "scale_thousand": "હજાર", "scale_lakh": "લાખ", "scale_crore": "કરોડ", "scale_million": "મિલિયન",
    "scale_billion": "બિલિયન", "scale_trillion": "ટ્રિલિયન",
    "scale_native": {"હજાર": 1, "લાખ": 1, "કરોડ": 1},
    "currency_native": {"રૂ.": "INR", "રુ.": "INR"},
    "abbr_native": {"ડૉ.": "ડૉક્ટર"},
    "abbr_dr": "ડૉક્ટર", "abbr_mr": "મિસ્ટર", "abbr_etc": "વગેરે", "abbr_vs": "વિરુદ્ધ", "abbr_govt": "સરકાર",
    "abbr_approx": "આશરે", "abbr_eg": "ઉદાહરણ તરીકે", "abbr_ltd": "લિમિટેડ", "abbr_pvt": "પ્રાઇવેટ",
    "u_hr": "કલાક", "u_min": "મિનિટ", "u_sec": "સેકન્ડ", "u_year": "વર્ષ",
}
GU_ORD = {1: "પહેલ", 2: "બીજ", 3: "ત્રીજ", 4: "ચોથ", 6: "છઠ"}
_gu_end = ("ો", "ી", "ું", "ા")
GU_MARKERS = {**{"લ" + e: {1} for e in _gu_end}, **{"જ" + e: {2, 3} for e in _gu_end},
              **{"થ" + e: {4} for e in _gu_end}, **{"ઠ્ઠ" + e: {6} for e in _gu_end},
              **{"મ" + e: "regular" for e in ("ો", "ી", "ું")}}

# ---------------------------------------------------------------------------------------------- Punjabi
PA_LEX = {
    "oblique_before": ("ਵਿੱਚ", "ਵਿਚ", "ਲਈ", "ਤੋਂ", "ਨੂੰ", "ਦਾ", "ਦੀ", "ਦੇ", "ਤੱਕ", "ਤਕ", "ਵਾਲਾ", "ਵਾਲੀ", "ਵਾਲੇ"),  # ਇੱਕ ਘੰਟੇ ਲਈ
    "point": "ਦਸ਼ਮਲਵ", "plus": "ਜਮ੍ਹਾਂ", "phone_plus": "ਪਲੱਸ", "minus": "ਘਟਾਓ", "neg": "ਮਾਈਨਸ", "times": "ਗੁਣਾ", "divide": "ਭਾਗ",
    "equals": "ਬਰਾਬਰ", "neq": "ਬਰਾਬਰ ਨਹੀਂ", "lt": "ਲੈੱਸ ਦੈਨ", "gt": "ਗ੍ਰੇਟਰ ਦੈਨ", "le": "ਲੈੱਸ ਦੈਨ ਔਰ ਇਕੁਅਲ ਟੂ",
    "ge": "ਗ੍ਰੇਟਰ ਦੈਨ ਔਰ ਇਕੁਅਲ ਟੂ", "pm": "ਜਮ੍ਹਾਂ ਘਟਾਓ", "approx": "ਲਗਭਗ", "squared": "ਦਾ ਵਰਗ", "cubed": "ਦਾ ਘਣ",
    "power": "ਦੀ ਘਾਤ {n}", "root": "ਵਰਗਮੂਲ", "cuberoot": "ਘਣਮੂਲ", "fourthroot": "ਚੌਥਾ ਮੂਲ",
    "fraction": "{a} ਬਟਾ {b}", "mixed_fraction": "{x} ਪੂਰਨ {f}",
    "fractions_special": {(1, 2): "ਅੱਧਾ"},
    "per": "{u} ਪ੍ਰਤੀ {p}", "percent": "{x} ਪ੍ਰਤੀਸ਼ਤ", "percent_word": "ਪ੍ਰਤੀਸ਼ਤ", "permille": "{x} ਪ੍ਰਤੀ ਹਜ਼ਾਰ",
    "range": "{a} ਤੋਂ {b}", "ratio": "{a} ਅਨੁਪਾਤ {b}", "ratio_cue": "ਅਨੁਪਾਤ", "date_labels": "ਤਾਰੀਖ|ਤਾਰੀਖ਼|ਮਿਤੀ",
    "year_before": r"(?:ਸੰਨ|ਸਾਲ|ਸਨ)", "year_after": rf"\s?(?:ਵਿੱਚ|ਵਿਚ|ਦੇ|ਦੀ|ਦਾ|ਤੋਂ|ਤੱਕ|ਈ\.)(?![{GURU}])",
    **_symbols("ਡਾਟ", "ਸਲੈਸ਼", "ਐਟ", "ਹਾਈਫਨ", "ਅੰਡਰਸਕੋਰ", "ਕੋਲਨ", "ਪ੍ਰਸ਼ਨ ਚਿੰਨ੍ਹ", "ਹੈਸ਼", "ਟਿਲਡ", "ਸੈਮੀਕੋਲਨ",
               "ਕਾਮਾ", "ਵਿਸਮਿਕ ਚਿੰਨ੍ਹ"),
    "and": "ਅਤੇ", "number_word": "ਨੰਬਰ",
    "phone_keywords": ["ਫ਼ੋਨ ਨੰਬਰ", "ਫੋਨ ਨੰਬਰ", "ਫ਼ੋਨ", "ਫੋਨ", "ਮੋਬਾਈਲ ਨੰਬਰ", "ਮੋਬਾਈਲ", "ਹੈਲਪਲਾਈਨ"],
    "code_connectors": ["ਹੈ"],
    "code_keywords": ["ਓਟੀਪੀ", "ਪਿੰਨ ਕੋਡ", "ਪਿੰਨ", "ਖਾਤਾ ਨੰਬਰ", "ਕੋਡ"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} ਵਜੇ", "time_hm": "{h} ਵੱਜ ਕੇ {m} ਮਿੰਟ", "time_hms": "{h} ਵੱਜ ਕੇ {m} ਮਿੰਟ {s} ਸਕਿੰਟ",
    "time_ap": "{dp} {t}", "time_absorb": ("ਵਜੇ",), "dp_morning": "ਸਵੇਰੇ", "dp_noon": "ਦੁਪਹਿਰ", "dp_evening": "ਸ਼ਾਮ",
    "dp_night": "ਰਾਤ",
    "money": "{x} {cur}", "cur_INR": ("ਰੁਪਿਆ", "ਰੁਪਏ"), "sub_INR": ("ਪੈਸਾ", "ਪੈਸੇ"), "cur_USD": "ਡਾਲਰ",
    "sub_USD": "ਸੈਂਟ", "cur_EUR": "ਯੂਰੋ", "sub_EUR": "ਸੈਂਟ", "cur_GBP": "ਪੌਂਡ", "sub_GBP": "ਪੈਂਸ",
    "scale_thousand": "ਹਜ਼ਾਰ", "scale_lakh": "ਲੱਖ", "scale_crore": "ਕਰੋੜ", "scale_million": "ਮਿਲੀਅਨ",
    "scale_billion": "ਬਿਲੀਅਨ", "scale_trillion": "ਟ੍ਰਿਲੀਅਨ",
    "scale_native": {"ਹਜ਼ਾਰ": 1, "ਹਜਾਰ": 1, "ਲੱਖ": 1, "ਕਰੋੜ": 1},
    "currency_native": {"ਰੁ.": "INR"},
    "abbr_native": {"ਡਾ.": "ਡਾਕਟਰ"},
    "abbr_dr": "ਡਾਕਟਰ", "abbr_mr": "ਮਿਸਟਰ", "abbr_etc": "ਆਦਿ", "abbr_vs": "ਬਨਾਮ", "abbr_govt": "ਸਰਕਾਰ",
    "abbr_approx": "ਲਗਭਗ", "abbr_ltd": "ਲਿਮਟਿਡ", "abbr_pvt": "ਪ੍ਰਾਈਵੇਟ",
    "u_hr": ("ਘੰਟਾ", "ਘੰਟੇ"), "u_min": "ਮਿੰਟ", "u_sec": "ਸਕਿੰਟ", "u_year": "ਸਾਲ",
}
PA_ORD = {1: "ਪਹਿਲ", 2: "ਦੂਜ", 3: "ਤੀਜ", 4: "ਚੌਥ"}
_pa_end = ("ਾ", "ੀ", "ੇ")
PA_MARKERS = {**{"ਲ" + e: {1} for e in _pa_end}, **{"ਜ" + e: {2, 3} for e in _pa_end},
              **{"ਥ" + e: {4} for e in _pa_end}, **{"ਵ" + e: "regular" for e in ("ਾਂ", "ੀਂ", "ੇਂ")}}

# ---------------------------------------------------------------------------------------------- Odia
OR_LEX = {
    "classifier": "ଟା", "time_h_1": "ଗୋଟାଏ",  # ଦଶଟାରେ; ଦିନ ଗୋଟାଏରେ (ଗୋଟାଏ 21, ଏକଟା 0); unverified
    "point": "ଦଶମିକ", "plus": "ଯୋଗ", "phone_plus": "ପ୍ଲସ", "minus": "ବିଯୋଗ", "neg": "ମାଇନସ", "times": "ଗୁଣ", "divide": "ଭାଗ",
    "equals": "ସମାନ", "neq": "ସମାନ ନୁହେଁ", "lt": "ଲେସ ଦ୍ୟାନ", "gt": "ଗ୍ରେଟର ଦ୍ୟାନ", "le": "ଲେସ ଦ୍ୟାନ ଅର ଇକୁଆଲ ଟୁ",
    "ge": "ଗ୍ରେଟର ଦ୍ୟାନ ଅର ଇକୁଆଲ ଟୁ", "pm": "ଯୋଗ ବିଯୋଗ", "approx": "ପ୍ରାୟ", "squared": "ର ବର୍ଗ", "cubed": "ର ଘନ",
    "power": "ର ଘାତ {n}", "root": "ବର୍ଗମୂଳ", "cuberoot": "ଘନମୂଳ", "fourthroot": "ଚତୁର୍ଥ ମୂଳ",
    "fraction": "{b} ଭାଗରୁ {a} ଭାଗ", "mixed_fraction": "{x} ପୂର୍ଣ୍ଣ {f}",
    "fractions_special": {(1, 2): "ଅଧା"},
    "per": "{u} ପ୍ରତି {p}", "percent": "{x} ପ୍ରତିଶତ", "percent_word": "ପ୍ରତିଶତ",
    "range": "{a+ରୁ} {b}", "ratio": "{a} ଅନୁପାତ {b}", "ratio_cue": "ଅନୁପାତ", "date_labels": "ତାରିଖ",
    "year_before": r"(?:ସନ|ବର୍ଷ)", "year_after": rf"\s?(?:ମସିହାରେ|ମସିହା|ମସିହାର|ସାଲରେ|ଠାରୁ|ପର୍ଯ୍ୟନ୍ତ)(?![{ORYA}])",
    **_symbols("ଡଟ", "ସ୍ଲାସ", "ଆଟ", "ହାଇଫେନ", "ଅଣ୍ଡରସ୍କୋର", "କୋଲନ", "ପ୍ରଶ୍ନବାଚକ ଚିହ୍ନ", "ହ୍ୟାସ", "ଟିଲଡ",
               "ସେମିକୋଲନ", "କମା", "ବିସ୍ମୟସୂଚକ ଚିହ୍ନ"),
    "and": "ଏବଂ", "number_word": "ନମ୍ବର",
    "phone_keywords": ["ଫୋନ ନମ୍ବର", "ଫୋନ", "ମୋବାଇଲ", "ହେଲ୍ପଲାଇନ"],
    "code_keywords": ["ଓଟିପି", "ପିନ କୋଡ", "ପିନ", "କୋଡ"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h+ଟା}", "time_hm": "{h+ଟା} {m} ମିନିଟ", "time_hms": "{h+ଟା} {m} ମିନିଟ {s} ସେକେଣ୍ଡ",
    "time_ap": "{dp} {t}", "dp_morning": "ସକାଳ", "dp_noon": "ମଧ୍ୟାହ୍ନ", "dp_evening": "ସନ୍ଧ୍ୟା", "dp_night": "ରାତି",
    "money": "{x} {cur}", "cur_INR": "ଟଙ୍କା", "sub_INR": "ପଇସା", "cur_USD": "ଡଲାର", "sub_USD": "ସେଣ୍ଟ",
    "cur_EUR": "ୟୁରୋ", "sub_EUR": "ସେଣ୍ଟ", "cur_GBP": "ପାଉଣ୍ଡ", "sub_GBP": "ପେନ୍ସ",
    "scale_thousand": "ହଜାର", "scale_lakh": "ଲକ୍ଷ", "scale_crore": "କୋଟି", "scale_million": "ମିଲିୟନ",
    "scale_billion": "ବିଲିୟନ", "scale_trillion": "ଟ୍ରିଲିୟନ",
    "scale_native": {"ହଜାର": 1, "ଲକ୍ଷ": 1, "କୋଟି": 1},
    "abbr_dr": "ଡାକ୍ତର", "abbr_etc": "ଇତ୍ୟାଦି", "abbr_govt": "ସରକାର",
    "u_hr": "ଘଣ୍ଟା", "u_min": "ମିନିଟ", "u_sec": "ସେକେଣ୍ଡ", "u_year": "ବର୍ଷ",
}
OR_ORD = {1: "ପ୍ରଥମ", 2: "ଦ୍ୱିତୀୟ", 3: "ତୃତୀୟ", 4: "ଚତୁର୍ଥ", 5: "ପଞ୍ଚମ", 6: "ଷଷ୍ଠ", 7: "ସପ୍ତମ", 8: "ଅଷ୍ଟମ",
          9: "ନବମ", 10: "ଦଶମ"}
OR_MARKERS = {"ମ": {1, 5, 7, 8, 9, 10}, "\u0b5f": {2, 3}, "\u0b2f\u0b3c": {2, 3}, "ର୍ଥ": {4}, "ଷ୍ଠ": {6}, "ତମ": "regular"}

# ---------------------------------------------------------------------------------------------- Nepali
NE_LEX = {
    # genitive को is written joined to the number (दुईको घन); construction unverified
    "squared": "+को वर्ग", "cubed": "+को घन", "power": "+को {n} घात",
    "point": "दशमलव", "plus": "जोड", "phone_plus": "प्लस", "minus": "घटाउ", "neg": "माइनस", "times": "गुणा", "divide": "भाग",
    "equals": "बराबर", "neq": "बराबर छैन", "approx": "करिब", "pm": "जोड घटाउ",
    "fraction": "{b} भागको {a}", "mixed_fraction": "{x} पूर्ण {f}", "fractions_special": {(1, 2): "आधा"},
    "per": "{u} प्रति {p}", "percent": "{x} प्रतिशत", "percent_word": "प्रतिशत", "permille": "{x} प्रति हजार",
    "range": "{a} देखि {b}", "ratio": "{a} अनुपात {b}", "ratio_cue": "अनुपात", "date_labels": "मिति",
    "year_before": r"(?:सन्|सन|साल|ईस्वी)", "year_after": rf"\s?(?:मा|देखि|सम्म|को|ई\.)(?![{DEVA}])",
    **_symbols("डट", "स्ल्याश", "एट", "हाइफन", "अन्डरस्कोर", "कोलन", "प्रश्नवाचक चिह्न", "ह्यास", "टिल्डे",
               "सेमिकोलन", "अल्पविराम", "विस्मयादिबोधक चिह्न"),
    "and": "र", "number_word": "नम्बर",
    "phone_keywords": ["फोन नम्बर", "फोन", "मोबाइल नम्बर", "मोबाइल", "हेल्पलाइन"],
    "code_connectors": ["हो"], "phone_cues_after": ["मा फोन गर्नुहोस्"],
    "code_keywords": ["ओटीपी", "पिन कोड", "पिन", "खाता नम्बर", "कोड"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} बजे", "time_hm": "{h} बजेर {m} मिनेट", "time_hms": "{h} बजेर {m} मिनेट {s} सेकेन्ड",
    "time_ap": "{dp} {t}", "time_absorb": ("बजे",), "dp_morning": "बिहान", "dp_noon": "दिउँसो", "dp_evening": "साँझ",
    "dp_night": "राति",
    "money": "{x} {cur}", "cur_INR": "रुपैयाँ", "sub_INR": "पैसा", "cur_USD": "डलर", "sub_USD": "सेन्ट",
    "cur_EUR": "युरो", "sub_EUR": "सेन्ट", "cur_GBP": "पाउन्ड", "sub_GBP": "पेन्स",
    "scale_thousand": "हजार", "scale_lakh": "लाख", "scale_crore": "करोड", "scale_million": "मिलियन",
    "scale_billion": "बिलियन", "scale_trillion": "ट्रिलियन",
    "scale_native": {"हजार": 1, "लाख": 1, "करोड": 1},
    "currency_native": {"रु.": "INR", "रू.": "INR"},
    "abbr_dr": "डाक्टर", "abbr_etc": "आदि", "abbr_govt": "सरकार",
    "u_hr": "घण्टा", "u_min": "मिनेट", "u_sec": "सेकेन्ड", "u_year": "वर्ष",
}
NE_ORD = {1: "पहिलो", 2: "दोस्रो", 3: "तेस्रो", 4: "चौथो", 6: "छैटौँ", 9: "नवौँ"}
def _ne_regular(words: str) -> str:
    """पाँच -> पाँचौँ, सय -> सयौँ; after a vowel sign the full vowel: साठी -> साठीऔँ (unverified)."""
    return words + ("औँ" if "\u093e" <= words[-1] <= "\u094c" else "ौँ")


NE_MARKERS = {"लो": {1}, "ली": {1}, "रो": {2, 3}, "री": {2, 3}, "स्रो": {2, 3}, "थो": {4}, "थी": {4},
              "औं": "regular", "औँ": "regular", "ौं": "regular", "ौँ": "regular"}

# ---------------------------------------------------------------------------------------------- Urdu
UR_LEX = {
    "oblique_before": ("میں", "سے", "کو", "پر", "کا", "کی", "کے", "تک", "والا", "والی", "والے"),  # ایک روپے میں
    "oblique_adj": {"آدھا": "آدھے"},  # ½ hr میں -> آدھے گھنٹے میں
    "_ord_suffix_end": {"ویں": "ے"},  # 6ویں دن -> چھٹے دن: masculine oblique (دوسرے 239 vs دوسری 130 in the text); unverified
    # ... but before a common feminine noun the feminine: 2ویں صدی -> دوسری صدی (ویں صدی and دوسری جنگ in the text); unverified
    "_ord_fem": {"marker": "ویں", "end": ("ے", "ی"),
                 "nouns": ("صدی", "جنگ", "بار", "دفعہ", "تاریخ", "منزل", "قسط", "جماعت", "ترمیم", "سالگرہ", "برسی",
                           "کلاس", "کتاب", "نشست", "پوزیشن", "شادی", "لہر")},
    "point": "اعشاریہ", "plus": "جمع", "phone_plus": "پلس", "minus": "منفی", "times": "ضرب", "divide": "تقسیم", "equals": "برابر",
    "neq": "برابر نہیں", "lt": "لیس دین", "gt": "گریٹر دین", "le": "لیس دین اور ایکول ٹو", "ge": "گریٹر دین اور ایکول ٹو",
    "pm": "جمع منفی", "approx": "تقریباً", "squared": "کا مربع", "cubed": "کا مکعب", "power": "کی طاقت {n}",
    "root": "جذر", "cuberoot": "مکعب جذر", "fourthroot": "چوتھا جذر",
    "fraction": "{a} بٹا {b}", "mixed_fraction": "{x} صحیح {f}", "fractions_special": {(1, 2): "آدھا"},
    "per": "{u} فی {p}", "percent": "{x} فیصد", "percent_word": "فیصد", "permille": "{x} فی ہزار",
    "range": "{a} سے {b}", "ratio": "{a} بہ {b}", "ratio_cue": "تناسب", "date_labels": "تاریخ",
    "year_before": r"(?:سن|سنہ|سال)", "year_after": rf"\s?(?:ء|میں|سے|تک|کے|کی|کا)(?![{ARAB}])",
    **_symbols("ڈاٹ", "سلیش", "ایٹ", "ہائفن", "انڈرسکور", "کولن", "سوالیہ نشان", "ہیش", "ٹلڈ", "سیمی کولن", "کوما",
               "ندائیہ نشان"),
    "and": "اور", "number_word": "نمبر",
    "phone_keywords": ["فون نمبر", "فون", "موبائل نمبر", "موبائل", "ہیلپ لائن"],
    "code_connectors": ["ہے"],
    "loan_squared": "اسکوائر", "loan_cubed": "کیوب", "loan_power": "پاور {n}", "loan_neq": "ناٹ ایکول ٹو", "phone_cues_after": ["پر فون کریں", "پر کال کریں"],
    "code_keywords": ["او ٹی پی", "پن کوڈ", "پن", "اکاؤنٹ نمبر", "کوڈ"],
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} بجے", "time_hm": "{h} بج کر {m} منٹ", "time_hms": "{h} بج کر {m} منٹ {s} سیکنڈ",
    "time_ap": "{dp} {t}", "time_absorb": ("بجے",), "dp_morning": "صبح", "dp_noon": "دوپہر", "dp_evening": "شام",
    "dp_night": "رات",
    "money": "{x} {cur}", "cur_INR": ("روپیہ", "روپے"), "sub_INR": ("پیسہ", "پیسے"), "cur_USD": "ڈالر",
    "sub_USD": "سینٹ", "cur_EUR": "یورو", "sub_EUR": "سینٹ", "cur_GBP": "پاؤنڈ", "sub_GBP": "پینس",
    "scale_thousand": "ہزار", "scale_lakh": "لاکھ", "scale_crore": "کروڑ", "scale_million": "ملین",
    "scale_billion": "بلین", "scale_trillion": "ٹریلین",
    "scale_native": {"ہزار": 1, "لاکھ": 1, "کروڑ": 1},
    "abbr_dr": "ڈاکٹر", "abbr_mr": "مسٹر", "abbr_etc": "وغیرہ", "abbr_govt": "حکومت", "abbr_vs": "بمقابلہ",
    "u_hr": ("گھنٹہ", "گھنٹے"), "u_min": "منٹ", "u_sec": "سیکنڈ", "u_year": "سال",
}
UR_ORD = {1: "پہل", 2: "دوسر", 3: "تیسر", 4: "چوتھ", 6: "چھٹ"}

# ---------------------------------------------------------------------------------------------- smaller languages
KOK_LEX = {
    "fractions_special": {(1, 2): "अर्द"},  # half: 20 in the text (अर्द वरान = half an hour); unverified
    "mixed_fraction": "{x} आनी {f}",  # Hindi सही: 0 in the Konkani text; आनी (and) 8384; unverified
    "u_km": "किलोमीटर",  # 30 in the text
    "point": "दशांश", "equals": "बरोबर", "percent": "{x} टक्के", "percent_word": "टक्के", "range": "{a} ते {b}",
    "and": "आनी", "time_h": "{h} वरां", "time_hm": "{h} वरां {m} मिनटां", "time_hms": "{h} वरां {m} मिनटां {s} सेकंद",
    "time_absorb": ("वरां",), "dp_morning": "सकाळीं", "dp_noon": "दनपारां", "dp_evening": "सांजे", "dp_night": "रातीं",
    "cur_INR": "रुपया", "sub_INR": "पयशे", "scale_thousand": "हजार", "scale_lakh": "लाख", "scale_crore": "कोटी",
    "scale_native": {"हजार": 1, "लाख": 1, "कोटी": 1},
}
KOK_ORD = {1: "पयल", 2: "दुसर", 3: "तिसर", 4: "चवथ"}
_kok_end = ("ो", "ी", "े")
KOK_MARKERS = {**{"ल" + e: {1} for e in _kok_end}, **{"र" + e: {2, 3} for e in _kok_end},
               **{"थ" + e: {4} for e in _kok_end}, **{"व" + e: "regular" for e in _kok_end}}

DOI_LEX = {
    "fractions_special": {(1, 2): "अद्धा"},  # half: 16 in the text (अद्धा समां); unverified
    "mixed_fraction": "{x} ते {f}",  # Hindi सही: 1 in the Dogri text; ते (and) 7145; unverified
    "percent": "{x} फीसदी", "percent_word": "फीसदी", "range": "{a} थमां {b} तगर", "and": "ते",
    "time_h": "{h} बजे", "time_hm": "{h} बजे {m} मिंट", "time_hms": "{h} बजे {m} मिंट {s} सकिंट",
    "dp_morning": "सवेरे", "dp_noon": "दपैहरी", "dp_evening": "शामीं", "dp_night": "रातीं",
    "cur_INR": "रपेऽ", "sub_INR": "पैसे", "scale_thousand": "ज्हार", "scale_lakh": "लक्ख", "scale_crore": "करोड़",
    "scale_native": {"ज्हार": 1, "लक्ख": 1, "करोड़": 1},
}
DOI_ORD = {1: "पैह्ला", 2: "दूआ", 3: "त्रीआ", 4: "चौथा"}

SD_LEX = {
    "fractions_special": {(1, 2): "अधु"},  # half: 34 in the text (अधु कलाक = half an hour); unverified
    "mixed_fraction": "{x} ऐं {f}",  # ऐं (and) 7759; unverified
    "percent": "{x} सैकिड़ो", "percent_word": "सैकिड़ो", "range": "{a} खां {b} ताईं", "and": "ऐं",
    "time_h": "{h} वॻे", "time_hm": "{h} वॻे {m} मिंट", "time_hms": "{h} वॻे {m} मिंट {s} सेकंड",
    "dp_morning": "सुबुह", "dp_noon": "मंझंद", "dp_evening": "शाम", "dp_night": "राति",
    "cur_INR": "रुपिया", "sub_INR": "पैसा", "scale_thousand": "हज़ार", "scale_lakh": "लख", "scale_crore": "करोड़",
    "scale_native": {"हज़ार": 1, "लख": 1, "करोड़": 1},
}
SD_ORD = {1: "पहिरियों", 2: "ॿियो", 3: "टियों", 4: "चोथों"}  # चोथों 6 in the text

KS_LEX = {
    "fractions_special": {(1, 2): "اوٚڑ"},  # Koul: oḍ "half"; attested (اوٚڑ گنٹہٕ = half an hour)
    "mixed_fraction": "{x} تہٕ {f}",
    "time_hour_forms": {4: "ژورِ"},  # Koul: tso:ri baji; other hours' clock forms not attested, left plain
    "percent": "{x} فیصد", "range": "{a} پیٹھ {b} تام", "and": "تہٕ",
    "time_h": "{h} بجہِ", "time_hm": "{h} بجہِ {m} منٹ", "time_hms": "{h} بجہِ {m} منٹ {s} سیکنڈ",
    "dp_morning": "صبح", "dp_noon": "دوپہر", "dp_evening": "شام", "dp_night": "راتھ",
    "cur_INR": "روپیہ", "sub_INR": "پیسہ", "scale_thousand": "ساس", "scale_lakh": "لچھ", "scale_crore": "کرور",
    "scale_native": {"ساس": 1, "لچھ": 1, "کرور": 1},
}
KS_ORD = {1: "گۄڈنیُک", 2: "دویم", 3: "ترٛیِم", 4: "ژوٗرِم", 5: "پانٛژِم", 6: "شیٚیِم"}  # 6: Koul sheyim; spelling unverified

SPECS = {
    # name: (code, script, letters, fallback, number source, lexicon, extra attributes)
    "marathi": dict(code="mr", script="Devanagari", letters=DEVA + ZW, fallback=("hindi",), cldr=True, lex=MR_LEX,
                    year_hundred="{x}शे", ord_irreg=MR_ORD, ord_markers=MR_MARKERS, ord_regular="{x}वा",
                    ord_gendered=True, ord_end="ा", glue=True,
                    mixed=dict(half1="दीड", half2="अडीच", half_pre="साडे", quarter_pre="सव्वा",
                               three_q_pre="पावणे")),
    "bengali": dict(code="bn", script="Bengali", letters=BENG + ZW, fallback=(), cldr=True, lex=BN_LEX,
                    year_hundred="{x}শো", ord_irreg=BN_SANSKRIT_ORD, ord_markers=BN_MARKERS, ord_regular="{x}তম",
                    glue=True, glue_pairs=BN_GLUE, glue_merge=("শে",), joined_thousand={2: "দুহাজার"},
                    mixed=dict(half1="দেড়", half2="আড়াই", half_pre="সাড়ে", quarter_pre="সওয়া",
                               three_q_pre="পৌনে")),
    "assamese": dict(code="as", script="Bengali", letters=BENG + ZW, fallback=("bengali",), own=True, lex=AS_LEX,
                     ord_irreg=AS_ORD, ord_markers=AS_MARKERS, ord_regular="{x}তম", glue=True, glue_pairs=AS_GLUE,
                     mixed=dict(half1="ডেৰ", half2="আঢ়ৈ", half_pre="চাৰে")),
    "gujarati": dict(code="gu", script="Gujarati", letters=GUJR + ZW, fallback=(), cldr=True, lex=GU_LEX,
                     year_hundred="{x}સો", ord_irreg=GU_ORD, ord_markers=GU_MARKERS, ord_regular="{x}મો",
                     ord_gendered=True, ord_end="ો", glue=True,
                     mixed=dict(half1="દોઢ", half2="અઢી", half_pre="સાડા", quarter_pre="સવા", three_q_pre="પોણા")),
    "punjabi": dict(code="pa", script="Gurmukhi", letters=GURU + ZW, fallback=(), cldr=True, lex=PA_LEX,
                    year_hundred="{x} ਸੌ", ord_irreg=PA_ORD, ord_markers=PA_MARKERS, ord_regular="{x}ਵਾਂ",
                    ord_gendered=True, ord_end="ਾ", glue=False,
                    mixed=dict(half1="ਡੇਢ", half2="ਢਾਈ", half_pre="ਸਾਢੇ", quarter_pre="ਸਵਾ", three_q_pre="ਪੌਣੇ")),
    "odia": dict(code="or", script="Odia", letters=ORYA + ZW, fallback=(), cldr=True, lex=OR_LEX,
                 year_hundred="{x} ଶହ", ord_irreg=OR_ORD, ord_markers=OR_MARKERS, ord_regular="{x}ତମ", glue=True,
                 mixed=dict(half1="ଦେଢ଼", half2="ଅଢ଼େଇ", half_pre="ସାଢ଼େ")),
    "nepali": dict(code="ne", script="Devanagari", letters=DEVA + ZW, fallback=("hindi",), cldr=True, lex=NE_LEX,
                   year_hundred="{x} सय", ord_irreg=NE_ORD, ord_markers=NE_MARKERS, ord_regular_fn=_ne_regular, glue=True,
                   detached=("औँ", "औं"),
                   mixed=dict(half1="डेढ", half2="अढाई", half_pre="साढे", quarter_pre="सवा", three_q_pre="पौने")),
    "urdu": dict(code="ur", script="Arabic", letters=ARAB + ZW, fallback=(), cldr=True, lex=UR_LEX,
                 year_hundred="{x} سو", ord_irreg=UR_ORD, ord_regular="{x}واں", ord_gendered=True, ord_end="ا",
                 ord_markers={"واں": "regular", "ویں": "regular"}, glue=False,
                 mixed=dict(half1="ڈیڑھ", half2="ڈھائی", half_pre="ساڑھے", quarter_pre="سوا", three_q_pre="پونے")),
    "konkani": dict(code="gom", script="Devanagari", letters=DEVA + ZW, fallback=("hindi",), own=True, lex=KOK_LEX,
                    ord_irreg=KOK_ORD, ord_markers=KOK_MARKERS, ord_regular="{x}वो", ord_gendered=True, ord_end="ो",
                    glue=True, mixed=dict(half2="अडीच")),  # अडीच वरांचेर (at 2:30), 2 in the text
    "dogri": dict(code="doi", script="Devanagari", letters=DEVA + ZW, fallback=("hindi",), own=True, lex=DOI_LEX,
                  ord_irreg=DOI_ORD, ord_regular="{x}मां", glue=False,  # पंजमां छेमां अट्ठमां नौमां दसमां: 1 each
                  mixed=dict(half1="डेढ़", half2="ढाई")),  # डेढ़ सौ, डेढ़ बजे; ढाई सौ (unverified). साढ़े is mostly "our"
    "sindhi": dict(code="sd", script="Devanagari", letters=DEVA + ZW, fallback=("hindi",), own=True, lex=SD_LEX,
                   ord_irreg=SD_ORD, ord_regular="{x}ों", glue=False,  # पंजों 1, सतों 2, अठों 3 (unverified)
                   mixed=dict(half1="ॾेढ", half2="अढाई", half_pre="साढे")),  # ॾेढ बजे, अढाई हज़ारु, साढे टी वॻे
    "kashmiri": dict(code="ks", script="Arabic", letters=ARAB + ZW, fallback=("urdu",), own=True, lex=KS_LEX,
                     ord_irreg=KS_ORD, glue=False,
                     mixed=dict(half1="ڈۄڈ", half2="ڈاے")),  # Koul ḍo:d, ḍāyi; text: ڈۄڈ ہتھ, زٕ ہتھ تہٕ ڈاے ہتھ
}

HINDI_BELT = {"maithili": "mai", "bhojpuri": "bho", "magahi": "mag", "chhattisgarhi": "hne"}
# Hindi phrases these languages may use as they are: the clock word बजे is attested in all four; से (range) is
# common in Bhojpuri and Magahi text. Maithili and Chhattisgarhi get their own range postposition (all unverified).
_CLOCK = {"time_h", "time_hm", "time_hms"}
HINDI_BELT_GRAMMAR = {"bhojpuri": _CLOCK | {"range"}, "magahi": _CLOCK | {"range"}, "maithili": _CLOCK,
                      "chhattisgarhi": _CLOCK}
HINDI_BELT_LEX = {"maithili": {"range": "{a} सँ {b}",  # सँ 1218 vs से 428 per million chars
                               "cur_INR": "रुपैया"},  # रुपैया 97 vs रुपये 2 (Grierson: rupaiā)
                  "chhattisgarhi": {"range": "{a} ले {b}"}}  # ले 3260 per million chars


# ordinals as each language's own text writes them (counts in the training text):
# Bhojpuri पहिला 591 vs पहला 34; Magahi पहिला 292 vs पहला 246; Chhattisgarhi पहिला 66 vs पहला 21; 2nd-6th stay Hindi.
# Maithili: पहिल 900, दोसर 849, तेसर 152, चारिम 75, छठम 39; regular = cardinal + म (पाँचम 35, सातम 57, आठम 60, दसम 51)
# whole irregular words that are not stem + ा: Bhojpuri छठवाँ 12 vs छठा 2 (Census: chAThAwã); Chhattisgarhi छठवां 21 vs 5
HINDI_BELT_ORD_WHOLE = {"bhojpuri": {6: "छठवाँ"}, "chhattisgarhi": {6: "छठवां"}}
HINDI_BELT_ORD = {"bhojpuri": {1: "पहिल"}, "magahi": {1: "पहिल"}, "chhattisgarhi": {1: "पहिल"},
                  "maithili": {1: "पहिल", 2: "दोसर", 3: "तेसर", 4: "चारिम", 6: "छठम"}}


def _make_hindi_belt(name: str) -> Lang:
    lang = Hindi()
    lang.name, lang.code = name, HINDI_BELT[name]
    words = list(HINDI_BELOW100)
    for k, v in TABLES["hindi_belt_overrides"].get(name, {}).items():
        words[int(k)] = v
    lang.below100 = words
    lang.fallback = ("hindi",)
    layer = cldr_layer(name) or {}
    lang.lex = {k: v for k, v in layer.items() if k == "months"}
    lang.lex.update(HINDI_BELT_LEX.get(name, {}))
    lang.borrow_grammar = frozenset(HINDI_BELT_GRAMMAR[name] | {"fractions_special"})  # Hindi आधा, तीन चौथाई
    lang.ord_irreg = {**ORD_IRREG, **HINDI_BELT_ORD[name]}
    lang.ord_whole = HINDI_BELT_ORD_WHOLE.get(name, {})
    for k in lang.ord_whole:
        lang.ord_irreg.pop(k, None)
    if name == "maithili":
        lang.ord_irreg = HINDI_BELT_ORD[name]
        lang.ord_plain, lang.ord_reg_suffix = True, "म"
    return lang


def make(name: str) -> Lang:
    if name in HINDI_BELT:
        return _make_hindi_belt(name)
    spec = SPECS[name]
    lang = IndoAryan()
    lang.name, lang.code, lang.script = name, spec["code"], spec["script"]
    lang.letters = spec["letters"]
    lang.fallback = spec["fallback"]
    lang.glue_unknown_suffix = spec.get("glue", False)
    if spec.get("cldr"):
        lang.below100 = _cldr_below100(name)
        lang.hundreds = _cldr_hundreds(name)
        lang.thousand, lang.lakh, lang.crore = (_cldr_scale(name, k) for k in ("thousand", "lakh", "crore"))
    else:
        t = TABLES["own"][name]
        lang.below100 = t["below100"]
        if "hundreds" in t:
            lang.hundreds = [tuple(x) if isinstance(x, list) else x for x in t["hundreds"]]
        lang.hundred = t.get("hundred", "")
        lang.thousand, lang.lakh, lang.crore = t["thousand"], t["lakh"], t["crore"]
    assert len(lang.below100) == 100 and all(lang.below100[:10]), name  # digits are always readable
    lang.year_hundred = spec.get("year_hundred", "")
    lang.ord_irreg = spec.get("ord_irreg", {})
    lang.ord_markers = spec.get("ord_markers", {})
    lang.ord_regular = spec.get("ord_regular", "")
    lang.ord_gendered = spec.get("ord_gendered", False)
    if spec.get("ord_regular_fn"):
        lang.ord_regular_fn = spec["ord_regular_fn"]  # instance attribute: called unbound
    lang.glue_pairs = spec.get("glue_pairs", {})
    lang.glue_merge = spec.get("glue_merge", ())
    lang.joined_thousand = spec.get("joined_thousand", {})
    lang.detached_suffixes = spec.get("detached", ())
    lang.mixed = spec.get("mixed", {})
    lex = {**cldr_layer(name), **spec["lex"]}
    if spec.get("ord_end"):
        lex["_ord_default_end"] = spec["ord_end"]
    lex.setdefault("money_join", " ")
    lex.setdefault("money", "{x} {cur}")
    lex.setdefault("date", "{d} {month} {y}")
    lex.setdefault("date_dm", "{d} {month}")
    lex.setdefault("date_my", "{month} {y}")
    lex.setdefault("time_ap", "{dp} {t}")
    lang.lex = lex
    return lang
