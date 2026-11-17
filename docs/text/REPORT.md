# openarcane.text — report

A clean-room, deterministic text normaliser for the Volt-TTS model (`openarcane/Volt-TTS`).
It turns written text into speakable text.
The design is in [DESIGN.md](DESIGN.md).

```python
from openarcane import normalize
normalize("ಬಿಲ್ ₹1,250.50", "kannada")  # "ಬಿಲ್ ಸಾವಿರದ ಇನ್ನೂರ ಐವತ್ತು ರೂಪಾಯಿ ಐವತ್ತು ಪೈಸೆ"
```

The CLI reads one line in and writes one line out:
`python -m openarcane.text -l kannada "text"`.
It uses only the Python standard library, makes no network calls and keeps no state between calls.

## 1. Status (measured)

| check | result |
|---|---|
| tests | `uv run --no-project --with pytest pytest -q tests` (from the repository root): **2411 passed** in about 1 s |
| corpus audit | all 26,860 training-text rows (26 languages; up to 1,500 rows with digits and 500 without per language) ran in 10.1 s with 0 errors. No ASCII or native digits are left, and every output is idempotent. 14 of the 13,000 digit-free rows change, all deliberately: abbreviation expansions such as `Mr.` → `Mister`, `डॉ.` → `डॉक्टर`, `&` → the language's "and", `கி.மீ.` → `கிலோமீட்டர்` |
| passthrough | text without numbers or symbols comes out byte-identical, including text that is not in Unicode NFC: matching runs on NFC (taken piece by piece between whitespace, where NFC never joins), and the engine copies every untouched whitespace-separated piece from the original by position, so `Cafe\u0301 … Café` keeps both spellings and a generated word never takes an untouched token's spelling. Only a piece the engine rewrites or cuts into may come out in NFC. Markdown, `###`, `**`, bullets, repeated spaces, tabs and line breaks are kept (`tests/text/test_sweep.py`, all 26 languages) |
| safety net | `normalize()` returns the input unchanged and logs the error if the engine fails on some input (an unknown language or a non-string argument still raises). Tests run with `OPENARCANE_TEXT_STRICT=1` so errors still fail them (`tests/text/test_safety_net.py`) |
| speed | 2,952 comparison rows in 0.37–0.43 s across runs (about 7,000 rows/s on one core) |

## 2. Per-language coverage

Each capability below was probed with fixed inputs:

| capability | probe inputs |
|---|---|
| cardinal | `45`, `999`, `12345`, `1,00,000`, `12,34,567` |
| ordinal | `1st`, `5th`, `21st` |
| decimal | `3.14` |
| fraction | `1/2`, `3/4`, `2½` |
| negative | `-5` |
| range | `5-7` |
| percent | `25%` |
| money | `₹1,250.50`, `$5` |
| date | `15/08/2025` |
| time | `10:30`, `7 PM` |
| codes | `OTP: 123456`, `+91 98450 12345` |
| units | `5 km`, `28°C`, `5 kg` |
| maths | `2 + 3 = 5`, `3²` |
| url/email | `www.gov.in`, `a@b.in` |

Every word in the output was then looked up in that language's own Volt-TTS training text.

Legend:

- **A, attested.** Every word occurs in the language's own training text. The grammar has not been
  checked by a native speaker.
- **B, borrowed.** At least one word comes from the language's fallback relative (see §2.2). The
  word is attested for the relative but **unverified** for this language.
- **U, unverified.** At least one output word never occurs in the language's text, for example
  `इक्कीसवाँ` (21st) or a loanword such as `माइनस`.
- **D, digit fallback.** Some probe numbers are read digit by digit because the language's number
  words are not known for them.
- **L / l, left as written.** All (L) or some (l) of the probes keep a symbol or Latin
  abbreviation, because the concept has no word in the language or its relatives.

| lang | card | ord | dec | frac | neg | range | pct | money | date | time | codes | units | maths | url |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| assamese | A | U | A | A | A | U | A | A | A | A | A | A | A | A |
| bengali | A | A | A | A | A | A | A | A | A | A | A | A | A | A |
| bhojpuri | A | U | B | B | B | B | B | B | B | B | B | B | B | B |
| bodo | D | A | B | B | B | A | A | B | B | l | B | B | B | B |
| chhattisgarhi | A | A | B | B | B | A | B | B | B | B | B | B | B | B |
| dogri | D | U | B | B | B | A | A | B | A | A | B | B | B | B |
| english | U | A | A | A | A | A | A | U | A | A | A | U | U | A |
| gujarati | A | U | A | U | U | A | A | A | A | A | A | A | A | A |
| hindi | A | U | A | A | A | A | A | A | A | A | A | A | A | A |
| kannada | A | A | A | A | A | A | A | A | A | A | A | A | A | A |
| kashmiri | A | A | B | B | B | A | A | B | A | A | B | B | B | B |
| konkani | A | U | A | B | B | A | A | B | A | A | B | B | B | B |
| magahi | A | A | B | B | B | B | B | B | B | B | B | B | B | B |
| maithili | A | A | B | B | B | A | B | B | B | B | B | B | B | B |
| malayalam | A | A | A | A | A | A | A | A | A | A | A | A | A | A |
| manipuri | D | U | A | l | L | A | A | A | A | l | A | l | L | l |
| marathi | A | U | A | A | A | A | A | A | A | A | A | A | A | A |
| nepali | A | A | A | A | U | A | A | A | A | A | A | U | A | A |
| odia | A | U | A | A | U | A | A | A | A | A | U | U | A | U |
| punjabi | A | U | A | U | U | A | A | A | A | A | A | A | A | A |
| sanskrit | D | U | A | B | A | A | A | B | U | A | B | B | B | B |
| santali | A | A | A | l | L | A | A | A | A | l | A | l | L | l |
| sindhi | A | U | B | B | B | A | A | B | A | A | B | B | B | B |
| tamil | U | A | A | A | U | A | A | A | A | A | A | A | U | A |
| telugu | A | A | A | U | A | A | A | A | A | A | A | A | A | A |
| urdu | A | U | A | A | A | A | A | A | A | A | A | A | A | A |

The words behind the less common cells:

| cell | cause |
|---|---|
| U ordinal (as, bho, doi, gu, hi, kok, mr, or, pa, sa, sd, ur, mni) | only `21st` fails; the regular `21` ordinal (`इक्कीसवाँ`, `एकवीसवा`, `ଏକୋଇଶତମ`, `اکیسواں` …) never occurs in the text |
| U negative / maths / codes / url | the loanwords `माइनस`, `மைனஸ்`, `ਮਾਈਨਸ`, `ସେଲସିୟସ୍`, `ପ୍ଲସ`, `ଆଟ`/`ଡଟ`, `ஸ்கொயர்` are not in the text |
| U english cardinal, money, units, maths | `lakh`, `rupees`, `paise`, `kilometres`, `Celsius`, `squared` never occur in the English training text (case-insensitive; words copied from the input are not counted) |
| U tamil cardinal | `பன்னிரண்டாயிரத்து` (12,000 joining form) is not in the text; each part is |
| U telugu fraction | `ముప్పావు` (three quarters) is not in the text |
| U gujarati / punjabi fraction | the division words `ભાગ્યા`, `ਬਟਾ` |
| U assamese range | `সাতলৈ` |
| D bodo cardinal | `999`, `12345`, `1,00,000`, `12,34,567` are read digit by digit; only attested Bodo compounds are used (sixties, exact hundreds and thousands) |
| D dogri cardinal | `999` only: Dogri has no attested word for 99, so `999` is read digit by digit (`900` → `नौ सौ` works) |
| D manipuri cardinal | `999`, `12345`, `12,34,567`. Words exist only for the exact hundreds 100, 400, 500, 600, 800 and 900 (200, 300 and 700 stay digit by digit) and for `1,00,000` |
| D sanskrit cardinal | `12,34,567`; up to `12345` the additive compounds are built (`पञ्चचत्वारिंशदधिकत्रिशतोत्तरद्वादशसहस्रं`, unattested as a whole) |
| l / L manipuri, santali | `-5` keeps its sign (no attested minus word), `3/4`, `7 PM`, `28°C`, `5 kg` (Santali), `2 + 3 = 5`, `3²` and `a@b.in` keep their symbols or Latin, because there is no attested word for that fraction, PM, Celsius, plus/equals/squared or "at" |
| l bodo time | `7 PM` keeps `PM` (no Bodo daypart word) |

Summary by language:

- **All 14 attested:** bengali, kannada, malayalam. English is attested except for the Indian-English and unit words (`lakh`, `rupees`, `kilometres`, `squared`), which its training text lacks.
- **One to three U, no borrowing:** assamese, gujarati, hindi, marathi, nepali, punjabi, tamil, telugu,
  urdu, odia (five U).
- **Mostly borrowed from Hindi or Urdu:** bhojpuri, magahi, maithili, chhattisgarhi, dogri, sindhi,
  konkani, kashmiri, bodo, sanskrit.
- **Partly left as written:** manipuri and santali.

### 2.1 Verified items (cited source or independent table)

**CLDR cardinal check.** CLDR RBNF `%spellout-cardinal` (Unicode License V3), run through PyICU (`tools/text/cldr_check.py`). Assamese is not checked, because CLDR has no
`as` rule set.

| language | 0–99 match | exact hundreds match | all checked numbers (1,371) | why the rest differ |
|---|---|---|---|---|
| english | 100/100 | 9/9 | 1371 | — |
| telugu | 100/100 | 9/9 | 1335 | `వేలు`/`ఒక్క` in compounds, chosen from the corpus |
| bengali | 100/100 | 6/9 | 957 | `দুশো` (180 in text) vs CLDR `দুইশো` (0); `নশো` 95 vs 5 |
| urdu | 99/100 | 9/9 | 1352 | `اناسی` vs `انیاسی` |
| marathi | 97/100 | 9/9 | 1322 | `उन्चालिस`-type corpus spellings |
| nepali | 94/100 | 9/9 | 1256 | corpus spellings |
| tamil | 90/100 | 8/9 | 1104 | `நாற்பத்து` (73 vs 3), `பூஜ்யம்` (151 vs 4) |
| malayalam | 89/100 | 8/9 | 102 | `അമ്പത്` vs CLDR `അൻപത്` (all fifties), `നൂറ്റി രണ്ട്` spaced where CLDR writes `നൂറ്റിരണ്ട്`, and `ഒന്ന്` for 1 where CLDR has `ഒരു` |
| hindi | 88/100 | 9/9 | 885 | `पंद्रह` vs `पन्द्रह`, `-नवे` vs `-नबे`, `तिरपन` |
| gujarati | 88/100 | 0/9 | 123 | hundreds as one word `એકસો` (CLDR `એક સો`), `છવ્વીસ`, `બોત્તેર`, `ત્રેતાલીસ` (omniglot) |
| kannada | 84/100 | 9/9 | 1076 | `ಇಪ್ಪತ್ನಾಲ್ಕು`-type contracted forms, which the text prefers |
| punjabi | 86/100 | 9/9 | 1116 | corpus spellings |
| odia | 67/100 | 9/9 | 815 | `ତିରିଶ` (71 vs 10) and similar corpus spellings |

Every mismatch that was inspected is a spelling choice taken from the training text's own counts, not
a wrong number.

**Items settled by a cited source:**

| language | items | source |
|---|---|---|
| Marathi | `विसावा`, `मिनिट` | Wiktionary |
| Gujarati | `ત્રેતાલીસ`, `ઇઠ્યોતેર`, `છઠ્ઠો` | omniglot number table |
| Punjabi | `ਘੰਟੇ` | Wiktionary |
| Urdu | `دوسرے`, `روپے` | Wiktionary |
| Nepali | `दोस्री` | Nepali tagset |
| Sanskrit | `त्रयस्त्रिंशत्`, `त्र्यशीतिः` | Whitney §476 |
| Sanskrit | `लक्षं` | source not recorded |
| Kashmiri | `پٕنٛژٕہ`, `اوٚڑ`, `ڈاے`/`ڈۄڈ`, `شیٚیِم`, `ژورِ بجہِ` | Koul |
| Maithili | `रुपैया` | Grierson |
| Bhojpuri | `छठवाँ` | Census Bhojpuri |
| Bodo | `जौखोन्दो` | government Bodo text |
| Manipuri | `ꯑꯍꯥꯟꯕ`/`ꯁꯨꯕ` ordinals, `ꯆꯥꯃ` hundreds, `ꯃꯔꯤꯐꯨꯇꯔꯥ`, `ꯒ ꯃꯈꯥꯏ`, `ꯄꯩꯁꯥ` | Pettigrew |
| Santali | `ᱫᱚᱥᱟᱨ`, `ᱛᱮᱥᱟᱨ` | Hansdah and Murmu |
| Malayalam | `രണ്ടേകാൽ` | Malayalam: A University Course, lesson 17 |
| English | `Miz` | Cambridge |

None of these sourced items was checked by a native speaker. The Kannada and Hindi REVIEW_NEEDED items were
approved by a native speaker on 2026-11-15 (§3); the Telugu, Malayalam and Tamil items are still on the list.

### 2.2 Fallback chains and borrowed concepts

These were measured by running all 35 golden inputs through each language and recording every lexicon
lookup answered by a relative. Number words are never borrowed. Grammar templates (`का वर्ग`, `से`,
`बजकर` …) are borrowed only where `borrow_grammar` allows it.

| language | chain | borrowed concepts | missing (rule dropped, plainer reading) |
|---|---|---|---|
| assamese | bengali | abbr_native, code_connectors | — |
| marathi | hindi | month_aliases, unit_abbr (matching only) | — |
| nepali | hindi | abbr_native, month_aliases, unit_abbr (matching only) | — |
| bhojpuri, magahi | hindi | most non-number words: operator, punctuation and unit words; money, date, clock (`बजकर`) and range templates; `fractions_special` | — |
| maithili, chhattisgarhi | hindi | as above, but with their own range word (`सँ`, `ले`) and `रुपैया` (Maithili) | — |
| dogri, sindhi, konkani | hindi | operator, punctuation and unit words, the `बटा` division word, `$` (dollar), keyword lists | — |
| sanskrit | hindi | as dogri, plus `money_join` and `sub_INR` | — |
| kashmiri | urdu | operator, punctuation and unit words, `بٹا`, `$`, keyword lists | — |
| bodo | hindi | operator, punctuation and unit words, `बटा`, `$`, keyword lists, date template | time_h, time_hm (clock read as plain numbers) |
| manipuri | — | — | dot, equals, fraction, minus, time_ap |
| santali | — | — | dot, equals, fraction, minus, time_ap (a mixed number without a template is read as a decimal) |
| all others | — | — | — |

"Matching only" means the keys hold input patterns (month spellings, unit abbreviations) used to
recognise text. They never become output words.

## 3. REVIEW_NEEDED (kn / te / ml / hi / ta, for a native checker)

**Native check, 2026-11-15:** a native Kannada and Hindi speaker approved every row of
[`NATIVE_REVIEW_kn_hi.md`](NATIVE_REVIEW_kn_hi.md) as written (18 Kannada, 18 Hindi). The sheet holds the Kannada
and Hindi items below, plus spot checks of OTP, phone, PIN, money, percent, time, ordinal, range, year, lakh
grouping, native digits and fractions. All 36 rows still match the current output. **Telugu, Tamil and Malayalam
are still open.**

Changes made for the open languages are **still flagged**. Each change has a
test in `tests/text/`; the items left unchanged have their current output pinned in
`tests/text/test_edge_cases.py` (`PINNED`), so any change to them is deliberate.

**Kannada: native-approved 2026-11-15 ([sheet](NATIVE_REVIEW_kn_hi.md) rows kn 1–6)**

- `=` reads `ಈಕ್ವಲ್ ಟು`. Approved.
- Date suffix order: `15/08/2025ರಂದು` → `ಹದಿನೈದು ಆಗಸ್ಟ್ ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತೈದರಂದು`. Approved as written.
- `2²` → `ಎರಡು ವರ್ಗ`. Approved as written.
- `ಕೋಟಿಯ` inside numeric cardinals: `₹15000000` → `ಒಂದು ಕೋಟಿಯ ಐವತ್ತು ಲಕ್ಷ ರೂಪಾಯಿ`. Approved.
- Unit stems with attached case endings: `5kgಗೆ` → `ಐದು ಕಿಲೋಗ್ರಾಂಗೆ`. Approved.
- Degree words `ಡಿಗ್ರಿ` / `ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್`. Approved.
- Not on the sheet, so still unchecked: the Kannada `km/h` rate reading and the structured-unit case
  ending `1½kgಗೆ`.

**Telugu**

- Date suffix order.
- Hour words: `గంటలకు` as the case ending of a written hour word.
- `మొదటి` for 1st.
- Fraction parts form: `1/20` → `ఇరవై భాగాల్లో ఒక భాగం`.
- `ఒక్క` vs `ఒకటి` in compounds before a noun.
- Rate template: `గంటకు {x} కిలోమీటర్లు`.
- Decimal digit names.
- `5kgకి`.
- Singular rate `1 km/h` → `గంటకు ఒక కిలోమీటరు`; rates after fractions (`2½ km/h`).
- Postpositions after a space (`వరకు`, `నుంచి`) are no longer glued.

**Tamil**

- `-5` → `மைனஸ் ஐந்து`.
- Dates: ours has no `தேதி` form; `பதினைந்தாம் தேதி` may be more natural.
- Rate template `மணிக்கு`.
- Decimal `ஒன்று`.
- `5kgக்கு`.

**Malayalam**

- The forties' spelling.
- Date suffix order.
- Rate template `മണിക്കൂറിൽ`.
- `ശതമാനത്തിന്` join.
- `രണ്ടേകാൽ` (sourced).
- `5kgക്ക്` and `2¼kgക്ക്`.
- `-i` nouns keep the written `ക്ക്` (`7 PMക്ക്` → `രാത്രി ഏഴ് മണിക്ക്`, `മണിക്ക്` 41 in the text).
- `10:30ക്ക്` → `പത്ത് മണി മുപ്പത് മിനിറ്റിന്`; a speaker may prefer `പത്തരയ്ക്ക്`.

**Hindi: native-approved 2026-11-15 ([sheet](NATIVE_REVIEW_kn_hi.md) rows hi 1–2)**

- Oblique forms before postpositions: `₹1 में` → `एक रुपये में`, `1 hr में` → `एक घंटे में`. Approved.
- Not on the sheet, so still unchecked: the native-quantity minus (`5 किलो-3 किलो=2 किलो`), and the
  fraction oblique with `आधा` agreeing (`½ hr में` → `आधे घंटे में`; `½-¾ कप` → `आधे से …`;
  Urdu `آدھے گھنٹے میں` likewise).

**All Dravidian**

- `km/h` rate readings (Telugu, Tamil, Malayalam open; Kannada not on the native sheet).

## 4. Unverified items and known limitations

**Unverified.** For languages outside the five above, these items have no citation and rest on
attestation or a reasoned guess. Where no word could be attested at all, the number is read digit by
digit or the symbol is kept.

- **Nepali:** `को` forms in maths (`दुईको घन`).
- **Maithili `सँ`, Chhattisgarhi `ले`, Bodo `निफ्राय … सिम`:** range templates.
- **Urdu:** `ویں` on irregular stems takes the masculine oblique, or the feminine before 17 listed common
  feminine nouns (`صدی`, `جنگ`, `بار`, `تاریخ` …), also when punctuation follows the noun (`:`, `؟`, `۔`, `،`, curly quotes, `…`). Other feminine nouns still get the masculine.
- **Sanskrit:**
  - `ऋण` (minus) and `सार्ध` mixed halves.
  - Additive compounds above 100, which are unattested as whole words.
- **Bodo:**
  - `थि` ordinals.
  - The half words `खावसे` and `आरो`.
  - The `बटा` division word.
- **Manipuri:** `ꯄ꯭ꯂꯁ` (plus) and `ꯇꯪꯈꯥꯏ`.
- **Santali:** the loanwords.
- **Half words:**
  - Konkani `अडीच` and its `{x} आनी {f}` template.
  - Dogri `डेढ़`/`ढाई` and `{x} ते {f}`.
  - Sindhi `ॾेढ`/`अढाई`/`साढे` and `{x} ऐं {f}`.
- **Odia:** `ଗୋଟାଏ` for one o'clock, and `ଗୋଟାଏରେ`, `ମିନିଟରେ`, `ସେକେଣ୍ଡରେ` with a written `ଟାରେ`.
- **Assamese:** `range_qty` (`পাঁচৰ পৰা দহ কিলোগ্ৰাম`) and the 21st ordinal.
- **Kashmiri:**
  - The fraction division form (`بٹا`) and the `تہٕ` mixed template.
  - The `شیٚیِم` spelling, which has 0 hits in the text.
  - Clock forms for hours other than 4.
- **Dogri `{x}मां` and Sindhi `{x}ों`:** regular ordinals.
- **Marathi:** `नववा` and `एक टक्का`, attested only.
- **Gujarati:** the oblique `રૂપિયામાં` and the spaced forms `રૂપિયા માં`, `રૂપિયા માંથી` and the other listed postpositions. A spaced `ના` is not in the list, since it is also the negator (`₹1 ના આપો` → `એક રૂપિયો ના આપો`); a spaced genitive `ના` therefore keeps the direct form.
- **Bengali:** `মিনিটে`, `সেকেন্ডে` for a written `টাতে` after minutes or seconds.
- **Bodo:** the attested sixties and exact hundreds and thousands, `आरो` mixed numbers, `पैसा`.
- **Manipuri:** `ꯀꯤꯂꯣꯒ꯭ꯔꯥꯝ`.
- **Manipuri and Santali:** mixed numbers without a template are read as decimals (`41½` → `… ꯄꯣꯏꯟꯠ ꯃꯉꯥ`).
- **Hindi-belt four (Bhojpuri, Magahi, Maithili, Chhattisgarhi):** 1–10 words chosen by local
  frequency, and their own ordinals (`पहिल दोसर तेसर चारिम`).
- **All B cells in §2:** a borrowed word is attested for the relative only.

**Known limitations**

- **Punjabi years.** Year reading is not consistent within a sentence: `1497` after `ਸੰਨ` is read as a year, while a later
  `1612` in the same sentence is read in thousands style.
- **Dayparts.** Tamil, Telugu and Malayalam switch from evening to night at 7 PM; the other languages with
  daypart words switch at 8 PM (`7 PM` → Hindi `शाम सात बजे`, Kannada `ಸಂಜೆ ಏಳು ಗಂಟೆ`). English says `p m`.
  Bodo, Manipuri and Santali read the clock and keep `PM` as written. Some speakers would say evening for
  7 PM in Tamil, Telugu and Malayalam.
- **Latin text** (`www`, acronyms, vehicle-registration letters) is kept in Latin, not spelled
  natively.
- **Odia hyphens.** Hyphen-joined words are left glued, as written.
- **Large numbers.** Above 10^15 they are read digit by digit. Non-round runs of 10 or more digits
  before a word are treated as IDs and read digit by digit.
- **Ambiguity.** Ambiguous spans follow the fixed policy in DESIGN.md §6. Examples: a weak year cue
  keeps the year reading (`in 1998 instalments`), and `a-b` is read as a range unless the clause has
  an operator. Two typed endpoints (`$5-$3`, `5%-10%`, `½ kg-1 kg`, `10:30-11:30`) are a subtraction only
  when the sum is local. Either right after the chain (closing brackets allowed) comes `=`, or an operator
  and operand with an `=` later in the same clause (`$10-$4+$2=$8`, `(($10-$4))=$6`, `$10-$4 - x = $3`); or
  just before it comes an operator, or `=` after a one-letter variable, a number or a bracketed sum, and no
  word follows the chain (`x = $5-$3`). Clock times need the `=`. So `$5-$10 per day + meals`, `Delivery
  costs $5-$10 + $2 handling`, `Daily budget (USD) = $5-$10`, `Interest rate (2026) = 5%-10%` and `Opening
  hours: 10:30-11:30 + 14:30-15:30` stay ranges. A range inside one money, percent or unit span
  (`₹500-1000`, `5-10%`) uses the same test. A hyphen right after a native word is minus only when a digit
  and a known quantity word (unit, currency, `qty_words`) come just before it and the sum is local in the
  same way, across a chain (`x = 5 किलो-3 किलो-1 किलो`, `5 लीटर-500 ml=4.5 लीटर`); `वजन = 5 किलो- 10 किलो
  प्रति दिन` and `5 किलो- 10 किलो प्रति दिन; 2+3=5` keep the hyphen, and a name hyphen (`कोविड-19`) is kept.
  A bracket before `=` counts only when it holds arithmetic (`(2+3)`, not `(Mon-Fri)`), script full stops
  (`۔ ।`) end the clause and the maths line, and vulgar fractions are operands (`½+¼=¾`). This is a heuristic. A markdown italic or bold star (`2 *cups*`, `**Total**`) is never multiplication, and
  two bare fraction glyphs joined by a dash are a range (`½-¾ cup`).

## 5. Clean-room and scope

- Written from scratch. No other normaliser's code or word tables were used.
- Word data comes from three places: hand-written tables, Unicode CLDR (cited), and attestation in the
  Volt-TTS training text.

## 6. Summary

`openarcane.text` provides `normalize(text, language)`, a CLI and 2,411 passing tests, and covers all 26
languages.

- **Fully attested:** Bengali, Kannada and Malayalam have attested words for all 14 capabilities. English
  lacks only Indian-English and unit words in its training text.
- **Nearly attested:** the other major languages have one to five unverified cells each.
- **Borrowed:** the smaller Devanagari and Perso-Arabic languages borrow non-number words from Hindi
  or Urdu, and say so.
- **Left as written:** Manipuri and Santali keep symbols where no word is attested.
- **Native checks:** Kannada and Hindi passed on 2026-11-15. A native speaker approved all 36 rows of
  [`NATIVE_REVIEW_kn_hi.md`](NATIVE_REVIEW_kn_hi.md) as written.
- **Still open:** native checks for Telugu, Malayalam and Tamil (§3).
