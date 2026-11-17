"""OpenArcane text normaliser: turns written text into text a TTS model can read aloud, in 25 Indian
languages and English.

    from openarcane import normalize
    normalize("₹2,250.50", "kannada")   # ಎರಡು ಸಾವಿರದ ಇನ್ನೂರ ಐವತ್ತು ರೂಪಾಯಿ ಐವತ್ತು ಪೈಸೆ

Standard library only: no dependencies, no network calls.
"""
from . import text
from .text import LANGUAGES, normalize

__version__ = "0.1.0"
__all__ = ["__version__", "normalize", "LANGUAGES", "text"]
