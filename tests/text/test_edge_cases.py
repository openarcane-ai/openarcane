"""Edge cases: maths versus ranges, units, clock words and case endings.
PINNED holds the current output of items left as REVIEW_NEEDED, so a change to them is deliberate."""
import pytest

from openarcane.text import normalize

CASES = [
    # a mixed number whose whole part has no word: read as a decimal, never crash
    ("manipuri", "41½", "ꯃꯔꯤ ꯑꯃ ꯄꯣꯏꯟꯠ ꯃꯉꯥ"),
    ("manipuri", "꯴꯱½", "ꯃꯔꯤ ꯑꯃ ꯄꯣꯏꯟꯠ ꯃꯉꯥ"),
    ("manipuri", "2¼", "ꯑꯅꯤ ꯄꯣꯏꯟꯠ ꯑꯅꯤ ꯃꯉꯥ"),
    ("manipuri", "2½", "ꯑꯅꯤꯒ ꯃꯈꯥꯏ"),
    ("santali", "2½", "ᱵᱟᱨ ᱯᱚᱭᱮᱱᱴ ᱢᱚᱲᱮ"),
    # rate templates after structured numbers
    ("telugu", "2½ km/h", "గంటకు రెండున్నర కిలోమీటర్లు"),
    ("tamil", "2½ km/h", "மணிக்கு இரண்டரை கிலோமீட்டர்"),
    ("malayalam", "2½ km/h", "മണിക്കൂറിൽ രണ്ടര കിലോമീറ്റർ"),
    # typed endpoints on a maths line are a subtraction
    ("english", "$5-$3=$2", "five dollars minus three dollars equals two dollars"),
    ("english", "₹5–₹10", "five rupees to ten rupees"),
    # a hyphen after a written native quantity on a maths line
    ("hindi", "5 किलो-3 किलो=2 किलो", "पाँच किलो माइनस तीन किलो बराबर दो किलो"),
    ("kannada", "ಕೋವಿಡ್-19 ಪ್ರಕರಣ", "ಕೋವಿಡ್-ಹತ್ತೊಂಬತ್ತು ಪ್ರಕರಣ"),
    # a decimal's last digit keeps its digit name in rates and money
    ("telugu", "2.1 km/h", "గంటకు రెండు పాయింట్ ఒకటి కిలోమీటర్లు"),
    ("tamil", "2.1km/h", "மணிக்கு இரண்டு புள்ளி ஒன்று கிலோமீட்டர்"),
    ("telugu", "₹2.111", "రెండు పాయింట్ ఒకటి ఒకటి ఒకటి రూపాయలు"),
    ("tamil", "₹2.111", "இரண்டு புள்ளி ஒன்று ஒன்று ஒன்று ரூபாய்"),
    # singular rate
    ("telugu", "1 km/h", "గంటకు ఒక కిలోమీటరు"),
    ("telugu", "౧ km/h", "గంటకు ఒక కిలోమీటరు"),
    ("telugu", "60 km/h", "గంటకు అరవై కిలోమీటర్లు"),
    # a native case ending after a structured quantity's unit
    ("kannada", "1½kgಗೆ", "ಒಂದೂವರೆ ಕಿಲೋಗ್ರಾಂಗೆ"),
    ("malayalam", "2¼kgക്ക്", "രണ്ടേകാൽ കിലോഗ്രാമിന്"),
    # Malayalam -i noun + ക്ക്
    ("malayalam", "7 PMക്ക്", "രാത്രി ഏഴ് മണിക്ക്"),
    ("malayalam", "7:00ക്ക്", "ഏഴ് മണിക്ക്"),
    ("malayalam", "5ക്ക്", "അഞ്ചിന്"),
    # the clock classifier after a clock word that already ends the time
    ("odia", "୧:୦୦ଟାରେ ଆସନ୍ତୁ।", "ଗୋଟାଏରେ ଆସନ୍ତୁ।"),
    ("odia", "୧୦:୩୦ଟାରେ ଆସନ୍ତୁ।", "ଦଶଟା ତିରିଶ ମିନିଟରେ ଆସନ୍ତୁ।"),
    ("bengali", "৫:৩০টাতে আসুন।", "পাঁচটা বেজে ত্রিশ মিনিটে আসুন।"),
    # Urdu ویں before a common feminine noun (unverified)
    ("urdu", "2ویں صدی میں", "دوسری صدی میں"),
    ("urdu", "2ویں اجلاس میں", "دوسرے اجلاس میں"),
    # Gujarati spaced postposition takes the oblique (unverified)
    ("gujarati", "₹૧ માં મળે છે.", "એક રૂપિયા માં મળે છે."),
    # chained typed subtraction
    ("english", "$5-$3-$1=$1", "five dollars minus three dollars minus one dollar equals one dollar"),
    # a hyphen inside a name is not minus, even on a line with maths
    ("hindi", "कुल 5 कोविड-19 मामले (2+3=5)", "कुल पाँच कोविड-उन्नीस मामले (दो प्लस तीन बराबर पाँच)"),
    # a native unit of more than one word, and a fallback lexicon's quantity word
    ("hindi", "5 वर्ग मीटर-3 वर्ग मीटर=2 वर्ग मीटर", "पाँच वर्ग मीटर माइनस तीन वर्ग मीटर बराबर दो वर्ग मीटर"),
    ("bhojpuri", "5 किलो-3 किलो=2 किलो", "पाँच किलो माइनस तीन किलो बराबर दू किलो"),
    # decimal and exponent digits keep their digit names before a scale or rate
    ("tamil", "₹2.111 lakh", "இரண்டு புள்ளி ஒன்று ஒன்று ஒன்று லட்சம் ரூபாய்"),
    ("tamil", "2e1 km/h", "மணிக்கு இரண்டு பெருக்கல் பத்து பவர் ஒன்று கிலோமீட்டர்"),
    # the clock classifier after seconds
    ("bengali", "৫:৩০:১৫টাতে আসুন।", "পাঁচটা বেজে ত্রিশ মিনিট পনেরো সেকেন্ডে আসুন।"),
    ("odia", "୧୦:୩୦:୧୫ଟାରେ ଆସନ୍ତୁ।", "ଦଶଟା ତିରିଶ ମିନିଟ ପନ୍ଦର ସେକେଣ୍ଡରେ ଆସନ୍ତୁ।"),
    # Urdu feminine noun followed by punctuation (unverified)
    ("urdu", "2ویں صدی: تعارف", "دوسری صدی: تعارف"),
    # Gujarati માંથી takes the oblique (unverified)
    ("gujarati", "₹1 માંથી મળે છે.", "એક રૂપિયા માંથી મળે છે."),
    # typed endpoints are a subtraction only when the sum is local
    ("english", "Pay $5-$10 per day + meals", "Pay five dollars to ten dollars per day plus meals"),
    ("english", "Budget $5-$10 per day; 2+3=5", "Budget five dollars to ten dollars per day; two plus three equals five"),
    ("english", "$5-$3 = $2", "five dollars minus three dollars equals two dollars"),
    ("english", "x=$5-$3", "x equals five dollars minus three dollars"),
    # a space after the hyphen
    ("hindi", "5 किलो- 3 किलो=2 किलो", "पाँच किलो माइनस तीन किलो बराबर दो किलो"),
    ("hindi", "5 वर्ग मीटर- 3 वर्ग मीटर=2 वर्ग मीटर", "पाँच वर्ग मीटर माइनस तीन वर्ग मीटर बराबर दो वर्ग मीटर"),
    ("hindi", "कुल 5 कोविड- 19 मामले (2+3=5)", "कुल पाँच कोविड- उन्नीस मामले (दो प्लस तीन बराबर पाँच)"),
    # Urdu question mark after the noun (unverified)
    ("urdu", "2ویں صدی؟", "دوسری صدی؟"),
    ("urdu", "3ویں صدی؟ تعارف", "تیسری صدی؟ تعارف"),
    ("urdu", "2ویں اجلاس؟", "دوسرے اجلاس؟"),
    # spaced Gujarati ના may be the negator: direct form kept (unverified)
    ("gujarati", "₹1 ના આપો.", "એક રૂપિયો ના આપો."),
    # a sum continues with + or a closing bracket; an assignment may be spaced
    ("english", "Total: $10-$4+$2=$8", "Total: ten dollars minus four dollars plus two dollars equals eight dollars"),
    ("english", "($10-$4)=$6", "(ten dollars minus four dollars) equals six dollars"),
    ("english", "x =    $5-$3", "x equals    five dollars minus three dollars"),
    ("english", "($5-$10 per day)", "(five dollars to ten dollars per day)"),
    # native quantities: minus only for a local sum, never from maths elsewhere in the clause
    ("hindi", "5 किलो- 10 किलो प्रति दिन; 2+3=5", "पाँच किलो- दस किलो प्रति दिन; दो प्लस तीन बराबर पाँच"),
    ("hindi", "5 किलो-3 किलो-1 किलो=1 किलो", "पाँच किलो माइनस तीन किलो माइनस एक किलो बराबर एक किलो"),
    ("hindi", "x = 5 किलो-3 किलो", "x बराबर पाँच किलो माइनस तीन किलो"),
    ("hindi", "(5 किलो-3 किलो)=2 किलो", "(पाँच किलो माइनस तीन किलो) बराबर दो किलो"),
    # an = after a label is not a sum
    ("english", "Daily budget = $5-$10 per day", "Daily budget equals five dollars to ten dollars per day"),
    ("english", "Opening hours = 10:30-11:30", "Opening hours equals ten thirty to eleven thirty"),
    ("hindi", "वजन = 5 किलो- 10 किलो प्रति दिन", "वजन बराबर पाँच किलो- दस किलो प्रति दिन"),
    # a native chain after an assignment
    ("hindi", "x = 5 किलो-3 किलो-1 किलो", "x बराबर पाँच किलो माइनस तीन किलो माइनस एक किलो"),
    ("hindi", "x = (5 किलो-3 किलो-1 किलो)", "x बराबर (पाँच किलो माइनस तीन किलो माइनस एक किलो)"),
    # nested and square brackets
    ("english", "(($10-$4))=$6", "((ten dollars minus four dollars)) equals six dollars"),
    ("english", "[$10-$4]=$6", "[ten dollars minus four dollars] equals six dollars"),
    ("hindi", "[5 किलो-3 किलो]=2 किलो", "[पाँच किलो माइनस तीन किलो] बराबर दो किलो"),
    # a signed operand or one-letter variable after the operator
    ("english", "$10-$4 + -$2 = $4", "ten dollars minus four dollars plus minus two dollars equals four dollars"),
    ("hindi", "5 किलो-3 किलो + x = 2 किलो", "पाँच किलो माइनस तीन किलो प्लस x बराबर दो किलो"),
    # any spacing after the hyphen is kept
    ("hindi", "5 किलो-  3 किलो=2 किलो", "पाँच किलो माइनस  तीन किलो बराबर दो किलो"),
    # a bracketed label before = is not a sum; a bracketed sum is
    ("english", "Daily budget (USD) = $5-$10", "Daily budget (USD) equals five dollars to ten dollars"),
    ("hindi", "वजन (kg) = 5 किलो-10 किलो", "वजन (kg) बराबर पाँच किलो-दस किलो"),
    ("english", "(2+3) = $5-$0", "(two plus three) equals five dollars minus zero dollars"),
    # a range inside one money, percent or unit span uses the local test
    ("english", "Set aside $5-10 per day + meals", "Set aside five to ten dollars per day plus meals"),
    ("hindi", "दैनिक बजट = ₹500-1000 प्रति दिन", "दैनिक बजट बराबर पाँच सौ से एक हजार रुपये प्रति दिन"),
    ("english", "x = ₹500-100", "x equals five hundred minus one hundred rupees"),
    # percent and unit endpoints
    ("english", "Expected return: 5%-10% per year.", "Expected return: five percent to ten percent per year."),
    ("english", "Parcel weight: 5 kg-10 kg.", "Parcel weight: five kilograms to ten kilograms."),
    ("english", "5 kg-3 kg=2 kg", "five kilograms minus three kilograms equals two kilograms"),
    ("english", "5%-3%=2%", "five percent minus three percent equals two percent"),
    # a spaced minus after the chain
    ("english", "$10-$4 - x = $3", "ten dollars minus four dollars minus x equals three dollars"),
    ("hindi", "5 किलो-3 किलो - x = 2 किलो", "पाँच किलो माइनस तीन किलो माइनस x बराबर दो किलो"),
    # a Latin unit after a native quantity
    ("hindi", "5 लीटर-500 ml=4.5 लीटर", "पाँच लीटर माइनस पाँच सौ मिलीलीटर बराबर चार दशमलव पाँच लीटर"),
    ("kannada", "5 ಕಿಲೋಗ್ರಾಂ-3 kg=2 ಕಿಲೋಗ್ರಾಂ", "ಐದು ಕಿಲೋಗ್ರಾಂ ಮೈನಸ್ ಮೂರು ಕಿಲೋಗ್ರಾಂ ಈಕ್ವಲ್ ಟು ಎರಡು ಕಿಲೋಗ್ರಾಂ"),
    # two clock intervals; a clock difference needs =
    ("english", "Opening hours: 10:30-11:30 + 14:30-15:30", "Opening hours: ten thirty to eleven thirty plus fourteen thirty to fifteen thirty"),
    ("english", "11:30-10:30=1:00", "eleven thirty minus ten thirty equals one o'clock"),
    # spaces around a typed dash
    ("english", "$10-  $4=$6", "ten dollars minus four dollars equals six dollars"),
    # spaced nested brackets
    ("english", "( ($10-$4) ) = $6", "( (ten dollars minus four dollars) ) equals six dollars"),
    # a bracketed year in a label is not a sum
    ("english", "Interest rate (2026) = 5%-10%.", "Interest rate (two thousand twenty-six) equals five percent to ten percent."),
    ("hindi", "बजट (2026) = ₹500-₹1000।", "बजट (दो हजार छब्बीस) बराबर पाँच सौ रुपये से एक हजार रुपये।"),
    # an operator after the range counts only with an = later in the clause
    ("english", "Delivery costs $5-$10 + $2 handling.", "Delivery costs five dollars to ten dollars plus two dollars handling."),
    # a shared-currency span inside a longer equation
    ("english", "₹1000-200-₹300=₹500", "one thousand minus two hundred rupees minus three hundred rupees equals five hundred rupees"),
    ("bengali", "₹1000-200-₹300=₹500", "এক হাজার বিয়োগ দুশো টাকা বিয়োগ তিনশো টাকা সমান পাঁচশো টাকা"),
    # a compact minus before a bracket on a maths line
    ("english", "Total: $10-($4+$2)=$4", "Total: ten dollars minus (four dollars plus two dollars) equals four dollars"),
    ("english", "5-(2+3)=0", "five minus (two plus three) equals zero"),
    # fraction endpoints with a unit or percent
    ("english", "Add ½ kg-1 kg of flour.", "Add one half kilogram to one kilogram of flour."),
    ("english", "Growth: 1½%-2%.", "Growth: one and one half percent to two percent."),
    # a Latin unit to a written native quantity
    ("hindi", "वजन 5 kg-10 किलो है।", "वजन पाँच किलोग्राम से दस किलो है।"),
    # the first endpoint takes the oblique before से
    ("hindi", "1 hr-2 hr में पहुँचेंगे।", "एक घंटे से दो घंटे में पहुँचेंगे।"),
    ("hindi", "₹1-₹2 में", "एक रुपये से दो रुपये में"),
    # a typed subtraction in a language without a minus word keeps the sign instead of crashing
    ("manipuri", "$10-$4=$6", "ꯗꯣꯂꯔ ꯇꯔꯥ-ꯗꯣꯂꯔ ꯃꯔꯤ=ꯗꯣꯂꯔ ꯇꯔꯨꯛ"),
    ("santali", "$10-$4=$6", "ᱜᱮᱞ ᱰᱚᱞᱟᱨ-ᱯᱩᱱ ᱰᱚᱞᱟᱨ=ᱛᱩᱨᱩᱭ ᱰᱚᱞᱟᱨ"),
    ("manipuri", "10 kg-4 kg=6 kg", "ꯀꯤꯂꯣꯒ꯭ꯔꯥꯝ ꯇꯔꯥ-ꯀꯤꯂꯣꯒ꯭ꯔꯥꯝ ꯃꯔꯤ=ꯀꯤꯂꯣꯒ꯭ꯔꯥꯝ ꯇꯔꯨꯛ"),
    # a bracket before "=" counts as a sum only when it holds arithmetic
    ("english", "Delivery (Mon-Fri) = $5-$10.", "Delivery (Mon-Fri) equals five dollars to ten dollars."),
    ("english", "Delivery (3-5 days) = $5-$10.", "Delivery (three to five days) equals five dollars to ten dollars."),
    ("english", "(10 - 4) = $5-$0", "(ten minus four) equals five dollars minus zero dollars"),
    # a written-out native unit word that starts with a native abbreviation is that unit
    ("tamil", "மாவு ½ kg-1 கிலோகிராம் சேர்க்கவும்.", "மாவு அரை கிலோகிராம் முதல் ஒரு கிலோகிராம் சேர்க்கவும்."),
    ("tamil", "மாவு 1 கிலோகிராம் சேர்க்கவும்.", "மாவு ஒரு கிலோகிராம் சேர்க்கவும்."),
    ("tamil", "2 கிலோமீட்டர்", "இரண்டு கிலோமீட்டர்"),
    ("tamil", "2 கிலோவுக்கு", "இரண்டு கிலோவுக்கு"),
    ("tamil", "2 கிலோ", "இரண்டு கிலோகிராம்"),
    ("malayalam", "1 കിലോഗ്രാം", "ഒരു കിലോഗ്രാം"),
    ("malayalam", "2 കിലോമീറ്റർ", "രണ്ട് കിലോമീറ്റർ"),
    ("malayalam", "2 കിലോയ്ക്ക്", "രണ്ട് കിലോയ്ക്ക്"),
    ("telugu", "1 కిలోగ్రాము", "ఒక కిలోగ్రాము"),
    ("telugu", "2 కిలోమీటర్లు", "రెండు కిలోమీటర్లు"),
    ("telugu", "2 కిలోమీటర్", "రెండు కిలోమీటర్"),
    ("kannada", "2 ಕೆಜಿಗೆ", "ಎರಡು ಕಿಲೋಗ್ರಾಂಗೆ"),
    # vulgar fractions are operands
    ("english", "½+¼=¾", "one half plus one quarter equals three quarters"),
    ("english", "½ kg + ¼ kg = ¾ kg", "one half kilogram plus one quarter kilogram equals three quarters kilogram"),
    ("hindi", "½+¼=¾", "आधा प्लस एक चौथाई बराबर तीन चौथाई"),
    # a compact minus before a bracket after a quantity with a unit, or a variable
    ("english", "Calculate 10 kg-(4 kg+2 kg)=4 kg.",
     "Calculate ten kilograms minus (four kilograms plus two kilograms) equals four kilograms."),
    ("english", "10%-(4%+2%)=4%", "ten percent minus (four percent plus two percent) equals four percent"),
    ("english", "x-(4+2)=4", "x minus (four plus two) equals four"),
    ("english", "Mon-(Fri) 2+2=4", "Mon-(Fri) two plus two equals four"),
    # script full stops end the clause that an "=" must be in
    ("urdu", "قیمت $5-$10 + $2 فیس۔ رعایت: $10-$2=$8",
     "قیمت پانچ ڈالر سے دس ڈالر جمع دو ڈالر فیس۔ رعایت: دس ڈالر منفی دو ڈالر برابر آٹھ ڈالر"),
    # a fraction with a unit takes the oblique, and आधा agrees
    ("hindi", "½ hr-1 hr में पहुँचेंगे।", "आधे घंटे से एक घंटे में पहुँचेंगे।"),
    ("hindi", "½ hr में", "आधे घंटे में"),
    ("hindi", "½ hr", "आधा घंटा"),
    ("urdu", "½ hr میں", "آدھے گھنٹے میں"),
    # a native-quantity endpoint uses the before-noun form of the number
    ("telugu", "పాలు ½ l-1 లీటరు పోయండి.", "పాలు అర లీటరు నుంచి ఒక లీటరు పోయండి."),
    # a range template's closing word is not doubled when the writer wrote it
    ("malayalam", "താപനില -5°C–-2°C വരെ ആയിരിക്കും.",
     "താപനില മൈനസ് അഞ്ച് ഡിഗ്രി സെൽഷ്യസ് മുതൽ മൈനസ് രണ്ട് ഡിഗ്രി സെൽഷ്യസ് വരെ ആയിരിക്കും."),
    ("malayalam", "5-10 വരെ", "അഞ്ച് മുതൽ പത്ത് വരെ"),
    ("malayalam", "5-10 ദിവസം വരെ", "അഞ്ച് മുതൽ പത്ത് ദിവസം വരെ"),
    ("malayalam", "5-10 ദിവസം", "അഞ്ച് മുതൽ പത്ത് വരെ ദിവസം"),
    ("sanskrit", "5-10 यावत्", "पञ्च आरभ्य दश यावत्"),
    # markdown italics are not multiplication
    ("english", "Add ½ *cup* of sugar.", "Add one half *cup* of sugar."),
    ("english", "Add 2 *cups* of sugar.", "Add two *cups* of sugar."),
    ("english", "Add *2 cups* of sugar.", "Add *two cups* of sugar."),
    ("english", "*Note:* 2*3=6", "*Note:* two times three equals six"),
    ("english", "2 * 3 = 6", "two times three equals six"),
    ("hindi", "2 *कप* चीनी", "दो *कप* चीनी"),
    # script full stops end the maths line too
    ("urdu", "روزانہ 5 - 10 لوگ آتے ہیں۔ حساب: 2+3=5", "روزانہ پانچ سے دس لوگ آتے ہیں۔ حساب: دو جمع تین برابر پانچ"),
    # compact operators between vulgar fractions
    ("english", "½*½=¼", "one half times one half equals one quarter"),
    ("english", "½-¼=¼", "one half minus one quarter equals one quarter"),
    ("english", "½/¼=2", "one half divided by one quarter equals two"),
    ("english", "Use ½/¼ tsp", "Use one half/one quarter tsp"),
    # a bracketed sum may hold fractions and one-letter variables
    ("english", "(½+¼) = 100%-25%.", "(one half plus one quarter) equals one hundred percent minus twenty-five percent."),
    ("english", "(x+y) = $10-$4", "(x plus y) equals ten dollars minus four dollars"),
    # a compact minus before a bracket after a fractional quantity
    ("english", "Calculate ½ kg-(¼ kg)=¼ kg.", "Calculate one half kilogram minus (one quarter kilogram) equals one quarter kilogram."),
    # Unicode subscript/superscript digits in URLs do not crash
    ("english", "See https://en.wikipedia.org/wiki/CO₂.", "See en dot wikipedia dot org slash wiki slash CO ₂."),
    ("english", "See https://x.org/a²b", "See x dot org slash a ² b"),
    # a space before a fraction glyph keeps the mixed number
    ("hindi", "1 ½ kg आटा लें।", "डेढ़ किलोग्राम आटा लें।"),
    ("english", "1 ½ kg flour", "one and one half kilograms flour"),
    ("kannada", "1 ½ kg", "ಒಂದೂವರೆ ಕಿಲೋಗ್ರಾಂ"),
    ("english", "-1 ½ kg", "minus one and one half kilograms"),
    # a stop followed by a closing quote ends the maths line
    ("hindi", "उसने कहा, “रोज 5 - 10 लोग आते हैं।” हिसाब: 2+3=5",
     "उसने कहा, “रोज पाँच से दस लोग आते हैं।” हिसाब: दो प्लस तीन बराबर पाँच"),
    ("english", 'He said, "5 - 10 people come daily." Sum: 2+3=5',
     'He said, "five to ten people come daily." Sum: two plus three equals five'),
    ("urdu", "اس نے کہا، ”روزانہ 5 - 10 لوگ آتے ہیں۔“ حساب: 2+3=5",
     "اس نے کہا، ”روزانہ پانچ سے دس لوگ آتے ہیں۔“ حساب: دو جمع تین برابر پانچ"),
    # two bare fractions joined by a dash are a range; a compact fraction slash or dash needs an "="
    ("english", "Shopping list: ½-¾ cup sugar + 2 eggs.", "Shopping list: one half to three quarters cup sugar plus two eggs."),
    ("english", "½-1½ cups", "one half to one and one half cups"),
    ("english", "Use a ½/¾-inch adapter + 2 washers.", "Use a one half/three quarters-inch adapter plus two washers."),
    ("english", "x = ½/¼", "x equals one half divided by one quarter"),
    ("hindi", "½-¾ कप चीनी", "आधे से तीन चौथाई कप चीनी"),
    ("kannada", "½-¾ ಕಪ್", "ಅರ್ಧದಿಂದ ಮುಕ್ಕಾಲು ಕಪ್"),
    # operators between markdown-wrapped operands; bold delimiters are never multiplication
    ("english", "*2* + *3* = *5*", "*two* plus *three* equals *five*"),
    ("english", "**2** + **3** = **5**", "**two** plus **three** equals **five**"),
    ("english", "**Total** = $5", "**Total** equals five dollars"),
    ("english", "This is **bold** text", "This is **bold** text"),
    # a compact slash before a fraction glyph
    ("english", "2/½=4", "two divided by one half equals four"),
]

# REVIEW_NEEDED items left unchanged for a native checker
PINNED = [
    ("kannada", "15/08/2025ರಂದು ಸಭೆ ಇದೆ.", "ಹದಿನೈದು ಆಗಸ್ಟ್ ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತೈದರಂದು ಸಭೆ ಇದೆ."),
    ("kannada", "2²", "ಎರಡು ವರ್ಗ"),
    ("kannada", "₹15000000", "ಒಂದು ಕೋಟಿಯ ಐವತ್ತು ಲಕ್ಷ ರೂಪಾಯಿ"),
    ("telugu", "15/08/2025న సమావేశం.", "పదిహేను ఆగస్టు రెండు వేల ఇరవై ఐదున సమావేశం."),
    ("malayalam", "15/08/2025ന് യോഗം.", "പതിനഞ്ച് ഓഗസ്റ്റ് രണ്ടായിരത്തി ഇരുപത്തിയഞ്ചിന് യോഗം."),
]


@pytest.mark.parametrize("lang,text,expected", CASES + PINNED)
def test_final(lang, text, expected):
    assert normalize(text, lang) == expected


# text that is not rewritten comes back byte for byte, even when it is not in NFC
@pytest.mark.parametrize("text,lang", [("Café ### x", "english"), ("क़ का", "hindi")])
def test_non_nfc_passthrough(text, lang):
    assert normalize(text, lang) == text


def test_non_nfc_rewritten_neighbour():
    out = normalize("Café 5 kg", "english")
    assert out == "Café five kilograms"


# each occurrence gets back its own spelling
def test_non_nfc_per_occurrence():
    out = normalize("Cafe\u0301 5 kg Caf\u00e9 Cafe\u0301", "english")
    assert out == "Cafe\u0301 five kilograms Caf\u00e9 Cafe\u0301"


# a generated word equal to an untouched token does not take that token's spelling
def test_non_nfc_generated_word():
    out = normalize("8 \u0627\u0653\u0679\u06be \u0622\u0679\u06be", "urdu")
    assert out == "\u0622\u0679\u06be \u0627\u0653\u0679\u06be \u0622\u0679\u06be"


def test_non_nfc_layout():
    assert normalize("Cafe\u0301   ###\n Cafe\u0301 x", "english") == "Cafe\u0301   ###\n Cafe\u0301 x"
