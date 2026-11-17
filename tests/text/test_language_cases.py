"""Per-language cases. The Kannada, Telugu, Malayalam, Hindi and Tamil items are REVIEW_NEEDED language facts
(docs/text/REPORT.md §3)."""
import pytest

from openarcane.text import normalize

CASES = [
    # --- Dravidian (kn te ta ml) ---
    ("telugu", "60 km/h", "గంటకు అరవై కిలోమీటర్లు"),
    ("tamil", "60 km/h", "மணிக்கு அறுபது கிலோமீட்டர்"),
    ("malayalam", "60 km/h", "മണിക്കൂറിൽ അറുപത് കിലോമീറ്റർ"),
    ("kannada", "5kgಗೆ", "ಐದು ಕಿಲೋಗ್ರಾಂಗೆ"),
    ("telugu", "2.1 kg", "రెండు పాయింట్ ఒకటి కిలోగ్రాములు"),
    ("telugu", "1/20", "ఇరవై భాగాల్లో ఒక భాగం"),
    ("telugu", "5kgకి", "ఐదు కిలోగ్రాములకు"),
    ("tamil", "2.1 kg", "இரண்டு புள்ளி ஒன்று கிலோகிராம்"),
    ("tamil", "5kgக்கு", "ஐந்து கிலோகிராமுக்கு"),
    ("malayalam", "50%ത്തിന്", "അമ്പത് ശതമാനത്തിന്"),
    ("malayalam", "2¼ kg", "രണ്ടേകാൽ കിലോഗ്രാം"),
    ("malayalam", "5kgക്ക്", "അഞ്ച് കിലോഗ്രാമിന്"),
    # --- major Indo-Aryan ---
    ("hindi", "यह ₹1 में मिला।", "यह एक रुपये में मिला।"),
    ("hindi", "1 hr में काम पूरा हुआ।", "एक घंटे में काम पूरा हुआ।"),
    ("marathi", "20वा वाढदिवस", "विसावा वाढदिवस"),
    ("marathi", "9वा क्रमांक", "नववा क्रमांक"),
    ("marathi", "10:01", "दहा वाजून एक मिनिट"),
    ("marathi", "1 min", "एक मिनिट"),
    ("marathi", "1% वाढ झाली.", "एक टक्का वाढ झाली."),
    ("bengali", "৫:০০টায় আসুন।", "পাঁচটায় আসুন।"),
    ("bengali", "৫:৩০টায় আসুন।", "পাঁচটা বেজে ত্রিশ মিনিটে আসুন।"),
    ("gujarati", "43 લોકો", "ત્રેતાલીસ લોકો"),
    ("gujarati", "78 લોકો", "ઇઠ્યોતેર લોકો"),
    ("gujarati", "6મો દિવસ", "છઠ્ઠો દિવસ"),
    ("gujarati", "₹1માં મળે છે.", "એક રૂપિયામાં મળે છે."),
    ("punjabi", "1 hr ਲਈ", "ਇੱਕ ਘੰਟੇ ਲਈ"),
    ("odia", "୧:୦୦ ବେଳେ ଆସନ୍ତୁ।", "ଗୋଟାଏ ବେଳେ ଆସନ୍ତୁ।"),
    ("odia", "୧୦:୦୦ଟାରେ ଆସନ୍ତୁ।", "ଦଶଟାରେ ଆସନ୍ତୁ।"),
    ("assamese", "3 1/2 kg", "চাৰে তিনি কিলোগ্ৰাম"),
    ("assamese", "7 PM বজাত আহিব।", "সন্ধিয়া সাত বজাত আহিব।"),
    ("assamese", "5-10 kg", "পাঁচৰ পৰা দহ কিলোগ্ৰাম"),
    ("nepali", "2री पत्नी", "दोस्री पत्नी"),
    ("urdu", "2ویں اجلاس میں", "دوسرے اجلاس میں"),
    ("urdu", "₹1 میں ملتا ہے۔", "ایک روپے میں ملتا ہے۔"),
    # --- small Indo-Aryan and Sanskrit ---
    ("sanskrit", "33", "त्रयस्त्रिंशत्"),
    ("sanskrit", "83", "त्र्यशीतिः"),
    ("sanskrit", "100000", "लक्षं"),
    ("kashmiri", "2025", "زٕ ساس پٕنٛژٕہ"),
    ("kashmiri", "25%", "پٕنٛژٕہ فیصد"),
    ("kashmiri", "1/2", "اوٚڑ"),
    ("kashmiri", "2½", "ڈاے"),  # the training text's spelling, not ڈٲی
    ("kashmiri", "6th", "شیٚیِم"),
    ("kashmiri", "4:00", "ژورِ بجہِ"),
    ("konkani", "2½", "अडीच"),
    ("konkani", "5 km", "पांच किलोमीटर"),
    ("dogri", "2½", "ढाई"),
    ("dogri", "5th", "पंजमां"),
    ("dogri", "10:30", "दस बजे त्रीह् मिंट"),  # साढ़े is mostly "our" in the Dogri text
    ("sindhi", "2½", "अढाई"),
    ("sindhi", "5th", "पंजों"),
    ("maithili", "₹2", "दू रुपैया"),
    ("bhojpuri", "6th बेर", "छठवाँ बेर"),
    # --- Bodo, Manipuri, Santali, English ---
    ("bodo", "60", "दजि"),
    ("bodo", "62", "दजिनै"),
    ("bodo", "200", "नैजौ"),
    ("bodo", "₹2000", "नैरोजा रां"),
    ("bodo", "25%", "नैजिबा जौखोन्दो"),
    ("bodo", "2½", "नै आरो खावसे"),  # own half word
    ("bodo", "₹1.50", "से रां बाजि पैसा"),
    ("manipuri", "1st", "ꯑꯍꯥꯟꯕ"),
    ("manipuri", "2nd", "ꯑꯅꯤꯁꯨꯕ"),
    ("manipuri", "100", "ꯆꯥꯃ"),
    ("manipuri", "400", "ꯆꯥꯃꯔꯤ"),
    ("manipuri", "90", "ꯃꯔꯤꯐꯨꯇꯔꯥ"),
    ("manipuri", "2½", "ꯑꯅꯤꯒ ꯃꯈꯥꯏ"),
    ("manipuri", "5 kg", "ꯀꯤꯂꯣꯒ꯭ꯔꯥꯝ ꯃꯉꯥ"),
    ("santali", "2nd", "ᱫᱚᱥᱟᱨ"),
    ("santali", "3rd", "ᱛᱮᱥᱟᱨ"),
    ("english", "Ms. Rao", "Miz Rao"),
    ("english", "13:00", "thirteen hundred hours"),
    ("english", "00:00", "midnight"),
    ("english", "10:30:01", "ten thirty and one second"),
]


@pytest.mark.parametrize("lang,text,expected", CASES)
def test_language_review(lang, text, expected):
    assert normalize(text, lang) == expected


# spellings found by comparing outputs with another normaliser, settled by the training text
SPELLING = [
    ("kannada", "30°C", "ಮೂವತ್ತು ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್"),  # ಸೆಲ್ಸಿಯಸ್ 13 vs ಸೆಲ್ಶಿಯಸ್ 4
    ("kannada", "90°", "ತೊಂಬತ್ತು ಡಿಗ್ರಿ"),  # CLDR ಡಿಗ್ರಿಯು is a case form; ಡಿಗ್ರಿ 65
    ("bengali", "30°C", "ত্রিশ ডিগ্রি সেলসিয়াস"),  # ডিগ্রি 95 vs ডিগ্রী 21
]


@pytest.mark.parametrize("lang,text,expected", SPELLING)
def test_spelling_from_text(lang, text, expected):
    assert normalize(text, lang) == expected


# bugs found by comparing outputs with another normaliser
FROM_COMPARISON = [
    ("odia", "ପିନ୍‌କୋଡ୍ 523955", "ପିନ୍‌କୋଡ୍ ପାଞ୍ଚ ଦୁଇ ତିନି, ନଅ ପାଞ୍ଚ ପାଞ୍ଚ"),  # keyword with virama + joiner
    ("hindi", "पिनकोड 560001", "पिनकोड पाँच छह शून्य, शून्य शून्य एक"),
    ("odia", "କୋଭିଡ଼୍-୧୯", "କୋଭିଡ଼୍-ଉଣେଇଶ"),  # a virama ends a word: the hyphen is not minus
    ("kannada", "ಕೋವಿಡ್-19", "ಕೋವಿಡ್-ಹತ್ತೊಂಬತ್ತು"),
    ("hindi", "तापमान -5", "तापमान माइनस पाँच"),  # a spaced sign is still minus
    ("telugu", "5.1 కోట్ల", "ఐదు పాయింట్ ఒకటి కోట్ల"),  # decimal before a native noun keeps the digit name
    ("telugu", "1956 వరకు", "వెయ్యి తొమ్మిది వందల యాభై ఆరు వరకు"),  # a free postposition keeps its space
    ("telugu", "2020 లో", "రెండు వేల ఇరవైలో"),  # a case ending still joins
]


@pytest.mark.parametrize("lang,text,expected", FROM_COMPARISON)
def test_from_comparison(lang, text, expected):
    assert normalize(text, lang) == expected


FROM_COMPARISON_2 = [
    ("english", "displaced 9 tons.", "displaced nine tons."),  # a written ton is not changed to tonne
    ("assamese", "মোবাইল নম্বৰ 69886799099 ব্যৱহাৰ",
     "মোবাইল নম্বৰ ছয় ন আঠ আঠ, ছয় সাত ন ন, শূন্য ন ন ব্যৱহাৰ"),  # 10+ digits, not round: an ID or phone
    ("hindi", "150000000 लोग", "पंद्रह करोड़ लोग"),
    ("english", "7000000000 records", "seven billion records"),
]


@pytest.mark.parametrize("lang,text,expected", FROM_COMPARISON_2)
def test_from_comparison_2(lang, text, expected):
    assert normalize(text, lang) == expected
