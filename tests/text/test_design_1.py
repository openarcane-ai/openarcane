"""Design rules, part 1. Each case: (language, input, expected)."""
import pytest

from openarcane.text import normalize

CASES = [
    # compositional spans
    ("english", "₹5+₹2=₹7", "five rupees plus two rupees equals seven rupees"),
    # counts
    ("english", "There are 123456789 records.",
     "There are one hundred twenty-three million four hundred fifty-six thousand seven hundred eighty-nine records."),
    ("english", "Ticket 123456789", "Ticket one two three four, five six seven, eight nine"),
    # year needs a cue
    ("english", "I counted 1998 votes.", "I counted one thousand nine hundred ninety-eight votes."),
    ("english", "In 1998 we won.", "In nineteen ninety-eight we won."),
    ("english", "the 1990s and 80s", "the nineteen nineties and eighties"),
    ("hindi", "1998 में 1998 वोट", "उन्नीस सौ अट्ठानवे में एक हजार नौ सौ अट्ठानवे वोट"),
    # calendar validation (literal reading instead of leaving digits)
    ("english", "Date: 29/02/2025", "Date: twenty-nine slash zero two slash two thousand twenty-five"),
    ("english", "29/02/2024", "twenty-ninth February twenty twenty-four"),
    # comma lists
    ("english", "1,2,3", "one,two,three"),
    # compact minus
    ("english", "10-3=7", "ten minus three equals seven"),
    # maths beats the dd/0m date guess
    ("english", "3/04 = 0.75", "three quarters equals zero point seven five"),
    ("english", "15/08 is", "fifteenth August is"),
    # suffix on the final spoken head
    ("kannada", "ಬೆಳಿಗ್ಗೆ 10:30ಕ್ಕೆ", "ಬೆಳಿಗ್ಗೆ ಹತ್ತು ಗಂಟೆ ಮೂವತ್ತು ನಿಮಿಷಕ್ಕೆ"),
    ("kannada", "₹5ಕ್ಕೆ", "ಐದು ರೂಪಾಯಿಗೆ"),
    # dayparts by value
    ("hindi", "12:00 AM", "रात बारह बजे"),
    ("hindi", "12:00 PM", "दोपहर बारह बजे"),
    # before-noun forms
    ("tamil", "1:30", "ஒரு மணி முப்பது நிமிடம்"),
    ("telugu", "1 పుస్తకం", "ఒక పుస్తకం"),
    ("malayalam", "1 ദിവസം", "ഒരു ദിവസം"),
    # money fractions
    ("hindi", "₹1.5; ₹1.05", "एक रुपया पचास पैसे; एक रुपया पाँच पैसे"),
    ("english", "costs ₹1.255", "costs one point two five five rupees"),
    # signs and leading dots
    ("english", "−₹5.50", "minus five rupees and fifty paise"),
    ("english", "−.5", "minus zero point five"),
    ("english", "value .75", "value zero point seven five"),
    # English unit plurals
    ("english", "1 kg; 5 kg", "one kilogram; five kilograms"),
    # compound units
    ("english", "5 MB/s; 5 Mb/s; 5 m²", "five megabytes per second; five megabits per second; five square metres"),
    ("english", "5 Mbps", "five megabits per second"),
    # scientific notation
    ("english", "1.2e-3", "one point two times ten to the power of minus three"),
    # identifiers
    ("english", "PAN ABCDE1234F", "PAN ABCDE one two three four F"),
    ("english", "COVID-19 and 5G", "COVID nineteen and five G"),
    # written code groups
    ("english", "OTP: 12 34 56", "OTP: one two, three four, five six"),
    # mixed numbers
    ("english", "2 1/2 kg", "two and one half kilograms"),
    ("hindi", "2 1/2 किलो", "ढाई किलो"),
    # financial years
    ("english", "FY 2025-26", "FY twenty twenty-five to twenty twenty-six"),
    ("hindi", "FY 2025-26", "FY दो हजार पच्चीस से दो हजार छब्बीस"),
    # whitespace inside spans
    ("english", "### 2  +\n3 =\t5", "### two  plus\nthree equals\tfive"),
    # URL / email symbols (scheme dropped: rejected part)
    ("english", "https://x.in/?a=1&b=2", "x dot in slash question mark a equals one and b equals two"),
    ("english", "a+b2@x.in", "a plus b two at x dot in"),

    ("english", "Available 24/7.", "Available twenty-four seven."),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_design_review(lang, text, expected):
    assert normalize(text, lang) == expected
