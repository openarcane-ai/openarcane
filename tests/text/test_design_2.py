"""Design rules, part 2."""
import threading

import pytest

from openarcane.text import normalize

CASES = [
    # 2 month-year dates
    ("english", "August 2025", "August twenty twenty-five"),
    # 3 money and round counts are quantities
    ("english", "₹100000000", "one hundred million rupees"),
    ("english", "7000000000 records", "seven billion records"),
    ("english", "Ticket 123456789", "Ticket one two three four, five six seven, eight nine"),
    # 4 code labels: label syntax only, no over-consumption
    ("english", "Account balance: 1250 rupees", "Account balance: one thousand two hundred fifty rupees"),
    ("english", "OTP: 123456 10:30", "OTP: one two three, four five six ten thirty"),
    ("english", "OTP for login is 482913.", "OTP for login is four eight two, nine one three."),
    # 5 minus in maths beats range and identifier readings
    ("english", "5 - 2 kg = 3 kg", "five minus two kilograms equals three kilograms"),
    ("english", "x-3=7", "x minus three equals seven"),
    ("english", "COVID-19 cases", "COVID nineteen cases"),
    # 6 signs and units on structured numbers
    ("hindi", "-2 1/2 किलो", "माइनस ढाई किलो"),
    ("english", "-1.2e-3 kg", "minus one point two times ten to the power of minus three kilograms"),
    # 7 spacing kept, any number of spaces
    ("english", "2   + 3 = 5", "two   plus three equals five"),
    ("english", "10  km", "ten  kilometres"),
    # 8 named-month dates are validated
    ("english", "29 February 2025", "twenty-nine February two thousand twenty-five"),
    ("english", "29 February 2024", "twenty-ninth February twenty twenty-four"),
    # 9 native month names and date labels
    ("hindi", "1 अगस्त 1998", "एक अगस्त उन्नीस सौ अट्ठानवे"),
    ("hindi", "अगस्त 1998 में", "अगस्त उन्नीस सौ अट्ठानवे में"),
    ("english", "Date: 15/8", "Date: fifteenth August"),
    ("english", "15/8", "fifteen by eight"),
    # 11 versions are not dates
    ("english", "v1.2.2025", "v one dot two dot two thousand twenty-five"),
    # 12 count context accepts Latin words in Indic text
    ("hindi", "123456789 records", "बारह करोड़ चौंतीस लाख छप्पन हजार सात सौ नवासी records"),
    # 13 24x7 yields to arithmetic
    ("english", "24×7=168", "twenty-four times seven equals one hundred sixty-eight"),
    ("english", "24/7 support", "twenty-four seven support"),
    # 14 per mille is not percent
    ("english", "5‰", "five per mille"),
    ("hindi", "5‰", "पाँच प्रति हज़ार"),
    # 15 singular units and clock (Telugu goldens are on the REVIEW_NEEDED list)
    ("telugu", "1:01", "ఒంటి గంట ఒక నిమిషం"),
    ("telugu", "1 hr", "ఒక గంట"),
    ("hindi", "1 hr; 2 hr", "एक घंटा; दो घंटे"),
    # 16 URL punctuation is read, never dropped
    ("english", "https://x.in/a;b,c!d", "x dot in slash a semicolon b comma c exclamation mark d"),
    # 17 phone cues
    ("english", "Call 112", "Call one one two"),
    ("english", "Call 100 people", "Call one hundred people"),
    ("hindi", "फोन 112", "फोन एक एक दो"),
    # 18 scale words outside money
    ("hindi", "5 lakh", "पाँच लाख"),
    ("english", "5k views", "five thousand views"),
    # 20 ratio cue beats clock shape
    ("english", "Ratio 12:30", "Ratio twelve is to thirty"),
    ("english", "12:30", "twelve thirty"),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_design_2(lang, text, expected):
    assert normalize(text, lang) == expected


def test_concurrent_calls_do_not_share_input():  # point 1
    inputs = ["OTP: 123456", "HELLO 99", "Call 112", "₹5 lakh", "x-3=7"] * 40
    serial = [normalize(t, "english") for t in inputs]
    out = [None] * len(inputs)
    barrier = threading.Barrier(8)

    def work(k):
        barrier.wait()
        for i in range(k, len(inputs), 8):
            out[i] = normalize(inputs[i], "english")

    threads = [threading.Thread(target=work, args=(k,)) for k in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert out == serial
