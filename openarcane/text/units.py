"""Latin unit tokens (case-sensitive) -> canonical unit key. Only matched right after a number."""

UNIT_ALIASES = {
    # length
    "km": "km", "kms": "km", "Km": "km", "KM": "km", "kilometre": "km", "kilometres": "km", "kilometer": "km",
    "kilometers": "km", "m": "m", "mtr": "m", "mtrs": "m", "metre": "m", "metres": "m", "meter": "m", "meters": "m",
    "cm": "cm", "cms": "cm", "mm": "mm", "µm": "um", "μm": "um", "nm": "nm", "ft": "ft", "feet": "ft", "foot": "ft",
    "in.": "inch", "inch": "inch", "inches": "inch", "mi": "mile", "mile": "mile", "miles": "mile",
    "yd": "yard", "yards": "yard",
    # area / volume
    "sq ft": "sqft", "sq. ft.": "sqft", "sq.ft.": "sqft", "sq. ft": "sqft", "sq.ft": "sqft", "sqft": "sqft",
    "ft²": "sqft", "sq m": "sqm", "sq. m.": "sqm", "m²": "sqm", "m2": "sqm", "sqm": "sqm", "km²": "sqkm",
    "sq km": "sqkm", "km2": "sqkm", "cm²": "sqcm", "m³": "cum", "cm³": "cucm", "cc": "cc",
    "acre": "acre", "acres": "acre", "ha": "hectare", "hectare": "hectare", "hectares": "hectare",
    # mass
    "kg": "kg", "kgs": "kg", "Kg": "kg", "KG": "kg", "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "mg": "mg", "µg": "ug", "mcg": "ug", "t": "tonne", "tonne": "tonne", "tonnes": "tonne", "ton": "ton",
    "tons": "ton", "quintal": "quintal", "qtl": "quintal", "lb": "lb", "lbs": "lb", "oz": "oz",
    # volume
    "l": "l", "L": "l", "ltr": "l", "ltrs": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
    "ml": "ml", "mL": "ml", "ML": "ml", "kl": "kl", "kL": "kl", "dL": "dl", "dl": "dl",
    # temperature / angle
    "°C": "degC", "° C": "degC", "℃": "degC", "°F": "degF", "° F": "degF", "℉": "degF", "°": "deg", "K": "kelvin",
    # speed
    "km/h": "kmph", "km/hr": "kmph", "kmph": "kmph", "kph": "kmph", "kmh": "kmph", "mph": "mph", "m/s": "mps",
    "km/l": "kmpl", "kmpl": "kmpl",
    # data / frequency / electrical
    "KB": "KB", "kB": "KB", "MB": "MB", "GB": "GB", "TB": "TB", "PB": "PB",
    # bits are case-sensitive: Mb = megabit, MB = megabyte
    "Kb": "kbit", "kbit": "kbit", "Mb": "Mbit", "Mbit": "Mbit", "Gb": "Gbit", "Gbit": "Gbit",
    "Kbps": "kbit/sec", "kbps": "kbit/sec", "Mbps": "Mbit/sec", "Gbps": "Gbit/sec", "MBps": "MB/sec", "Hz": "Hz", "kHz": "kHz", "MHz": "MHz", "GHz": "GHz",
    "W": "W", "kW": "kW", "MW": "MW", "GW": "GW", "kWh": "kWh", "KWh": "kWh", "Wh": "Wh", "V": "V", "kV": "kV",
    "mA": "mA", "mAh": "mAh", "A": "ampere", "hp": "hp", "HP": "hp", "bhp": "bhp", "rpm": "rpm", "dB": "dB",
    "cal": "cal", "kcal": "kcal", "Kcal": "kcal", "J": "joule", "kJ": "kJ", "N": "newton", "Pa": "pascal",
    "kPa": "kPa", "psi": "psi", "MP": "megapixel",
    # time
    "ms": "ms", "s": "sec", "sec": "sec", "secs": "sec", "second": "sec", "seconds": "sec",
    "min": "min", "mins": "min", "minute": "min", "minutes": "min", "h": "hr", "hr": "hr", "hrs": "hr",
    "hour": "hr", "hours": "hr", "yr": "year", "yrs": "year", "years": "year",
}
# Aliases too ambiguous in running text unless directly attached to the digits (5s, 3h, 2A).
TIGHT_ONLY = {"s", "h", "t", "A", "N", "J", "K", "in.", "ha", "cc", "MP", "mi", "yd"}
# Spelled-out English words ("hours", "grams") are only rewritten for English; inside Indic text the
# writer chose an English word and it is left as written.
ABBREVIATIONS = {"kmph", "kmpl", "kbps", "kbit", "mtrs", "ltrs", "secs", "mins", "kcal", "sqft", "hrs", "kgs", "gms", "cms",
                 "kms", "qtl", "bhp", "tonne"}
ENGLISH_ONLY = ({a for a in UNIT_ALIASES if a.isalpha() and a.islower() and len(a) >= 4} - ABBREVIATIONS) \
    | {"feet", "foot", "inch"}
