# openarcane.text — design

Clean-room, deterministic text normaliser for the Volt-TTS model
(`openarcane/Volt-TTS`). It turns written text into speakable text:
numbers, money, dates, times, digit strings, units, maths and symbols become words in the
requested language. Everything else is copied through byte-for-byte.

## 1. API

```python
from openarcane import normalize, LANGUAGES
normalize("ಬಿಲ್ ₹1,250.50", "kannada")   # -> "ಬಿಲ್ ಸಾವಿರದ ಇನ್ನೂರ ಐವತ್ತು ರೂಪಾಯಿ ಐವತ್ತು ಪೈಸೆ"
```

- `normalize(text: str, language: str) -> str`. `language` is the TTS name (`kannada`, `hindi`, …,
  `english`); ISO 639 codes (`kn`, `hi`, `sat`, `mni`, …) are accepted as aliases.
- CLI: `python -m openarcane.text -l kannada "text"` or text on stdin, one line in,
  one line out (`--show` prints input and output side by side).
- Python standard library only, no network, no state. Patterns are compiled once per language.

## 2. Languages and output script

Output script = the script the TTS saw for that language. Measured on
the Volt-TTS training text (3,000 random rows per language, share of letters):

| language | id | script in training text | native digits seen |
|---|---|---|---|
| assamese | 2501 | Bengali (Assamese letters ৰ ৱ) | Bengali + ASCII |
| bengali | 2502 | Bengali | Bengali + ASCII |
| bhojpuri, chhattisgarhi, magahi, maithili, dogri, konkani, marathi, nepali, sanskrit, hindi, bodo | | Devanagari | Devanagari + ASCII |
| **sindhi** | 2521 | **Devanagari** (not Arabic) | ASCII |
| gujarati | 2507 | Gujarati | — |
| punjabi | 2518 | Gurmukhi | ASCII |
| odia | 2517 | Odia | Odia + ASCII |
| kannada / telugu / tamil / malayalam | | own scripts | Kannada + ASCII, ASCII |
| **manipuri** | 2514 | **Meetei Mayek** (not Bengali) | Meetei Mayek |
| **santali** | 2520 | **Ol Chiki** | Ol Chiki + ASCII |
| **kashmiri** | 2509 | Perso-Arabic | Extended Arabic-Indic |
| urdu | 2524 | Perso-Arabic | Extended Arabic-Indic + ASCII |
| english | 2050 | Latin | ASCII |

Input digits accepted from **every** decimal-digit block regardless of language (ASCII, Devanagari,
Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam, Ol Chiki, Meetei Mayek,
Arabic-Indic, Extended Arabic-Indic, Limbu, Tibetan, fullwidth). Arabic `٫` / `٬` are decimal and
group separators. Tamil also has non-decimal number signs (௰ ௱ ௲): left alone (rare, legacy).

## 3. Pipeline

1. **Digit folding (offset-preserving).** Every native digit is mapped 1:1 to ASCII in a working copy,
   so match offsets equal original offsets. No other character is changed (matching runs on NFC, but the engine
   copies every untouched whitespace-separated piece from the original by position). No whitespace
   collapse, no markdown stripping: the model was trained on noised text (`###`, `**`, extra spaces,
   tabs, line breaks, zero-width chars) and must keep seeing it.
2. **Scanner.** A trigger regex finds the next candidate position; the rules below are tried in
   priority order at that position. Each handler returns words or `None` (fall through to the next
   rule). Handlers see the surrounding text, so a rule can decline when the context says another
   reading is meant (an operator next to `10-3`, an `=` on the line of `3/04`, a noun after a count).
   A rejected date-shaped token is never split into smaller numbers: it is read literally (§6).
3. **Splice.** Unmatched text is copied unchanged. A replaced span gets a space inserted only when
   it would otherwise glue to a neighbouring letter or digit that is *not* a known suffix. Inside a
   span the writer's whitespace is kept (`2  +\n3 =\t5` → `two  plus\nthree equals\tfive`).
   Operator spans are local, so a typed atom next to an operator keeps its own reading
   (`₹5+₹2=₹7` → five rupees plus two rupees equals seven rupees).
4. **Suffix attachment.** Digits followed directly (or after `-` or one space for listed suffixes)
   by a native case/ordinal suffix are joined with language sandhi: `1998ರಲ್ಲಿ` → `…ಎಂಟರಲ್ಲಿ`,
   `5ನೇ` → `ಐದನೇ`, `1985లో`, `19వ` → `పందొమ్మిదవ`, `2023-ல்` → `…மூன்றில்`, `5-ാം` → `അഞ്ചാം`,
   `5वीं` → `पाँचवीं`, `2रा` → `दूसरा`, `৫ম` → `পঞ্চম`.

### Rule priority (highest first)

| # | kind | examples | reading |
|---|---|---|---|
| 1 | URL / email | `https://x.co/a`, `www.gov.in`, `a.b@x.com` | scheme `https://` dropped (not read aloud); letters kept; `. / @ - _ : ? = & # + % ~ ; , ! * $` → symbol words, any other symbol kept as written (never dropped); digit runs ≤ 4 as numbers, longer or 0-led digit by digit; letter+mark runs of any script kept whole (`https://उदाहरण.भारत` → `उदाहरण डॉट भारत`); trailing sentence punctuation excluded |
| 2 | phone | `+91 98450 12345`, `098450-12345`, `080-2345 6789`, `1800-123-4567`, bare 10-digit mobile `[6-9]\d{9}` | digit-by-digit, written groups kept as pauses (`,`); unseparated 10-digit mobile → 5+5. A phone cue (`Call`, `Dial`, `Helpline`, `Phone`, `Mob.`, native `फोन`/`ಫೋನ್`…) makes a 3–15 digit number at the end of a clause a dial number (`Call 112` → one one two; `Call 100 people` stays a count). Unseparated digits ending in five zeros are a quantity, not a phone (`7000000000 records`). A currency, unit or scale word right after the number, with any spacing, makes it an amount (`9876543210 INR`, `6000000001  kg`), unless a phone cue comes before it. Per-language cues after the number also mark a dial number (Hindi `112 पर फोन करें` → `एक एक दो पर फोन करें`; Marathi `वर फोन करा`, Urdu `پر فون کریں`, Gujarati, Nepali) |
| 3 | keyword code | OTP/PIN/PIN code/code/A/C/account/acct/ID/Aadhaar/PNR/ref/txn/order … + native spellings, then label syntax only (`:`, `#`, `=`, `-`, `is`, or up to four filler words such as `OTP for login is`; never other words, so `Account balance: 1250` is an amount; native connectors per language: Hindi `है`/`नंबर`, Marathi `आहे`, Bengali `হল`, Gujarati `છે`, Punjabi `ਹੈ`, Nepali `हो`, Urdu `ہے`, Tamil `எண்`, Kannada `ಸಂಖ್ಯೆ`, Telugu `నంబర్`/`సంఖ్య`, Malayalam `നമ്പർ`), then digit groups; a group that starts another token (`10:30`, `15/08/2025`, `2025-08-15`) is not taken | digit-by-digit; written groups kept (`12 34 56` → three pauses); one unbroken run is grouped ≤5 one group, 6→3+3, 7→3+4, 10→5+5, else 4s |
| 4 | date | `15/08/2025`, `15-08-2025`, `15.08.2025`, `2025-08-15`, `15 Aug 2025`, `Aug 15, 2025`, `15th August` | calendar-validated (leap years); day cardinal (English: ordinal), month name in language, year (English: year style). `mm/dd/yyyy` only when the first part cannot be a month, and only for day-first shapes: a year-first date is never repaired by swapping (`2025-15-08` is read literally). Invalid (`29/02/2025`, `29 February 2025`) → parts read literally (separator word for numeric dates). Native month names (CLDR spelling plus listed variants such as `सितम्बर`) are date cues like English ones (`1 अगस्त 1998`, `अगस्त 1998`); a date label (`Date:`, `DOB`, `दिनांक`, `ದಿನಾಂಕ`) makes `15/8` a day–month and lets a dotted two-digit-year date through (`DOB: 15.08.25`). A numeric date never starts right after a Latin letter (`v1.2.2025` is a version). Spaced slashes are a date only with a four-digit year and no maths in the clause (`15 / 08 / 2025` is a date; `6 / 3 / 2 = 1` is division) |
| 5 | time | `10:30`, `10:30:15`, `10.30 am`, `7 PM`, `22:05 hrs` | per-language clock template (Hindi `{h} बजकर {m} मिनट`, Kannada `{h} ಗಂಟೆ {m} ನಿಮಿಷ`, Tamil `{h} மணி`, with the before-noun form `ஒரு மணி`); zero minutes → hour only; AM/PM → daypart by value (12 AM → night, 12 PM → noon, 1–3 PM noon, 4–6 PM evening, 7–11 PM night, 4–11 AM morning) placed before the time in Indic, `a m`/`p m` in English. A following hour word (`बजे`, `ಗಂಟೆ`, `மணி`, `മണി`) is absorbed; a case suffix moves to the end (`10:30ಕ್ಕೆ` → `…ನಿಮಿಷಕ್ಕೆ`), and so does the case ending of a written inflected hour word (Telugu `10:30 గంటలకు` → `పది గంటల ముప్పై నిమిషాలకు`, REVIEW_NEEDED). Singular nouns for one (Telugu `ఒంటి గంట ఒక నిమిషం`). A ratio cue before `a:b` (`Ratio 12:30`, `अनुपात`) makes it a ratio. A time zone after the time is kept: expanded where the language has a word (`10:30 IST` → `ten thirty Indian Standard Time`), otherwise left as written (`दस बजकर तीस मिनट IST`). A language with no clock template reads the time as plain numbers and leaves AM/PM as written (Bodo `10:30 PM` → `जि थामजि PM`), never as a ratio |
| 6 | money | `₹1,250.50`, `Rs. 500/-`, `INR 2.5 crore`, `$5`, `€10.99`, `£3`, `USD 100`, `−₹5.50`, native `रु.`/`ರೂ.`/`రూ.`/`ரூ.`/`രൂ.` | amount + currency word with singular/plural where the language has it; 1–2 decimals → minor unit by string arithmetic (`₹1.5` → one rupee fifty paise, `₹1.05` → five paise); ≥3 decimals → decimal amount + plural currency, never rounded; the amount is always a quantity (`₹100000000` is a cardinal, never digit by digit); sign before or after the symbol → minus word; `/-` dropped; scale words honoured, also a strictly descending sequence of them (`₹1 crore 25 lakh` → one crore twenty-five lakh rupees); a scientific amount is one atom (`INR 1.2e6`); native abbreviations are accepted after the amount too (`5 रु.` → `पाँच रुपये`); a native suffix inflects the currency word (`₹5ಕ್ಕೆ` → `ಐದು ರೂಪಾಯಿಗೆ`); a language without a minor-unit word reads 1–2 decimals as a decimal amount with the main currency (Manipuri `₹1.50` → `ꯂꯨꯄꯥ ꯑꯃ ꯄꯣꯏꯟꯠ ꯃꯉꯥ ꯐꯨꯟ`) |
| 7 | percent, per mille | `12.5%`, `ಶೇ. 50`, `50 per cent`, `5‰` | number + percent word (Kannada: `ಶೇಕಡ` before the number); `‰` has its own per-mille template (`five per mille`, `पाँच प्रति हज़ार`) and is never read as percent; a language without a per-mille word keeps the symbol |
| 7b | mixed number, scientific, decade | `2 1/2 kg`, `1.2e-3`, `1990s`, `80s` (English) | `two and one half kilograms` (native ½/¼/¾ forms: `ढाई`, `ಎರಡೂವರೆ`, `இரண்டரை`, `രണ്ടര`); mantissa + times + ten + power word; decades pluralised. Both take an optional sign and a following unit, including a compound unit (`-2 1/2 किलो` → `माइनस ढाई किलो`, `-1.2e-3 kg`, `1e3 MB/s` → … megabytes per second); so do vulgar fractions (`-2½ kg` → minus two and one half kilograms). A scientific number takes `%` (`1e3%`). The writer's spacing before the unit is kept |
| 7c | scaled quantity | `5 lakh`, `2.5 crore`, `10 million`, `5k` | number + the language's scale word, outside money too (`5 lakh` in Hindi → `पाँच लाख`); takes a unit (`5 lakh kg`) and the before-noun form (Telugu `2 lakh రూపాయలు` → `రెండు లక్షల రూపాయలు`) |
| 8 | unit | `5 km`, `2.5kg`, `28°C`, `100 km/h`, `5 GB`, `5 MB/s`, `5 Mb/s`, `5 Mbps`, `3 sq ft`, `5 m²`, `ಕಿ.ಮೀ.`/`कि.मी.` | case-sensitive longest match (`Mb` = megabit, `MB` = megabyte); `unit/denominator` → `{unit} per {denominator}` with the per word of the language; number + CLDR long name: singular for one and plural otherwise where the language inflects the unit in this use (English, Telugu `ఒక గంట`/`రెండు గంటలు`, Hindi hours `एक घंटा`/`दो घंटे`), one invariant form where it does not (Kannada `ಕಿಲೋಮೀಟರ್`, Hindi `किलोमीटर`); the writer's spacing between number and unit is kept |
| 9 | math expression | `2 + 3 = 5`, `12 × 4 − 6 ÷ 2`, `x² + 2x + 1 = 0`, `√16`, `a^2`, `(a+b)²`, `x ≠ y`, `≤ ≥ < >` | operator words, with any run of spaces kept as written; superscripts → square/cube/power; variables (single Latin letters) kept; an operator may follow `%` (`5%+3%=8%`) or a native-script word or abbreviation (`5 किलो+3 किलो=8 किलो`); a spaced `/` in a maths clause is division; on a maths line `x-3` is minus and a spaced range inside a quantity is minus (`5 - 2 kg = 3 kg`) |
| 10 | fraction | `3/4`, `1/2`, `½`, `¾`, `24/7`, `1/2.5` | `a by b` template per language; operands are complete numbers, and a decimal operand makes it a plain division (`1/2.5` → one by two point five, never `one half.five`); a sign belongs to the whole fraction (`-3/4` → minus three quarters); ½ ¼ ¾ with native words; `24/7` / `24x7` → `twenty-four seven`, except on a maths line (`24×7=168`) |
| 11 | range | `5-7`, `5–7`, `2020-21`, `FY 2025-26` | `a from-to b` template. `YYYY-YY` where YY = next year → both read as full years (`twenty twenty-five to twenty twenty-six`). A compact hyphen next to an operator is minus (`10-3=7`). After an en or em dash the right endpoint may be signed (`-5–-2°C` → minus five to minus two degrees Celsius) |
| 12 | ordinal | `1st`, `21st`, `3ನೇ`, `5वीं`, `6औँ`, `1واں`, `১লা` | language ordinal; a regular marker on a number with an irregular ordinal gives the irregular word (Nepali `6औँ` → `छैटौँ`, Urdu `1واں` → `پہلا`); Bengali date suffixes `লা রা ঠা শে ই` (`১লা` → `পয়লা`, `২১শে` → `একুশে`, `২০শে` → `বিশে`); Sanskrit 11–19 `-दशः`, otherwise stem + `तमः` (`विंशतितमः`) |
| 13 | multi-dot numbers | `192.168.1.1`, `v2.0.1` | groups read as cardinals joined by the dot word |
| 14 | alnum token | `5G`, `COVID-19`, `A4`, `i7`, `2BHK`, `PAN ABCDE1234F`, `MH12AB1234` | letters kept in Latin; a digit run with Latin letters on both sides, or 4+ digits touching a letter, is an identifier → digit by digit; otherwise the number is read normally (`5G` → five G) |
| 15 | number | `1,23,456`, `1,234,567`, `-5`, `−.5`, `3.14`, `007`, `1857`, `12345678901` | cardinal; leading 0 → digit by digit; ≥ 9 unseparated digits → digit by digit unless a word follows (`123456789 records` is a count, also with a Latin word in Indic text); comma groups accepted only as complete Indian or Western patterns (`1,2,3` is a list); decimals → `point` + digits one by one; leading-dot decimals; negatives → minus word |
| 16 | `#n`, `No. n`, `&` between words, `@handle` | `#1`, `No. 5` | number word + numeral; `&` → and word |
| 17 | native abbreviations (core langs only) | `ಡಾ.`, `डॉ.`, `Dr.`, `Mr.`, `etc.` | expansion |

## 4. Numbers

- **Cardinals.** Indian system for every Indic language: …crore, lakh, thousand, hundred, 0–99.
  Above 99 crore the crore multiplier recurses (`1234 crore`), no arab/kharab. Western-grouped input
  (`1,234,567`) is parsed the same way and still read in the Indian system for Indic languages.
  **English** follows the input: Indian grouping (`1,00,000`) → lakh/crore, otherwise million/billion.
- **Word sources.** Indo-Aryan languages need a full 0–99 table (irregular). Dravidian languages are
  composed with per-language sandhi functions. Sources, in order: hand-written tables → Unicode CLDR
  `common/rbnf` (main @ 3d45043, 2026-05-08: bn gu hi kn ml mr ne or pa ta te ur en_IN) used as an
  automated cross-check over 0–10⁹ samples → training-corpus attestation (each generated word
  checked for occurrences in that language's TTS training text) → cited grammar/Wiktionary pages.
- **Languages without a CLDR spellout** (assamese, sanskrit, kashmiri, sindhi, konkani, maithili,
  manipuri, bodo, dogri, santali, bhojpuri, magahi, chhattisgarhi): own hand-written tables,
  checked word by word against attestation in that language's own training text and a cited
  reference where one exists. **No silent borrowing of number words:** a language uses another
  language's number words only when its own training text attests them (measured: Bhojpuri,
  Magahi, Chhattisgarhi, Maithili attest 94–100 of Hindi's 0–99 words; Dogri, Konkani, Sindhi,
  Bodo, Sanskrit, Nepali, Marathi attest only 4–32, so they get their own tables). Hindi-belt rule: for 1–10, when the language's own word differs from Hindi, the local word is used if it is the more frequent of the two in that language's own text (Bhojpuri `दू` 1162 vs `दो` 341; Magahi `दू`, `छौ`; Maithili `दू`, `नव`; Chhattisgarhi `दू`). This is attestation, not independent verification: those languages stay *attested, unverified* in REPORT.md. Assamese has its
  own table (`৪` → `চাৰি`, not Bengali `চার`). Numbers a table cannot verify are read digit by
  digit with that language's own digit names, and the gap is listed as *unverified* in REPORT.md.
- **Sanskrit:** 100–99,999 use the compound style of the training text (`पञ्चविंशत्यधिकद्विसहस्रं` = 2025, `सप्तत्यधिकनवशतोत्तरैकसहस्रं` = 1970); from 1,00,000 digit by digit. Numerals 1–4 inflect for gender and case (`त्रयः बालकाः`, `त्रीणि फलानि`). v1 reads the
  neuter counting (citation) form for all; agreement is a documented limitation, not claimed.
- **Decimals:** integer part + point word + each digit (`3.14` → three point one four), except money
  subunits (`₹10.50` → ten rupees fifty paise).
- **Years:** a bare 4-digit number is a count unless a year cue is next to it. English cues: `in`,
  `since`, `from`, `until`, `by`, `of`, `during`, `year`, `born`, `early/late/mid`, `FY/AY`, `AD/BC/CE`,
  `1998 to 2005`; Hindi cues: `सन्`, `वर्ष`, `साल` before or `में`, `से`, `तक`, `के/की/का`, `ई.` after.
  With a cue English reads pairs (`nineteen ninety-eight`, `two thousand five`, `twenty twenty-five`)
  and Hindi reads hundreds (`उन्नीस सौ अट्ठानवे`); without one both read the cardinal
  (`I counted 1998 votes` → `one thousand nine hundred ninety-eight`). Dates and two-year ranges
  (`1998-2005`, span ≤ 100) always use the year reading. **Settled with corpus counts:**
  where the training text writes years in hundreds, that language reads 1100–1999 the same way with a
  year cue or in a date: Marathi `एकोणीसशे` (669 vs `एक हजार नऊशे` 0), Bengali `উনিশশো` (1293 vs 0),
  Gujarati `ઓગણીસસો` (244 vs 0), Punjabi `ਉੱਨੀ ਸੌ` (306 vs 3), Odia `ଉଣେଇଶ ଶହ` (57 vs 0), Nepali
  `उन्नाइस सय` (528 vs 1), Urdu `انیس سو` (407 vs 0), and Bhojpuri, Magahi, Maithili and
  Chhattisgarhi `उन्नीस सौ` (706 / 630 / 484 / 1288 vs `एक हजार नौ सौ` 2 / 6 / 1 / 0). The other
  languages read years as cardinals.
- **Small tables:** Bodo has 0–99 and `जौसे` (100); Manipuri 0–99 plus noun-first thousand/lakh/crore with no hundreds digit; Santali 0–99, hundreds, thousand, lakh, crore. Anything else is digit by digit.
- **Digit-by-digit:** zero uses the language's ordinary digit word (CLDR `0`).

## 5. Lexicons

Per language a dict of concepts → words: digit names, number scales, point, minus, plus, times,
divide, equals, not-equal, less/greater (than), ≤, ≥, square, cube, power, root, by (fraction),
half, quarter, three-quarters, percent, degree, from-to (range), dot, slash, at, colon, hash/number,
and, currency names and subunits, 12 months, hour/minute/second words, dayparts, ~50 unit names.

- Months and unit names come from CLDR (ICU 78.3 data) where it exists for the locale
  (as bn bho brx doi gu hi kn kok ks mai ml mni mr ne or pa sa sat sd ta te ur en), adapted to the
  training script (Sindhi from `sd_Deva`, Manipuri transliterated to Meetei Mayek or kept as English
  loan in Latin if the transliteration cannot be verified).
- Maths/operator words: loanwords where that is how the word is spoken in Indian classrooms
  (`ಪ್ಲಸ್`, `ಮೈನಸ್`), native words where they are the norm (`बराबर`, `சமம்`). Five core languages
  are flagged `REVIEW_NEEDED` for native checkers.
- Number words never fall back (see §4). Non-number concepts (operator loanwords such as `प्लस`,
  unit names, abbreviations) may fall back along an explicit per-language chain of same-script
  relatives, never to English Latin. **Grammar is not borrowed:** templates that carry the
  relative's grammar (`squared` का वर्ग, `cubed`, `power`, `range` से, the clock `बजकर`, `neq` नहीं,
  `e.g.`/`i.e.` phrases) are taken only where a language lists them (`borrow_grammar`: Bhojpuri and
  Magahi range + clock, Maithili and Chhattisgarhi clock). Otherwise the language uses its own form
  (Nepali `+को घन` → `दुईको घन`; Maithili range `सँ`, Chhattisgarhi `ले`, Bodo `निफ्राय … सिम`, all
  unverified), the relative's bare loanword (`loan_squared` स्क्वेयर, اسکوائر), or the concept is missing. Every language's chain is printed in REPORT.md and every
  borrowed concept is listed there, so a caller can see exactly what is borrowed.
- Missing concepts: when a word is in neither the language nor its fallback chain, the rule that needed it
  is dropped and the next, plainer rule is tried (a Santali `5%` keeps the symbol; a Manipuri clock time
  is read as plain numbers if a word is missing). Each such miss is counted and listed in REPORT.md.
- Word order is data, not code: `scale_tpl`, `unit_tpl`, `money`, `date*` templates. Manipuri puts the
  noun first (`ꯂꯤꯁꯤꯡ ꯑꯅꯤ ꯇꯔꯥꯃꯥꯊꯣꯢ` = 2011, `ꯂꯨꯄꯥ …`, `ꯄꯨꯡ …`, month-first dates), as its training text does.
- Grammatical context: each language exposes an `adj()` hook for the form used before a noun or
  clock unit (Telugu `ఒక పుస్తకం`, `రెండు లక్షల రూపాయలు`; Tamil `ஒரு மணி`; Malayalam `ഒരു ദിവസം`)
  and an `attach()` hook for case/classifier suffixes (Kannada sandhi, Bengali `৫টি` → `পাঁচটি`).
  Suffix attachment applies to the last spoken word of the whole span (the currency or minute word),
  not to the digits.

## 6. Ambiguity policy

- Never verbalise something we are not confident is a number expression: bare `-`, `/`, `*`, `#`,
  `>` used as markdown stay untouched; `x` is multiplication only between digits.
- A "maths line" is the clause around the token: from the previous sentence end (`.`, `?`, `!`, `।` followed by a space) or line break to the next one. `24/7 support. 2+2=4` keeps `twenty-four seven`.
- Hyphen between numbers: compact `a-b` next to an operator (`10-3=7`) → minus; spaced `a - b` on a
  line containing `=` or another operator → minus; otherwise range (phone/date first if they match).
- Slash: `d/m/y` → date (validated); `dd/0m` (leading-zero month, valid day/month, no maths on the
  line) → day + month; `24/7` → twenty-four seven; other `a/b` → fraction (`3/04 = 0.75` → three
  quarters equals zero point seven five); inside URLs → slash word.
- A date-shaped token that fails validation (`29/02/2025`, `31/04/2025`) is read literally, part by
  part with the separator word (`twenty-nine slash zero two slash two thousand twenty-five`). It is not
  left as digits, because the TTS cannot read raw digits reliably, and it is not split into a fraction
  and a number.
- Dot: `10.30 am` → time only with am/pm or the language's hour word after it (`1.30 ಗಂಟೆಗೆ`); `15.08.2025` → date; `1.2.34` (2-digit tail) → version;
  3+ dotted groups → multi-dot; else decimal.
- Weak year cue vs a following noun: `in 1998 instalments` keeps the year reading. Both readings are
  possible (`in 1998 elections were held`), and after `in` the year is far more frequent in news text.
- Comma: a comma is a group separator only inside a complete Indian (`12,34,567`) or Western
  (`1,234,567`) pattern; anything else is punctuation and each number is read on its own
  (`1,2,3` → `one,two,three`; `5, 6 and 7`).

## 6b. Further rules

- Typed-endpoint ranges: a money or clock span followed by a dash tries the same rule again, and two
  endpoints join with the range template (`₹5–₹10` → `five rupees to ten rupees`).
- Compound durations `1h 30m [5s]` before units (`m` = minutes only after an hour part).
- Vehicle registrations `KA-01-AB-1234` (letters kept, digit runs digit by digit); UPI addresses
  `name@handle` read like an email; unary `±`/`+` before a digit with no left operand.
- Scale words match in any case (`Lakh`, `CRORE`); fraction percent/unit tails (`1/2 kg` singular).
- `fractions_special` holds number words and is not borrowed from a fallback (only the Hindi-belt four
  may borrow it); languages without their own word read `{a} <division word> {b}` with own numerals.
- Language-owned ordinals for the Hindi-belt four (Bhojpuri/Magahi/Chhattisgarhi `पहिला`; Maithili
  `पहिल दोसर तेसर चारिम … +म`); Urdu `ویں` on an irregular stem takes the masculine oblique (unverified).

## 7. Testing

- pytest under `tests/text/`: per-language golden cases (numbers 0–100 spot
  checks, scales, each span kind), a fixed ladder of number inputs for all 7 test languages,
  idempotence (normalising twice changes nothing), passthrough (text without numbers/symbols is
  byte-identical, markdown/whitespace preserved), no ASCII or native digits remain, and
  deterministic speed (≥ 2,000 sentences/s on one core).
- Capability gates: for every language and capability (cardinal, ordinal, suffix sandhi, clock, money,
  operator words, units) REPORT.md marks **verified** (cited source, or native-checked goldens),
  **attested** (every word occurs in that language's training text, grammar not checked),
  **digit fallback** (gaps read digit by digit) or **unverified**. A capability is only claimed as
  verified with an exact golden test, e.g. Marathi `2री` → `दुसरी`.
- The engine keeps no per-call state on shared objects (thread-local input), so concurrent calls
  cannot mix text; a test runs eight threads against the serial output.
- Dev-only tools (not imported by the package): `tools/text/cldr_check.py` (PyICU + CLDR rbnf),
  `tools/text/corpus_check.py` (word attestation in training text).

## 8. Clean-room

Written from scratch; no other normaliser's code or tables were used. Word data comes from hand-written tables, Unicode CLDR (Unicode License
V3 / DFS-2016; cited) and corpus attestation.
