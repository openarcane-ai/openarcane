"""Telugu. Composition follows CLDR RBNF te (main @ 3d45043) with three deliberate changes, all checked against
the training corpus: standalone multiples take the plural (రెండు వేలు 114 hits, CLDR రెండు వేల), multiplier 1
inside a scale is ఒక (ఇరవై ఒక్క వేలు, not ఇరవై ఒకటి వేల), and crore recurses instead of అరబ్/ఖరబ్."""
from __future__ import annotations

from . import cldr_layer
from .base import Lang

UNITS = ["సున్నా", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు", "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది"]
TEENS = ["పది", "పదకొండు", "పన్నెండు", "పదమూడు", "పద్నాలుగు", "పదిహేను", "పదహారు", "పదిహేడు", "పద్దెనిమిది",
         "పంతొమ్మిది"]
TENS = ["", "", "ఇరవై", "ముప్పై", "నలభై", "యాభై", "అరవై", "డెబ్బై", "ఎనభై", "తొంభై"]

U, I, AI = "ు", "ి", "ై"
VOWEL_SIGNS = set("\u0C3E\u0C3F\u0C40\u0C41\u0C42\u0C43\u0C46\u0C47\u0C48\u0C4A\u0C4B\u0C4C")


def below100(n: int) -> str:
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEENS[n - 10]
    t, o = divmod(n, 10)
    return TENS[t] + (f" {UNITS[o]}" if o else "")


def multiplier(n: int) -> str:
    """Number in front of a scale word: 1 -> ఒక, 21 -> ఇరవై ఒక్క."""
    if n == 1:
        return "ఒక"
    w = below100(n) if n < 100 else Telugu().cardinal(n)
    return w[: -len("ఒకటి")] + "ఒక్క" if w.endswith(" ఒకటి") else w


class Telugu(Lang):
    name, code, script = "telugu", "te", "Telugu"
    letters = "ఀ-౿‌‍"
    glue_unknown_suffix = True
    # endings written after a space that join the number word; the free postpositions నుంచి/నుండి/వరకు keep their space
    detached_suffixes = ("వ", "వది", "న", "లో", "కి", "కు", "గా")

    def cardinal(self, n: int) -> str:
        if n < 100:
            return below100(n)
        parts = []  # (standalone, combining)
        cr, rest = divmod(n, 10**7)
        if cr:
            parts.append(("ఒక కోటి", "ఒక కోటి") if cr == 1 else
                         (f"{multiplier(cr)} కోట్లు", f"{multiplier(cr)} కోట్ల"))
        lk, rest = divmod(rest, 10**5)
        if lk:
            parts.append(("ఒక లక్ష", "ఒక లక్ష") if lk == 1 else
                         (f"{multiplier(lk)} లక్షలు", f"{multiplier(lk)} లక్షల"))
        th, rest = divmod(rest, 1000)
        if th:
            parts.append(("వెయ్యి", "వెయ్యి") if th == 1 else (f"{multiplier(th)} వేలు", f"{multiplier(th)} వేల"))
        h, rest = divmod(rest, 100)
        if h:
            parts.append(("వంద", "నూట") if h == 1 else (f"{UNITS[h]} వందలు", f"{UNITS[h]} వందల"))
        if rest:
            parts.append((below100(rest), below100(rest)))
        return " ".join([c for _, c in parts[:-1]] + [parts[-1][0]])

    def digit(self, d: int) -> str:
        return UNITS[d]

    def attach(self, words: str, suffix: str, n: int | None = None) -> str:
        if suffix in ("వ", "వది", "వ.", "వదైన"):  # ordinal: మూడు -> మూడవ, ఎనిమిది -> ఎనిమిదవ, ఇరవై -> ఇరవయ్యవ
            if words.endswith((U, I)):
                return words[:-1] + suffix
            if words.endswith(AI):
                return words[:-1] + "య్య" + suffix
            return words + suffix
        if words.endswith("లు") and suffix in ("కి", "కు", "లో"):  # నిమిషాలు + కి -> నిమిషాలకు
            return words[:-1] + ("్లో" if suffix == "లో" else "కు")
        if suffix[:1] in VOWEL_SIGNS and words.endswith((U, I)):  # నాలుగు + ింట -> నాలుగింట
            return words[:-1] + suffix
        return words + suffix

    def adj(self, words: str) -> str:
        for a, b in ((" వేలు", " వేల"), (" లక్షలు", " లక్షల"), (" కోట్లు", " కోట్ల"), (" వందలు", " వందల")):
            if words.endswith(a):
                return words[: -len(a)] + b
        if words == "ఒకటి" or words.endswith(" ఒకటి"):
            return words[:-len("ఒకటి")] + ("ఒక" if words == "ఒకటి" else "ఒక్క")
        return words

    def ordinal(self, n: int) -> str:
        # "1st" -> మొదటి (787 hits in the Telugu text vs ఒకటవ 33); a written 1వ still gives ఒకటవ. REVIEW_NEEDED
        return "మొదటి" if n == 1 else self.attach(self.say_int(n), "వ")

    def say_fraction(self, a, b, a_words=None, b_words=None):
        """1/20 -> ఇరవై భాగాల్లో ఒక భాగం: the contracted {b+ింట} form only after a -u/-i final (REVIEW_NEEDED)"""
        special = (self.w("fractions_special", {}) or {}).get((a, b))
        bw = b_words or self.say_int(b)
        if special or bw.endswith((U, I)):
            return super().say_fraction(a, b, a_words, b_words)
        aw = a_words or self.say_int(a)
        return f"{bw} భాగాల్లో {self.adj(aw)} {'భాగం' if a == 1 else 'భాగాలు'}"

    def mixed_fraction(self, whole, a, b):
        """2½ -> రెండున్నర (attested: రెండున్నర 18, ఒకటిన్నర 8, మూడున్నర 5, పదిన్నర 3)."""
        w = self.say_int(whole)
        if (a, b) == (1, 2) and w.endswith((U, I)):
            return w + "న్నర"
        return None

    def say_time(self, h, m, s, ap):
        """Clock time with singular nouns for one: ఒంటి గంట (1 o'clock), ఒక నిమిషం. REVIEW_NEEDED."""
        num = lambda x: self.adj(self.say_int(x))
        if s is None and m == 0:
            t = "ఒంటి గంట" if h == 1 else f"{num(h)} గంటలు"
        else:
            hour = "ఒంటి గంట" if h == 1 else f"{num(h)} గంటల"
            if s is None:
                t = f"{hour} " + ("ఒక నిమిషం" if m == 1 else f"{num(m)} నిమిషాలు")
            else:
                mins = "ఒక నిమిషం" if m == 1 else f"{num(m)} నిమిషాల"
                t = f"{hour} {mins} " + ("ఒక సెకను" if s == 1 else f"{num(s)} సెకన్లు")
        if ap:
            t = self.fill(self.w("time_ap"), t=t, dp=self.daypart(h, ap))
        return t


TELUGU_LEX = {
    "point": "పాయింట్", "minus": "మైనస్", "plus": "ప్లస్", "times": "ఇంటు", "divide": "భాగించు", "equals": "సమానం",
    "neq": "సమానం కాదు", "lt": "లెస్ దాన్", "gt": "గ్రేటర్ దాన్", "le": "లెస్ దాన్ ఆర్ ఈక్వల్ టు",
    "ge": "గ్రేటర్ దాన్ ఆర్ ఈక్వల్ టు", "pm": "ప్లస్ మైనస్", "approx": "సుమారు", "squared": "స్క్వేర్",
    "cubed": "క్యూబ్", "power": "టు ది పవర్ {n}", "root": "రూట్", "cuberoot": "క్యూబ్ రూట్", "fourthroot": "ఫోర్త్ రూట్",
    "fraction": "{b+ింట} {a}", "mixed_fraction": "{x} పూర్ణాంకం {f}",
    "fractions_special": {(1, 2): "అర", (1, 4): "పావు", (3, 4): "ముప్పావు"},
    "per": "{u} పర్ {p}", "percent": "{x} శాతం", "percent_word": "శాతం", "range": "{a} నుంచి {b}", "ratio": "{a} నిష్పత్తి {b}",
    "dot": "డాట్", "slash": "స్లాష్", "at": "ఎట్", "hyphen": "హైఫన్", "underscore": "అండర్‌స్కోర్", "colon": "కోలన్",
    "question": "క్వశ్చన్ మార్క్", "hash": "హ్యాష్", "tilde": "టిల్డ్", "semicolon": "సెమీకోలన్", "comma": "కామా", "exclamation": "ఆశ్చర్యార్థక గుర్తు",
    "permille": "వెయ్యికి {x}", "ratio_cue": "నిష్పత్తి", "date_labels": "తేదీ",
    "phone_keywords": ["ఫోన్ నంబర్", "ఫోన్", "మొబైల్ నంబర్", "మొబైల్", "హెల్ప్‌లైన్"], "and": "మరియు", "number_word": "నంబర్",
    "date": "{d} {month} {y}", "date_dm": "{d} {month}", "date_my": "{month} {y}",
    "time_h": "{h} గంటలు", "time_hm": "{h} గంటల {m} నిమిషాలు", "time_hms": "{h} గంటల {m} నిమిషాల {s} సెకన్లు",
    "time_ap": "{dp} {t}", "dp_morning": "ఉదయం", "dp_noon": "మధ్యాహ్నం", "dp_evening": "సాయంత్రం", "dp_night": "రాత్రి",
    "money": "{x} {cur}", "money_join": " ",
    "cur_INR": ("రూపాయి", "రూపాయలు"), "sub_INR": ("పైసా", "పైసలు"), "cur_USD": ("డాలర్", "డాలర్లు"),
    "sub_USD": ("సెంటు", "సెంట్లు"), "cur_EUR": ("యూరో", "యూరోలు"), "sub_EUR": ("సెంటు", "సెంట్లు"),
    "cur_GBP": ("పౌండ్", "పౌండ్లు"), "sub_GBP": ("పెన్నీ", "పెన్స్"),
    "scale_thousand": "వేలు", "scale_lakh": "లక్షలు", "scale_crore": "కోట్లు", "scale_million": "మిలియన్",
    "scale_billion": "బిలియన్", "scale_trillion": "ట్రిలియన్",
    "scale_native": {"వేలు": 1, "వేల": 1, "లక్షలు": 1, "లక్షల": 1, "లక్ష": 1, "కోట్లు": 1, "కోట్ల": 1, "కోటి": 1},
    "currency_native": {"రూ.": "INR", "రూ": "INR"},
    "dp_evening_until": 7,  # రాత్రి ఏడు (4) vs సాయంత్రం ఏడు (0)
    "time_absorb_case": {"గంటలకు": "కు", "గంటకు": "కు"},  # 10:30 గంటలకు -> ... నిమిషాలకు (REVIEW_NEEDED)
    "code_connectors": ["నంబర్", "సంఖ్య"],
    "code_keywords": ["ఓటీపీ", "ఓటిపి", "పిన్ కోడ్", "పిన్", "ఖాతా నంబర్", "ఖాతా సంఖ్య", "ఆధార్ నంబర్", "కోడ్"],
    "unit_abbr": {"కి.మీ.": "km", "కి.మీ": "km", "కిమీ": "km", "కేజీ": "kg", "కిలో": "kg", "కి.గ్రా.": "kg",
                  "గ్రా.": "g", "సెం.మీ.": "cm", "మి.మీ.": "mm", "మీ.": "m", "లీ.": "l"},
    "abbr_native": {"డా.": "డాక్టర్", "శ్రీ.": "శ్రీ", "కి.మీ.": "కిలోమీటర్లు"},
    "abbr_dr": "డాక్టర్", "abbr_mr": "మిస్టర్", "abbr_mrs": "మిసెస్", "abbr_ms": "మిస్", "abbr_prof": "ప్రొఫెసర్",
    "abbr_etc": "మొదలైనవి", "abbr_vs": "వర్సెస్", "abbr_govt": "ప్రభుత్వం", "abbr_approx": "సుమారు",
    "abbr_eg": "ఉదాహరణకు", "abbr_ie": "అంటే", "abbr_jr": "జూనియర్", "abbr_sr": "సీనియర్", "abbr_ltd": "లిమిటెడ్",
    "abbr_pvt": "ప్రైవేట్", "abbr_dept": "శాఖ",
    "u_min": ("నిమిషం", "నిమిషాలు"), "u_hr": ("గంట", "గంటలు"), "u_sec": ("సెకను", "సెకన్లు"), "u_year": ("సంవత్సరం", "సంవత్సరాలు"),
    "u_kmph": ("గంటకు {x} కిలోమీటరు", "గంటకు {x} కిలోమీటర్లు"), "u_quintal": "క్వింటాళ్లు", "u_kmpl": "కిలోమీటర్లు పర్ లీటర్", "u_bhp": "బీహెచ్‌పీ",
    "u_rpm": "ఆర్‌పీఎం", "u_dB": "డెసిబెల్స్", "u_kl": "కిలోలీటర్లు", "u_cc": "సీసీ", "u_Wh": "వాట్ అవర్",
    "u_kV": "కిలోవోల్టులు", "u_mAh": "మిల్లీ ఆంపియర్ అవర్",
}


def make(name="telugu"):
    lang = Telugu()
    lang.lex = {**cldr_layer("telugu"), **TELUGU_LEX}
    return lang
