"""DEV TOOL (not imported by the package). Extract month and unit names from Unicode CLDR via ICU.

Needs PyICU built against ICU >= 78 (CLDR 48). Writes openarcane/text/data/cldr_lexicon.json:
  {language: {"locale": .., "months": [12], "units": {key: name}}}
Unit names are taken from the count-1 and count-5 long forms ("1 kilometre", "5 kilometres") with the number
stripped, stored as [one, other]; langs/__init__.py decides per language whether the plural is used (Telugu,
English) or the invariant noun (Kannada ಕಿಲೋಮೀಟರ್, not ಕಿಲೋಮೀಟರ್‌ಗಳು). Units whose
long form falls back to the root locale's Latin symbol ("5 km") are skipped.

Usage: <python-with-pyicu> -I tools/text/extract_cldr_lexicon.py
"""
import json
import os
import re

import icu

LOCALES = {
    "assamese": "as", "bengali": "bn", "bhojpuri": "bho", "bodo": "brx", "dogri": "doi", "gujarati": "gu",
    "hindi": "hi", "kannada": "kn", "konkani": "kok", "kashmiri": "ks_Arab", "maithili": "mai",
    "malayalam": "ml", "marathi": "mr", "nepali": "ne", "odia": "or", "punjabi": "pa", "sanskrit": "sa",
    "santali": "sat_Olck", "sindhi": "sd_Deva", "tamil": "ta", "telugu": "te", "urdu": "ur", "english": "en_IN",
    "manipuri_bengali": "mni_Beng",
}

U = icu.MeasureUnit
UNITS = {
    "km": U.createKilometer, "m": U.createMeter, "cm": U.createCentimeter, "mm": U.createMillimeter,
    "um": U.createMicrometer, "nm": U.createNanometer, "ft": U.createFoot, "inch": U.createInch,
    "mile": U.createMile, "yard": U.createYard, "sqft": U.createSquareFoot, "sqm": U.createSquareMeter,
    "sqkm": U.createSquareKilometer, "sqcm": U.createSquareCentimeter, "cum": U.createCubicMeter,
    "cucm": U.createCubicCentimeter, "acre": U.createAcre, "hectare": U.createHectare, "kg": U.createKilogram,
    "g": U.createGram, "mg": U.createMilligram, "ug": U.createMicrogram, "tonne": U.createMetricTon,
    "lb": U.createPound, "oz": U.createOunce, "l": U.createLiter, "ml": U.createMilliliter,
    "degC": U.createCelsius, "degF": U.createFahrenheit, "deg": U.createDegree, "kelvin": U.createKelvin,
    "kmph": U.createKilometerPerHour, "mph": U.createMilePerHour, "mps": U.createMeterPerSecond,
    "KB": U.createKilobyte, "MB": U.createMegabyte, "GB": U.createGigabyte,
    "TB": U.createTerabyte, "PB": U.createPetabyte, "kbit": U.createKilobit, "Mbit": U.createMegabit,
    "Gbit": U.createGigabit, "Hz": U.createHertz, "kHz": U.createKilohertz, "MHz": U.createMegahertz,
    "GHz": U.createGigahertz, "W": U.createWatt, "kW": U.createKilowatt, "MW": U.createMegawatt,
    "GW": U.createGigawatt, "kWh": U.createKilowattHour, "V": U.createVolt, "mA": U.createMilliampere,
    "ampere": U.createAmpere, "hp": U.createHorsepower, "cal": U.createCalorie, "kcal": U.createKilocalorie,
    "joule": U.createJoule, "kJ": U.createKilojoule, "newton": U.createNewton, "pascal": U.createPascal,
    "kPa": U.createKilopascal, "psi": U.createPoundPerSquareInch, "megapixel": U.createMegapixel,
    "ms": U.createMillisecond, "sec": U.createSecond, "min": U.createMinute, "hr": U.createHour,
    "year": U.createYear,
}
UNITS = {k: v for k, v in UNITS.items()}
NUM_RX = re.compile(r"[\d०-९০-৯٠-٩۰-۹᱐-᱙.,]+")


def unit_name(loc, key, count):
    if UNITS[key] is None:
        return None
    mf = icu.MeasureFormat(loc, icu.UMeasureFormatWidth.WIDE)
    s = mf.formatMeasures([icu.Measure(count, UNITS[key]())], icu.FieldPosition(0))
    name = NUM_RX.sub("", s).replace(" ", " ").replace(" ", " ").strip()
    if not name or re.fullmatch(r"[A-Za-z°/²³µ ]+", name) and not str(loc).startswith("en"):
        return None
    return name


def main():
    out = {}
    for lang, loc_id in LOCALES.items():
        loc = icu.Locale(loc_id)
        months = list(icu.DateFormatSymbols(loc).getMonths())
        units = {}
        for key in UNITS:
            one = unit_name(loc, key, 1)
            if one is None:
                continue
            units[key] = [one, unit_name(loc, key, 5) or one]
        out[lang] = {"locale": loc_id, "months": months, "units": units}
    meta = {"source": "Unicode CLDR via ICU %s (CLDR 48)" % icu.ICU_VERSION,
            "license": "Unicode License v3 (https://www.unicode.org/license.txt)"}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "openarcane", "text", "data", "cldr_lexicon.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"_meta": meta, **out}, fh, ensure_ascii=False, indent=1, sort_keys=True)
    for lang, d in out.items():
        print(lang, len(d["units"]), d["months"][:2])


if __name__ == "__main__":
    main()
