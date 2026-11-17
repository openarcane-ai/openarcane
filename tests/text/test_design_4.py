"""Design rules, part 4, plus fixes found by
comparing outputs with another normaliser."""
import pytest

from openarcane.text import normalize

CASES = [
    # 1 code groups stop before a year-first date too
    ("english", "OTP: 123456 2025-08-15", "OTP: one two three, four five six fifteenth August twenty twenty-five"),
    # 2 decimal operands are complete atoms: a division, never a special fraction
    ("english", "1/2.5 = 0.4", "one by two point five equals zero point four"),
    ("english", "Version 1.2/3.4", "Version one point two by three point four"),
    # 3 signed vulgar mixed numbers
    ("english", "-2½ kg", "minus two and one half kilograms"),
    ("english", "-½", "minus one half"),
    # 4 operators after native-script operands
    ("hindi", "5 किलो+3 किलो=8 किलो", "पाँच किलो प्लस तीन किलो बराबर आठ किलो"),
    # 5 inequalities are maths context
    ("english", "3/04 < 1", "three quarters is less than one"),
    ("english", "5 < 10", "five is less than ten"),
    # 6 phone-vs-quantity uses the same spacing as the unit rule
    ("english", "6000000001  kg", "six billion one  kilograms"),
    # 7 compound units after structured numbers
    ("english", "1e3 MB/s", "one times ten to the power of three megabytes per second"),
    # 8 scientific percentages
    ("english", "1e3%", "one times ten to the power of three percent"),
    # 9 Unicode URL text keeps letter+mark runs
    ("hindi", "https://उदाहरण.भारत", "उदाहरण डॉट भारत"),
    # 10 spaced date separators; a spaced slash in maths is division
    ("english", "15 / 08 / 2025", "fifteenth August twenty twenty-five"),
    ("english", "Score 6 / 3 / 2 = 1", "Score six divided by three divided by two equals one"),
    ("english", "and / or", "and / or"),
    # 11 time zones are kept: expanded where a word exists, otherwise left as written
    ("english", "10:30 IST", "ten thirty Indian Standard Time"),
    ("hindi", "10:30 IST", "दस बजकर तीस मिनट IST"),
    # 12 Bengali date suffixes
    ("bengali", "২১শে ফেব্রুয়ারি", "একুশে ফেব্রুয়ারি"),
    ("bengali", "১লা বৈশাখ", "পয়লা বৈশাখ"),
    ("bengali", "২০শে মে", "বিশে মে"),
    ("bengali", "৪ঠা জুলাই", "চৌঠা জুলাই"),
    ("bengali", "৫ই মে", "পাঁচই মে"),
    # 13-14 the regular marker on an irregular number gives the irregular ordinal
    ("nepali", "6औँ", "छैटौँ"),
    ("nepali", "5औँ", "पाँचौँ"),
    ("urdu", "1واں", "پہلا"),
    ("urdu", "5واں", "پانچواں"),
    ("punjabi", "1ਵਾਂ", "ਪਹਿਲਾ"),
    # 15 Sanskrit ordinals above ten
    ("sanskrit", "11th", "एकादशः"),
    ("sanskrit", "20th", "विंशतितमः"),
    ("sanskrit", "100th", "शततमः"),
    # 16 native code-label connectors, with negative controls
    ("tamil", "ஓடிபி எண் 123456", "ஓடிபி எண் ஒன்று இரண்டு மூன்று, நான்கு ஐந்து ஆறு"),
    ("hindi", "ओटीपी नंबर 123456", "ओटीपी नंबर एक दो तीन, चार पाँच छह"),
    ("tamil", "ஓடிபி எண்ணிக்கை 5", "ஓடிபி எண்ணிக்கை ஐந்து"),
    ("tamil", "பேருந்து எண் 123456",
     "பேருந்து எண் ஒரு லட்சத்து இருபத்து மூன்றாயிரத்து நானூற்று ஐம்பத்து ஆறு"),
    # 17 a missing minor-unit word falls back to a decimal amount with the currency
    ("manipuri", "₹1.50", "ꯂꯨꯄꯥ ꯑꯃ ꯄꯩꯁꯥ ꯌꯥꯡꯈꯩ"),  # superseded by language review: Manipuri ꯄꯩꯁꯥ (paisa) added
    ("hindi", "₹1.50", "एक रुपया पचास पैसे"),
    # 18 fallback phrases with grammar are not borrowed: own forms, a bare loanword, or plain numbers
    ("nepali", "2^3", "दुईको घन"),
    ("konkani", "2^2", "दोन स्क्वेयर"),
    ("maithili", "5-7", "पाँच सँ सात"),
    ("bodo", "10:30", "जि थामजि"),
    ("bodo", "10:30 PM", "जि थामजि PM"),
    # 19 year readings in hundreds (settled with corpus counts)
    ("marathi", "वर्ष 1998", "वर्ष एकोणीसशे अठ्ठ्याण्णव"),
    ("gujarati", "વર્ષ 1998", "વર્ષ ઓગણીસસો અઠ્ઠાણું"),
    # 20 Indian grouping survives decimals
    ("english", "1,00,000.5", "one lakh point five"),
    # superscripts after a number: one space
    ("english", "3²", "three squared"),
    ("hindi", "3²", "तीन का वर्ग"),
    # Gujarati hundreds are joined (corpus: એકસો 129 vs 12, બસો 97 vs 0)
    ("gujarati", "250", "બસો પચાસ"),
    # fixes found by comparing outputs with another normaliser
    ("hindi", "7 PM", "शाम सात बजे"),
    ("bengali", "7 PM", "সন্ধ্যা সাতটা"),
    ("tamil", "7 PM", "இரவு ஏழு மணி"),
    ("telugu", "2½", "రెండున్నర"),
    ("tamil", "-5", "மைனஸ் ஐந்து"),
    ("assamese", "-5", "মাইনাছ পাঁচ"),
    ("malayalam", "20000", "ഇരുപതിനായിരം"),
    ("assamese", "43", "তিয়াল্লিছ"),
    ("assamese", "71", "এসত্তৰ"),
    ("assamese", "60 km/h", "ষাঠি কিলোমিটাৰ প্ৰতি ঘণ্টা"),
    ("assamese", "10:30", "দহ বাজি ত্ৰিছ মিনিট"),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_r4(lang, text, expected):
    assert normalize(text, lang) == expected
