"""normalize() falls back to the original text when the engine errors (strict=False), and raises in strict mode."""
import pytest

from openarcane.text import api, normalize


def test_engine_error_returns_text_unchanged(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("synthetic engine failure")
    monkeypatch.setattr(api, "_normalize", boom)
    text = "ನಿಮ್ಮ OTP 482913."
    assert normalize(text, "kannada", strict=False) == text
    with pytest.raises(RuntimeError):
        normalize(text, "kannada", strict=True)


def test_unknown_language_still_raises():
    with pytest.raises(Exception):
        normalize("5", "klingon", strict=False)


def test_tests_run_strict():
    assert api.STRICT
