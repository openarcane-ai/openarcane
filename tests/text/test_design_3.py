"""Design rules, part 3."""
import pytest

from openarcane.text import normalize

CASES = [
    # 1 a currency, unit or scale after a phone-shaped number makes it an amount
    ("english", "9876543210 INR",
     "nine billion eight hundred seventy-six million five hundred forty-three thousand two hundred ten rupees"),
    ("english", "9876543210 kg",
     "nine billion eight hundred seventy-six million five hundred forty-three thousand two hundred ten kilograms"),
    ("english", "Call 9876543210 now", "Call nine eight seven six five, four three two one zero now"),
    # 2 code groups stop before a date
    ("english", "OTP: 123456 15/08/2025", "OTP: one two three, four five six fifteenth August twenty twenty-five"),
    # 3 operators after percentages
    ("english", "5%+3%=8%", "five percent plus three percent equals eight percent"),
    # 4 scientific money amounts
    ("english", "INR 1.2e6", "one point two times ten to the power of six rupees"),
    # 5 descending scale components in one amount
    ("english", "₹1 crore 25 lakh", "one crore twenty-five lakh rupees"),
    # 6 spacing kept on unit tails of structured quantities
    ("english", "-1.2e-3  kg", "minus one point two times ten to the power of minus three  kilograms"),
    # 7 signed written fractions
    ("english", "-3/4", "minus three quarters"),
    # 8 vulgar fractions with units
    ("english", "2½ kg", "two and one half kilograms"),
    # 9 signed right endpoint after an en dash
    ("english", "-5–-2°C", "minus five to minus two degrees Celsius"),
    # 10 scaled quantities with units
    ("english", "5 lakh kg", "five lakh kilograms"),
    # 11 before-noun form on scaled quantities
    ("telugu", "2 lakh రూపాయలు", "రెండు లక్షల రూపాయలు"),
    # 12 native label connectors
    ("hindi", "ओटीपी है 123456", "ओटीपी है एक दो तीन, चार पाँच छह"),
    # 13 phone cues after the number
    ("hindi", "112 पर फोन करें", "एक एक दो पर फोन करें"),
    ("urdu", "1122 پر فون کریں", "ایک ایک دو دو پر فون کریں"),
    # 14 no field swap for year-first dates
    ("english", "Date: 2025-15-08", "Date: two thousand twenty-five hyphen fifteen hyphen zero eight"),
    ("english", "Date: 08/15/2025", "Date: fifteenth August twenty twenty-five"),
    # 15 a date label overrides the version reading of d.m.yy
    ("english", "DOB: 15.08.25", "DOB: fifteenth August twenty-five"),
    # 16 decimal ratio operands
    ("english", "Ratio 1:2.5", "Ratio one is to two point five"),
    # 17 maths context ends at a sentence end
    ("english", "24/7 support. 2+2=4", "twenty-four seven support. two plus two equals four"),
    # 18 native currency abbreviation after the amount
    ("hindi", "5 रु.", "पाँच रुपये."),  # at a line end the abbreviation dot is also the full stop (corpus audit)
    ("hindi", "5 रु. दिए", "पाँच रुपये दिए"),
    # 19 inflected Telugu hour word gives its case ending to the last word (REVIEW_NEEDED: formal rendering)
    ("telugu", "10:30 గంటలకు", "పది గంటల ముప్పై నిమిషాలకు"),
    ("telugu", "10 గంటలకు", "పది గంటలకు"),
    # 20 Hindi-belt numerals: the local word when it is the more frequent one in the language's own text
    ("bhojpuri", "2 गो", "दू गो"),
    ("maithili", "9", "नव"),
    ("magahi", "6", "छौ"),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_round3(lang, text, expected):
    assert normalize(text, lang) == expected
