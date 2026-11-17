"""Hindi (Devanagari). Base lexicon for the Hindi-belt languages that fall back to it."""
from __future__ import annotations

from . import cldr_layer
from .base import Lang, table_cardinal

BELOW100 = (
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ "
    "दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
    "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस "
    "तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस "
    "चालीस इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास "
    "पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ "
    "साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर "
    "सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उनासी "
    "अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी "
    "नब्बे इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे"
).split()
assert len(BELOW100) == 100

# irregular ordinals: masculine stem + (ा / ी / े)
ORD_IRREG = {1: "पहल", 2: "दूसर", 3: "तीसर", 4: "चौथ", 6: "छठ"}
ORD_SUFFIXES = {"वाँ", "वां", "वा", "वीं", "वी", "वें", "वे", "ला", "ली", "ले", "रा", "री", "रे", "था", "थी", "थे",
                "ठा", "ठी", "ठे"}


class Hindi(Lang):
    script = "Devanagari"
    letters = "ऀ-ॣ॰-ॿ꣠-ꣿ"
    below100 = BELOW100
    hundred, thousand, lakh, crore = "सौ", "हजार", "लाख", "करोड़"
    ord_irreg = ORD_IRREG
    ord_suffixes = ORD_SUFFIXES

    def cardinal(self, n: int) -> str:
        return table_cardinal(self, n, self.below100, self.hundred, self.thousand, self.lakh, self.crore)

    def digit(self, d):
        return self.below100[d]

    ord_plain = False  # irregular ordinals are whole words (Maithili पहिल, दोसर), not stems + ा/ी/े
    ord_reg_suffix = "वाँ"
    ord_whole: dict = {}  # n -> whole ordinal word that takes no gender ending (Bhojpuri छठवाँ)

    def ordinal_from_suffix(self, n, suffix):
        if suffix not in self.ord_suffixes:
            return None
        if n in self.ord_whole:
            return self.ord_whole[n]
        if self.ord_plain:
            return self.ordinal(n) if (n in self.ord_irreg or suffix[0] in "वब") else None
        end = suffix[-1] if suffix[-1] in "ाीे" else ("ी" if "ी" in suffix else ("े" if "े" in suffix else "ा"))
        if n in self.ord_irreg:
            return self.ord_irreg[n] + end
        if suffix[0] in "वब":
            return self.say_int(n) + suffix
        return None

    def ordinal(self, n):
        if n in self.ord_whole:
            return self.ord_whole[n]
        if n in self.ord_irreg:
            return self.ord_irreg[n] + ("" if self.ord_plain else "ा")
        return self.say_int(n) + self.ord_reg_suffix

    year_style = True

    def year(self, n):
        """1100-1999 are read in hundreds (उन्नीस सौ अट्ठानवे); other years as cardinals."""
        if 1100 <= n <= 1999:
            hi, lo = divmod(n, 100)
            return f"{self.below100[hi]} {self.hundred}" + (f" {self.below100[lo]}" if lo else "")
        return self.say_int(n)

    def mixed_fraction(self, whole, a, b):
        if (a, b) == (1, 2):
            return {1: "डेढ़", 2: "ढाई"}.get(whole) or f"साढ़े {self.say_int(whole)}"
        if (a, b) == (1, 4):
            return f"सवा {self.say_int(whole)}"
        if (a, b) == (3, 4):
            return f"पौने {self.say_int(whole + 1)}"
        return None


HINDI_LEX = {
    "oblique_before": ("में", "से", "को", "पर", "का", "की", "के", "तक", "वाला", "वाली", "वाले"),  # एक रुपये में, एक घंटे में (REVIEW_NEEDED)
    "oblique_adj": {"आधा": "आधे"},  # ½ hr में -> आधे घंटे में
    "point": "दशमलव", "minus": "माइनस", "plus": "प्लस", "times": "गुणा", "divide": "भाग", "equals": "बराबर",
    "neq": "बराबर नहीं", "lt": "लेस दैन", "gt": "ग्रेटर दैन", "le": "लेस दैन ऑर इक्वल टू",
    "ge": "ग्रेटर दैन ऑर इक्वल टू", "pm": "प्लस माइनस", "approx": "लगभग", "squared": "का वर्ग",
    "cubed": "का घन", "power": "की घात {n}", "root": "रूट", "cuberoot": "क्यूब रूट", "fourthroot": "फोर्थ रूट",
    "fraction": "{a} बटा {b}", "mixed_fraction": "{x} सही {f}",
    "fractions_special": {(1, 2): "आधा", (1, 4): "एक चौथाई", (3, 4): "तीन चौथाई", (1, 3): "एक तिहाई",
                          (2, 3): "दो तिहाई"},
    "per": "{u} प्रति {p}",
    "qty_words": ("किलो", "रुपए", "रु"),  # written quantity words that are not unit names: 5 किलो-3 किलो=2 किलो
    "year_before": r"(?:सन्|सन|वर्ष|साल|ईस्वी)", "year_after": r"\s?(?:में|से|तक|के|की|का|ई\.|ई॰|ईस्वी)(?![ऀ-ॣ])",
    "percent": "{x} प्रतिशत", "percent_word": "प्रतिशत", "range": "{a} से {b}", "ratio": "{a} अनुपात {b}",
    "dot": "डॉट", "slash": "स्लैश", "at": "एट", "hyphen": "हाइफ़न", "underscore": "अंडरस्कोर", "colon": "कोलन",
    "question": "क्वेश्चन मार्क", "hash": "हैश", "tilde": "टिल्डे", "semicolon": "सेमीकोलन", "comma": "कॉमा", "exclamation": "एक्सक्लेमेशन मार्क",
    "permille": "{x} प्रति हज़ार", "ratio_cue": "अनुपात", "date_labels": "दिनांक|तारीख|तिथि",
    "phone_keywords": ["कॉल करें", "फ़ोन नंबर", "फोन नंबर", "फ़ोन", "फोन", "मोबाइल नंबर", "मोबाइल", "हेल्पलाइन नंबर", "हेल्पलाइन"],
    "month_aliases": {"फरवरी": 2, "अप्रेल": 4, "सितम्बर": 9, "अक्टूबर": 10, "अक्तूबर": 10, "नवम्बर": 11, "दिसम्बर": 12}, "and": "और", "number_word": "नंबर",
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} बजे", "time_hm": "{h} बजकर {m} मिनट", "time_hms": "{h} बजकर {m} मिनट {s} सेकंड",
    "time_ap": "{dp} {t}", "time_absorb": ("बजे",), "dp_morning": "सुबह", "dp_noon": "दोपहर", "dp_evening": "शाम", "dp_night": "रात",
    "money": "{x} {cur}", "money_join": " ",
    "cur_INR": ("रुपया", "रुपये"), "sub_INR": ("पैसा", "पैसे"), "cur_USD": "डॉलर", "sub_USD": "सेंट",
    "cur_EUR": "यूरो", "sub_EUR": "सेंट", "cur_GBP": "पाउंड", "sub_GBP": "पेंस",
    "scale_thousand": "हजार", "scale_lakh": "लाख", "scale_crore": "करोड़", "scale_million": "मिलियन",
    "scale_billion": "बिलियन", "scale_trillion": "ट्रिलियन",
    "scale_native": {"हज़ार": 1, "हजार": 1, "लाख": 1, "करोड़": 1, "करोड": 1},
    "currency_native": {"रु.": "INR", "रु": "INR", "रू.": "INR"},
    "code_connectors": ["है", "हैं", "नंबर", "नम्बर"],
    # bare loanwords for languages that borrow the concept but not Hindi grammar (का वर्ग, नहीं)
    "loan_squared": "स्क्वेयर", "loan_cubed": "क्यूब", "loan_power": "पावर {n}", "loan_neq": "नॉट इक्वल टू",
    "phone_cues_after": ["पर फोन करें", "पर फ़ोन करें", "पर कॉल करें", "पर फोन करो", "पर कॉल करो"],
    "code_keywords": ["ओटीपी", "पिन कोड", "पिनकोड", "पिन", "खाता संख्या", "खाता नंबर", "अकाउंट नंबर", "आधार नंबर",
                      "कोड"],
    "unit_abbr": {"कि.मी.": "km", "कि.मी": "km", "किमी": "km", "कि.ग्रा.": "kg", "किग्रा": "kg", "ग्रा.": "g",
                  "से.मी.": "cm", "मि.मी.": "mm", "मि.ली.": "ml", "ली.": "l"},
    "abbr_native": {"डॉ.": "डॉक्टर", "कि.मी.": "किलोमीटर"},
    "abbr_dr": "डॉक्टर", "abbr_mr": "मिस्टर", "abbr_mrs": "मिसेज़", "abbr_ms": "मिस", "abbr_prof": "प्रोफ़ेसर",
    "abbr_etc": "इत्यादि", "abbr_vs": "बनाम", "abbr_govt": "सरकार", "abbr_approx": "लगभग",
    "abbr_eg": "उदाहरण के लिए", "abbr_ie": "यानी", "abbr_jr": "जूनियर", "abbr_sr": "सीनियर", "abbr_ltd": "लिमिटेड",
    "abbr_pvt": "प्राइवेट", "abbr_dept": "विभाग",
    "u_hr": ("घंटा", "घंटे"), "u_min": "मिनट", "u_sec": "सेकंड", "u_year": "साल", "u_quintal": "क्विंटल",
    "u_kmpl": "किलोमीटर प्रति लीटर", "u_bhp": "बीएचपी", "u_rpm": "आरपीएम", "u_dB": "डेसिबल", "u_kl": "किलोलीटर",
    "u_cc": "सीसी", "u_Wh": "वाट घंटा", "u_kV": "किलोवोल्ट", "u_mAh": "मिलीएम्पियर घंटा",
}


def make(name="hindi"):
    lang = Hindi()
    lang.name, lang.code = "hindi", "hi"
    lang.lex = {**cldr_layer("hindi"), **HINDI_LEX}
    return lang
