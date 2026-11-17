"""Design rules, part 5."""
import pytest

from openarcane.text import normalize

CASES = [
    # 1 alphabetic scale words in any case
    ("english", "₹1.5 Lakh", "one point five lakh rupees"),
    ("english", "Rs 1.5 Crore", "one point five crore rupees"),
    # 2 compact subtraction after a unit
    ("english", "5 kg-3 kg=2 kg", "five kilograms minus three kilograms equals two kilograms"),
    ("english", "COVID-19", "COVID nineteen"),
    # 3 a code stops before a named-month date
    ("english", "OTP: 123456 15 Aug 2025", "OTP: one two three, four five six fifteenth August twenty twenty-five"),
    # 4 tight scientific notation with a unit
    ("english", "1.2e-3kg", "one point two times ten to the power of minus three kilograms"),
    # 5 ranges between typed endpoints
    ("english", "₹5–₹10", "five rupees to ten rupees"),
    ("english", "10:30–11:30", "ten thirty to eleven thirty"),
    # 6 percent and unit tails on slash and vulgar fractions (a proper fraction takes the singular)
    ("english", "1/2 kg", "one half kilogram"),
    ("english", "2½%", "two and one half percent"),
    ("english", "15/08", "fifteenth August"),
    # 7 a written native quantity as the right operand, only after a quantity with digits
    ("hindi", "5 किलो+तीन किलो=आठ किलो", "पाँच किलो प्लस तीन किलो बराबर आठ किलो"),
    ("hindi", "राम+श्याम", "राम+श्याम"),
    # 8 any horizontal spacing around date slashes
    ("english", "15  /  08  /  2025", "fifteenth August twenty twenty-five"),
    # 10 number-bearing fraction phrases are not borrowed; own numerals with the borrowed division word
    ("bodo", "3/4", "थाम बटा ब्रै"),
    ("bodo", "½", "खावसे"),  # own word for half (attested, unverified)
    ("bhojpuri", "3/4", "तीन चौथाई"),  # the Hindi-belt languages may borrow it (Hindi numerals are theirs)
    # 11 Sindhi two is the implosive ॿ
    ("sindhi", "2", "ॿ"),
    # 12 Urdu ویں on an irregular ordinal: masculine oblique (unverified)
    ("urdu", "6ویں دن", "چھٹے دن"),
    ("urdu", "5ویں", "پانچویں"),
    # 13 Hindi-belt ordinals as their own text writes them
    ("bhojpuri", "1st", "पहिला"),
    ("maithili", "1st", "पहिल"),
    ("maithili", "2nd", "दोसर"),
    ("maithili", "5th", "पाँचम"),
    # 14 Malayalam case endings on a noun ending in an inherent a
    ("malayalam", "₹5ക്ക്", "അഞ്ച് രൂപയ്ക്ക്"),
    ("malayalam", "5ക്ക്", "അഞ്ചിന്"),
    # 15 a dotted time before an hour word
    ("kannada", "1.30 ಗಂಟೆಗೆ", "ಒಂದು ಗಂಟೆ ಮೂವತ್ತು ನಿಮಿಷಕ್ಕೆ"),
    ("english", "10.30", "ten point three zero"),
    # 16 compound durations
    ("english", "1h 30m", "one hour thirty minutes"),
    ("english", "5 m", "five metres"),
    # 17 vehicle registration numbers
    ("english", "KA-01-AB-1234", "KA zero one AB one two three four"),
    # 18 UPI addresses
    ("english", "Pay ravi@okicici", "Pay ravi at okicici"),
    # 19 decilitre denominators
    ("english", "5 mg/dL", "five milligrams per decilitre"),
    # 20 unary signs
    ("english", "±5%", "plus or minus five percent"),
    ("english", "+5°C", "plus five degrees Celsius"),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_round5(lang, text, expected):
    assert normalize(text, lang) == expected
