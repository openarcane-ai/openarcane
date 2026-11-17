"""Every language on a fixed set of written forms: no crash, no ASCII or native digit left in the output, and the
normaliser is idempotent (a second pass changes nothing). Text without anything to verbalise passes through."""
import re

import pytest

from openarcane.text import LANGUAGES, normalize

INPUTS = [
    "12", "105", "2025", "1,25,000", "12,345,678", "3.75", "-42", "1/2", "2½", "3 1/4", "45%", "10-15",
    "₹1,250.50", "Rs. 500", "$20", "€5.5", "£3", "INR 2 lakh", "₹1 crore 25 lakh",
    "15/08/2025", "2025-08-15", "15 Aug 2025", "10:30", "7:05 pm", "1990s",
    "Call 9876543210", "+91 98765 43210", "OTP: 482913", "PIN 560001", "1800-123-4567",
    "5 kg", "2.5 km", "30°C", "100 ml", "2+3=5", "10 × 4", "x^2", "√16", "3:2",
    "24/7", "1st", "2nd", "COVID-19", "www.example.com", "info@example.org", "v2.1.3",
]
DIGIT = re.compile(r"[0-9०-९০-৯੦-੯૦-૯୦-୯௦-௯౦-౯"
                   r"೦-೯൦-൯۰-۹٠-٩꯰-꯹᱐-᱙]")
PASSTHROUGH = ["### Heading\n\n- item  one\n\t**bold** text", "  spaces   kept  ", "line one\r\nline two", ""]


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_no_crash_no_digits_idempotent(lang):
    for text in INPUTS:
        out = normalize(text, lang)
        assert not DIGIT.search(out), (lang, text, out)
        assert normalize(out, lang) == out, (lang, text, out)


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_passthrough(lang):
    for text in PASSTHROUGH:
        assert normalize(text, lang) == text
