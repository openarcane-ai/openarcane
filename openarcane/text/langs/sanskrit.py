"""Sanskrit (Devanagari).

Numbers 0-99 are neuter citation forms from data/indic_number_tables.json, kept only where they occur in the
Sanskrit training text (unattested ones, e.g. 81-89, make the number read digit by digit). 100-99,999 follow the
compound style the training text uses for years and amounts: the remainder + अधिक in front of the round part,
hundreds joined to thousands with उत्तर (corpus: सप्तदशाधिकद्विसहस्रतमे, सप्तत्यधिकनवशतोत्तरैकसहस्रतमे).
So 2025 -> पञ्चविंशत्यधिकद्विसहस्रं, 105 -> पञ्चाधिकशतं, 1970 -> सप्तत्यधिकनवशतोत्तरैकसहस्रं. Numbers from
1,00,000 up are read digit by digit (लक्षं/कोटि are rare in the text and their composition is not attested).
Case endings are not inflected: the nominative/accusative neuter form is used everywhere.
"""
from __future__ import annotations

from . import cldr_layer
from .indo_aryan import DEVA, DIGIT_FALLBACK_HITS, TABLES, ZW, IndoAryan, _Gap

T = TABLES["own"]["sanskrit"]

# compound (pre-noun) stems of the citation forms
_STEM = {"एकं": "एक", "द्वे": "द्वि", "त्रीणि": "त्रि", "चत्वारि": "चतुर्", "षट्": "षड्"}
ORD = {1: "प्रथमः", 2: "द्वितीयः", 3: "तृतीयः", 4: "चतुर्थः", 5: "पञ्चमः", 6: "षष्ठः", 7: "सप्तमः", 8: "अष्टमः",
       9: "नवमः", 10: "दशमः"}


def stem(word: str) -> str:
    """citation form -> compound stem: विंशतिः -> विंशति, एकं -> एक, चत्वारि -> चतुर्."""
    if word in _STEM:
        return _STEM[word]
    if word.endswith(("ः", "ं")):
        return word[:-1]
    return word


def adhika(word: str) -> str:
    """stem + अधिक with vowel sandhi: पञ्च -> पञ्चाधिक, विंशति -> विंशत्यधिक, त्रिंशत् -> त्रिंशदधिक,
    चतुर् -> चतुरधिक, षड् -> षडधिक."""
    s = stem(word)
    if s.endswith("त्"):
        return s[:-2] + "दधिक"
    if s.endswith("्"):  # चतुर्, षड्
        return s[:-1] + "धिक"
    if s.endswith(("ि", "ी")):
        return s[:-1] + "्यधिक"
    return s + "ाधिक"


def _join(left: str, right: str) -> str:
    """a-final compound member + ए-initial one: अधिक + एक -> अधिकैक, उत्तर + एक -> उत्तरैक."""
    if right.startswith("ए"):
        return left + "ै" + right[1:]
    return left + right


class Sanskrit(IndoAryan):
    def _mult(self, k: int) -> str:
        """multiplier stem for 1..99 in front of शत / सहस्र."""
        if k < 10:
            return ["", "एक"][k] if k < 2 else T["hundred_prefix"][k - 1]
        return stem(self._w(k))

    def cardinal(self, n: int) -> str:
        if n < 100:
            return self._w(n)
        if n == 10**5:
            return "लक्षं"  # exactly one lakh: 3 in the text (Whitney); other lakh compositions stay digits
        if n >= 10**5:
            raise _Gap(n)
        th, rest = divmod(n, 1000)
        h, r = divmod(rest, 100)
        base = ""
        if h:
            base = (T["hundred_prefix"][h - 1] if h > 1 else "") + T["hundred"]
        if th:
            thousands = (self._mult(th) if th > 1 or base else "") + T["thousand"]
            base = _join(base + "ोत्तर", thousands) if base else thousands  # नवशत + उत्तर + एकसहस्र
        if r:
            base = _join(adhika(self._w(r)), base)
        return base + "ं"

    def ordinal(self, n: int) -> str:
        """1-10 from the table; 11-19 (-दश) + ः (एकादशः); otherwise stem + तमः (विंशतितमः, शततमः)."""
        if n in ORD:
            return ORD[n]
        try:
            card = self.cardinal(n)
        except _Gap:
            return self.say_int(n)  # digit by digit: no ordinal form can be built
        if card.endswith("दश"):
            return card + "ः"
        return stem(card) + "तमः"

    def mixed_fraction(self, whole: int, a: int, b: int):
        """x½ -> सार्ध + stem, the compound the training text uses (सार्धत्रिवर्ष, सार्धैकशततम); unverified."""
        if (a, b) != (1, 2):
            return None
        try:
            return _join("सार्ध", stem(self.cardinal(whole)))
        except _Gap:
            return None

    def attach(self, words: str, suffix: str, n: int | None = None) -> str:
        """compound with a following noun: चत्वारि + वादने -> चतुर्वादने, एकं + वादने -> एकवादने."""
        head, sp, last = words.rpartition(" ")
        return head + sp + stem(last) + suffix


SA_LEX = {
    "point": "दशमलव", "neg": "ऋण",  # ऋण 135 in the text, माइनस 0 (unverified as a sign word)
    "fractions_special": {(1, 2): "अर्धम्", (1, 4): "पादः"}, "mixed_fraction": "{x} च {f}",
    "percent": "{x} प्रतिशतं", "percent_word": "प्रतिशतं", "range": "{a} आरभ्य {b} यावत्", "and": "च",
    "time_h": "{h+वादने}", "time_hm": "{h+वादने} {m} निमेषाः", "time_absorb": ("वादने",),
    "dp_morning": "प्रातः", "dp_noon": "मध्याह्ने", "dp_evening": "सायं", "dp_night": "रात्रौ",
    "cur_INR": "रूप्यकाणि", "u_hr": "घण्टाः", "u_min": "निमेषाः",
    "date_labels": "दिनाङ्कः",
    "scale_thousand": "सहस्रं", "scale_lakh": "लक्षं", "scale_crore": "कोटि",
    "scale_native": {"सहस्रं": 1, "लक्षं": 1, "कोटि": 1},
}


def make(name="sanskrit"):
    lang = Sanskrit()
    lang.name, lang.code, lang.script = name, "sa", "Devanagari"
    lang.letters = DEVA + ZW
    lang.fallback = ("hindi",)
    lang.glue_unknown_suffix = False
    lang.below100 = T["below100"]
    assert len(lang.below100) == 100 and all(lang.below100[:10])
    lex = {**cldr_layer(name), **SA_LEX}
    lex.setdefault("money", "{x} {cur}")
    lex.setdefault("date", "{d} {month} {y}")
    lex.setdefault("date_dm", "{d} {month}")
    lex.setdefault("date_my", "{month} {y}")
    lex.setdefault("time_ap", "{dp} {t}")
    lang.lex = lex
    return lang


__all__ = ["make", "Sanskrit", "DIGIT_FALLBACK_HITS"]
