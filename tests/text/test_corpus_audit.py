"""Bugs found by running the normaliser over sampled training rows (REPORT.md, corpus audit)."""
import pytest

from openarcane.text import normalize

CASES = [
    # an abbreviation never starts inside a word: the vowel sign or virama before it is not \w
    ("telugu", "దాసరిక్కూడా.", "దాసరిక్కూడా."),
    ("telugu", "శ్రీశ్రీ.", "శ్రీశ్రీ."),
    ("bengali", "ঠান্ডা.", "ঠান্ডা."),
    ("telugu", "డా. రావు", "డాక్టర్ రావు"),
    ("bengali", "ডা. রায়", "ডাক্তার রায়"),
    # a title needs the name after it
    ("english", "see Dr.", "see Dr."),
    ("english", "Mr. Woods", "Mister Woods"),
    # an abbreviation dot at a line end is also the full stop
    ("english", "apples etc.", "apples et cetera."),
    ("english", "apples etc. more", "apples et cetera more"),
    ("tamil", "80 கி.மீ.", "எண்பது கிலோமீட்டர்."),
    ("tamil", "சதுர கி.மீ. வரை", "சதுர கிலோமீட்டர் வரை"),
    ("telugu", "5 కి.మీ.\nఇది", "ఐదు కిలోమీటర్లు.\nఇది"),
    # attested dollar words (ᱢᱚᱲᱮ ᱰᱚᱞᱟᱨ, ꯗꯣꯂꯔ ꯑꯅꯤ in the text)
    ("santali", "$5", "ᱢᱚᱲᱮ ᱰᱚᱞᱟᱨ"),
    ("manipuri", "$5", "ꯗꯣꯂꯔ ꯃꯉꯥ"),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_corpus_audit(lang, text, expected):
    assert normalize(text, lang) == expected


ATTESTED = [
    # final attestation audit: the training text's own spelling replaces a CLDR spelling that never occurs
    ("bengali", "250", "দুশো পঞ্চাশ"),  # দুশো 180 vs দুইশো 0
    ("bengali", "600", "ছশো"),
    ("bengali", "2022 সালে", "দুহাজার বাইশ সালে"),  # দুহাজার 504 vs দুই হাজার 87
    ("bengali", "12000", "বারো হাজার"),
    ("nepali", "39", "उन्चालिस"),
    ("urdu", "79", "اناسی"),
    ("odia", "99", "ଅନେଶ୍ୱତ"),
    ("santali", "15/08/2025", "ᱜᱮᱞᱢᱚᱲᱮ ᱟᱜᱚᱥᱴ ᱵᱟᱨ ᱦᱟᱡᱟᱨ ᱵᱟᱨᱜᱮᱞ ᱢᱚᱲᱮ"),  # ᱟᱜᱚᱥᱴ 51 vs ᱟᱜᱟᱥᱛ 0
]


@pytest.mark.parametrize("lang,text,expected", ATTESTED)
def test_attested_spelling(lang, text, expected):
    assert normalize(text, lang) == expected
