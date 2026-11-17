"""Text normaliser for Volt-TTS: turns written text into speakable text in 25 Indian languages and English.

    from openarcane.text import normalize
    normalize("₹1,250.50 ಪಾವತಿಸಿ", "kannada")

Standard library only: no dependencies, no network calls.
"""
from .api import ALIASES, LANGUAGES, normalize

__all__ = ["normalize", "LANGUAGES", "ALIASES"]
