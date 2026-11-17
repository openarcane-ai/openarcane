"""Language registry. Each module exposes `make()` returning a configured Lang instance."""
from __future__ import annotations

import importlib
import json
import os
import re

from .base import Lang

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cldr_lexicon.json")
with open(_DATA, encoding="utf-8") as _fh:
    CLDR = json.load(_fh)

# TTS language name -> (module, ISO 639 code)
LANGUAGE_MODULES = {
    "english": ("english", "en"), "hindi": ("hindi", "hi"), "kannada": ("kannada", "kn"),
    "telugu": ("telugu", "te"), "tamil": ("tamil", "ta"), "malayalam": ("malayalam", "ml"),
    "marathi": ("indo_aryan", "mr"), "bengali": ("indo_aryan", "bn"), "assamese": ("indo_aryan", "as"),
    "gujarati": ("indo_aryan", "gu"), "punjabi": ("indo_aryan", "pa"), "odia": ("indo_aryan", "or"),
    "nepali": ("indo_aryan", "ne"), "urdu": ("indo_aryan", "ur"), "kashmiri": ("indo_aryan", "ks"),
    "sindhi": ("indo_aryan", "sd"), "konkani": ("indo_aryan", "gom"), "maithili": ("indo_aryan", "mai"),
    "dogri": ("indo_aryan", "doi"), "bhojpuri": ("indo_aryan", "bho"), "magahi": ("indo_aryan", "mag"),
    "chhattisgarhi": ("indo_aryan", "hne"), "sanskrit": ("sanskrit", "sa"), "bodo": ("tibeto_burman", "brx"),
    "manipuri": ("tibeto_burman", "mni"), "santali": ("santali", "sat"),
}
ALIASES = {code: name for name, (_, code) in LANGUAGE_MODULES.items()}
ALIASES.update({"kok": "konkani", "or": "odia", "ory": "odia", "pan": "punjabi", "mni_mtei": "manipuri",
                "sat_olck": "santali", "sd_deva": "sindhi", "ks_arab": "kashmiri", "en_in": "english",
                "oriya": "odia", "bangla": "bengali", "meitei": "manipuri", "meetei": "manipuri"})

_ZW = re.compile(r"^[​-‍\s]+|[​-‍\s]+$")


# languages whose unit nouns take a plural after numbers other than 1 (others use the invariant noun)
PLURAL_UNITS = {"english", "telugu"}


def _clean(x: str) -> str:
    return re.sub(r"\s{2,}", " ", _ZW.sub("", x))


def cldr_layer(name: str) -> dict:
    c = CLDR.get(name)
    if not c:
        return {}
    out = {"months": list(c["months"])}
    for k, v in c["units"].items():
        one, other = (v if isinstance(v, list) else [v, v])
        if "/" in one or "/" in other:  # e.g. ta/ml "கி.மீ/மணிநேரம்"-style per-unit forms: hand lexicon decides
            continue
        out[f"u_{k}"] = (_clean(one), _clean(other)) if name in PLURAL_UNITS else _clean(one)
    return out


_CACHE: dict[str, Lang] = {}


def resolve(language: str) -> str:
    key = language.strip().lower().replace("-", "_")
    if key in LANGUAGE_MODULES:
        return key
    if key in ALIASES:
        return ALIASES[key]
    raise ValueError(f"unknown language {language!r}; known: {', '.join(sorted(LANGUAGE_MODULES))}")


def get(language: str) -> Lang:
    name = resolve(language)
    if name not in _CACHE:
        mod = importlib.import_module(f".{LANGUAGE_MODULES[name][0]}", __name__)
        lang = mod.make(name)
        lang.registry = _REGISTRY_VIEW
        _CACHE[name] = lang
        for fb in lang.fallback:  # make sure fallback languages are loaded too
            get(fb)
    return _CACHE[name]


class _RegistryView(dict):
    def get(self, name, default=None):  # noqa: A003
        try:
            return get(name)
        except ValueError:
            return default


_REGISTRY_VIEW = _RegistryView()
