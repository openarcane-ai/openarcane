"""Language base class: number words, lexicon with fallback chain, sandhi-aware templates."""
from __future__ import annotations

import re
from collections import Counter

# (language, concept, source-language) -> count, filled whenever a concept is borrowed from a
# fallback language. Used by the coverage report; never affects output.
FALLBACK_HITS: Counter = Counter()

_TPL = re.compile(r"\{(\w+)(?:\+([^}]*))?\}")

MAX_CARDINAL = 10**15  # above this, numbers are read digit by digit


# templates whose fallback wording contains grammar (postpositions, verb forms), not just a loanword. A language
# borrows them only when listed in its `borrow_grammar`; otherwise it gets the fallback's `loan_<key>` (a bare
# loanword such as स्क्वेयर) or the concept is missing.
GRAMMAR_KEYS = frozenset({"squared", "cubed", "power", "range", "time_h", "time_hm", "time_hms", "abbr_eg", "abbr_ie",
                          "neq", "fractions_special"})  # fractions_special holds number words (तीन चौथाई)


class MissingWord(LookupError):
    """A concept has no word in the language or its fallbacks. The engine drops the rule that needed it and
    tries the next one, so the span is read more plainly (e.g. `5%` -> number word + `%` kept) instead of
    borrowing a word from an unrelated language."""


class Lang:
    name = "base"
    code = "xx"
    script = "Latin"
    # regex character class (without brackets) matching letters + marks of the native script;
    # used to detect suffixes written directly after digits. Empty = no suffix handling.
    letters = ""
    # suffix tokens that may follow a number after ONE space and still belong to it
    detached_suffixes: tuple[str, ...] = ()
    # glue an unknown native suffix to the number (Dravidian case endings) or keep a space
    glue_unknown_suffix = False
    comma = ", "
    fallback: tuple[str, ...] = ()  # language names whose lexicon fills gaps, in order
    borrow_grammar: frozenset = frozenset()  # GRAMMAR_KEYS this language may take from its fallback as they are
    lex: dict = {}
    registry: dict = {}  # filled by langs/__init__.py: name -> instance

    # ------------------------------------------------------------------ lexicon
    def w(self, key: str, default: str | None = None):
        if key in self.lex:
            return self.lex[key]
        for fb in self.fallback:
            other = self.registry.get(fb)
            if other is None:
                continue
            if key in GRAMMAR_KEYS and key not in self.borrow_grammar:
                # the fallback's phrase carries its own grammar (Hindi का वर्ग, से, बजकर): use its plain loanword
                # form if it has one, otherwise the concept is missing
                loan = other.lex.get(f"loan_{key}")
                if loan is not None:
                    FALLBACK_HITS[(self.name, f"loan_{key}", fb)] += 1
                    return loan
                continue
            if key in other.lex:
                FALLBACK_HITS[(self.name, key, fb)] += 1
                return other.lex[key]
        if default is not None:
            return default
        FALLBACK_HITS[(self.name, key, "MISSING")] += 1
        raise MissingWord(f"{self.name}: {key}")

    def has(self, key: str) -> bool:
        return self.w(key, default="\0") != "\0"

    # ------------------------------------------------------------------ numbers
    def cardinal(self, n: int) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def digit(self, d: int) -> str:
        return self.cardinal(d)

    def say_digits(self, s: str) -> str:
        return " ".join(self.digit(int(c)) for c in s if c.isdecimal())

    def say_int(self, n: int) -> str:
        if n >= MAX_CARDINAL:
            return self.say_digits(str(n))
        return self.cardinal(n)

    def say_decimal(self, int_part: str, frac: str) -> str:
        whole = self.say_int(int(int_part)) if int_part else self.digit(0)
        return f"{whole} {self.w('point')} {self.say_digits(frac)}"

    def ordinal(self, n: int) -> str:
        tpl = self.w("ordinal", "{x}")
        return self.fill(tpl, x=self.say_int(n))

    def year(self, n: int) -> str:
        return self.say_int(n)

    def attach(self, words: str, suffix: str, n: int | None = None) -> str:
        """Join a native suffix to the last word of `words` (sandhi hook)."""
        if self.glue_unknown_suffix:
            return words + suffix
        return f"{words} {suffix}"

    def ordinal_from_suffix(self, n: int, suffix: str) -> str | None:
        """Return a full ordinal when `suffix` is an ordinal marker for this language."""
        return None

    # ------------------------------------------------------------------ composite readings
    year_style = False  # True: 4-digit years get a special reading (English pairs)

    def date_day(self, d: int) -> str:
        return self.say_int(d)

    def daypart(self, h: int, ap: str) -> str:
        """h is 1..12 with am/pm."""
        if ap == "am":
            key = "dp_night" if h == 12 or h < 4 else "dp_morning"
        else:
            # evening runs 4 PM up to dp_evening_until (exclusive). 7 PM is evening in most training text
            # (शाम सात, ಸಂಜೆ ಏಳು, সন্ধ্যা সাতটা, संध्याकाळी सात, સાંજે સાત) but night in Tamil/Telugu/Malayalam
            # (இரவு ஏழு, రాత్రి ఏడు, രാത്രി ഏഴ്), which set it to 7. A language may name dusk separately
            # (Assamese আবেলি 4-5 PM, সন্ধিয়া 6-7 PM).
            key = "dp_noon" if h == 12 or h < 4 else ("dp_evening" if h < self.w("dp_evening_until", 8) else "dp_night")
            if key == "dp_evening" and h >= self.w("dp_dusk_from", 99):
                key = "dp_dusk"
        return self.w(key)

    def say_time(self, h: int, m: int, s: int | None, ap: str | None) -> str:
        hw, mw = (self.w("time_hour_forms", {}) or {}).get(h) or self.say_int(h), self.say_int(m)
        if s is not None:
            t = self.fill(self.w("time_hms"), h=hw, m=mw, s=self.say_int(s))
        elif m == 0:
            one = h in (1, 13) and self.w("time_h_1", "")  # Odia ଗୋଟାଏ: one o'clock
            t = one or self.fill(self.w("time_h"), h=hw)
        else:
            t = self.fill((m == 1 and self.w("time_hm_1", "")) or self.w("time_hm"), h=hw, m=mw)
        if ap:
            t = self.fill(self.w("time_ap"), t=t, dp=self.daypart(h, ap))
        return t

    def say_money(self, cur: str, amount_words: str | None = None, one: bool = False, main: int | None = None,
                  sub: int | None = None, neg: bool = False, main_words: str | None = None, noadj: bool = False) -> str:
        if amount_words is not None:  # noadj: a decimal amount's last digit keeps its digit name (₹2.111)
            return self.fill(self.w("money"), _noadj=noadj, x=amount_words, cur=self.plural(f"cur_{cur}", one))
        parts = []
        if main:
            parts.append(self.fill(self.w("money"), x=main_words or self.say_int(main),
                                   cur=self.plural(f"cur_{cur}", main == 1)))
        if sub:
            parts.append(self.fill(self.w("money"), x=self.say_int(sub), cur=self.plural(f"sub_{cur}", sub == 1)))
        if not parts:
            parts.append(self.fill(self.w("money"), x=self.digit(0), cur=self.plural(f"cur_{cur}", False)))
        out = self.w("money_join", " ").join(parts)
        return f"{self.w('minus')} {out}" if neg else out

    def say_fraction(self, a: int, b: int, a_words: str | None = None, b_words: str | None = None) -> str:
        special = (self.w("fractions_special", {}) or {}).get((a, b))
        if special:
            return special
        return self.fill(self.w("fraction"), a=a_words or self.say_int(a), b=b_words or self.say_int(b))

    def oblique(self, word: str) -> str:
        """direct singular -> oblique singular for nouns whose oblique equals the direct plural
        (Hindi रुपया -> रुपये, Urdu گھنٹہ -> گھنٹے, Gujarati રૂપિયો -> રૂપિયા); other words unchanged"""
        for k, v in self.lex.items():
            if isinstance(v, tuple) and len(v) == 2 and v[0] == word and k.startswith(("cur_", "sub_", "u_")):
                return v[1]
        return word

    def unit_word(self, key: str, one: bool = False):
        v = self.w(f"u_{key}", default="")
        if not v:
            return None
        if isinstance(v, tuple):
            return v[0] if one else v[1]
        return v

    # ------------------------------------------------------------------ templates
    def adj(self, words: str) -> str:
        """Form of a number used in front of a noun (Telugu లక్షలు -> లక్షల, Tamil ஒன்று -> ஒரு)."""
        return words

    def fill(self, tpl: str, _noadj: bool = False, **kw) -> str:
        def rep(m):
            v = kw[m.group(1)]
            suf = m.group(2)
            if suf:
                return self.attach(v, suf)
            if not _noadj and m.group(1) in ("x", "a", "h", "m", "s", "d") and tpl[m.end():m.end() + 2].strip():
                v = self.adj(v)  # something (a unit, currency, ...) follows the number
            return v

        return re.sub(r" {2,}", " ", _TPL.sub(rep, tpl)).strip()

    def plural(self, key: str, n_one: bool) -> str:
        v = self.w(key)
        if isinstance(v, tuple):
            return v[0] if n_one else v[1]
        return v


def table_cardinal(lang: Lang, n: int, below100: list[str], hundred, thousand: str, lakh: str,
                   crore: str, join=" ") -> str:
    """Indian-system composition for languages with a full 0-99 table.

    `hundred` is either a word (`"सौ"`) or a callable h -> words for h*100.
    """
    if n < 100:
        return below100[n]
    parts = []
    cr, rest = divmod(n, 10**7)
    if cr:
        parts.append(f"{table_cardinal(lang, cr, below100, hundred, thousand, lakh, crore, join)} {crore}")
    lk, rest = divmod(rest, 10**5)
    if lk:
        parts.append(f"{below100[lk]} {lakh}")
    th, rest = divmod(rest, 1000)
    if th:
        parts.append(f"{below100[th]} {thousand}")
    h, rest = divmod(rest, 100)
    if h:
        parts.append(hundred(h) if callable(hundred) else f"{below100[h]} {hundred}")
    if rest:
        parts.append(below100[rest])
    return join.join(parts)
