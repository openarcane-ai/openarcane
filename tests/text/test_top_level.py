"""The public surface: `from openarcane import normalize`, argument errors and the command line."""
import subprocess
import sys
from pathlib import Path

import pytest

import openarcane
from openarcane import LANGUAGES, normalize

ROOT = str(Path(__file__).resolve().parents[2])


def run(*args, stdin=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, input=stdin, cwd=ROOT)


def test_top_level_normalize_is_the_text_normaliser():
    assert normalize is openarcane.text.normalize
    assert normalize("₹2,250.50", "kannada") == "ಎರಡು ಸಾವಿರದ ಇನ್ನೂರ ಐವತ್ತು ರೂಪಾಯಿ ಐವತ್ತು ಪೈಸೆ"


def test_languages():
    assert len(LANGUAGES) == 26
    assert "kannada" in LANGUAGES and "english" in LANGUAGES


def test_import_loads_no_heavy_modules():
    r = run("-c", "import sys, openarcane; openarcane.normalize('₹5', 'hindi'); "
                  "print(sorted({'torch', 'numpy', 'transformers'} & set(sys.modules)))")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "[]"


@pytest.mark.parametrize("text,language,message", [
    (5, "hindi", "text must be a string, got int"),
    (None, "hindi", "text must be a string, got NoneType"),
    ("₹5", 5, "language must be a string, got int"),
])
def test_argument_types(text, language, message):
    with pytest.raises(TypeError, match=message):
        normalize(text, language)


def test_unknown_language_raises():
    with pytest.raises(ValueError, match="unknown language 'klingon'; known: assamese"):
        normalize("₹5", "klingon")


def test_cli_argument_and_stdin():
    assert run("-m", "openarcane.text", "-l", "kn", "₹2,250.50").stdout == "ಎರಡು ಸಾವಿರದ ಇನ್ನೂರ ಐವತ್ತು ರೂಪಾಯಿ ಐವತ್ತು ಪೈಸೆ\n"
    assert run("-m", "openarcane.text", "-l", "hindi", stdin="₹5\n2 + 3 = 5\n").stdout == "पाँच रुपये\nदो प्लस तीन बराबर पाँच\n"


def test_cli_unknown_language_is_a_usage_error():
    r = run("-m", "openarcane.text", "-l", "klingon", "5")
    assert r.returncode == 2
    assert r.stdout == ""
    assert "Traceback" not in r.stderr
    assert r.stderr.startswith("usage: python -m openarcane.text")
    assert "error: unknown language 'klingon'" in r.stderr
