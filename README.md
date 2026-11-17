# OpenArcane

Open speech models for Indian languages.

| Model | What it does | Weights |
|---|---|---|
| Volt-TTS | Text-to-speech for 25 Indian languages, with built-in voices and voice cloning | [openarcane/Volt-TTS](https://huggingface.co/openarcane/Volt-TTS) |
| OpenArcane ASR (preview) | Speech recognition for Indian languages | [openarcane/openarcane-asr-0.6b-preview](https://huggingface.co/openarcane/openarcane-asr-0.6b-preview) |

This repository holds the `openarcane` Python package: the text normaliser made for Volt-TTS. It turns written
text into text a TTS model can read aloud. Numbers, money, dates, times, phone numbers and OTPs, units, maths and
web addresses become words in the chosen language. Everything else is copied through unchanged, including
markdown and spacing.

## Install

```bash
pip install "git+https://github.com/openarcane-ai/openarcane"
```

Python 3.10 or newer. Standard library only: no dependencies and no GPU.

## Usage

```python
from openarcane import normalize

normalize("ಬಿಲ್ ₹1,250.50", "kannada")
# ಬಿಲ್ ಸಾವಿರದ ಇನ್ನೂರ ಐವತ್ತು ರೂಪಾಯಿ ಐವತ್ತು ಪೈಸೆ

normalize("OTP 482913, 15/08/2025 को 7:30 PM", "hindi")
# OTP चार आठ दो, नौ एक तीन, पंद्रह अगस्त दो हजार पच्चीस को शाम सात बजकर तीस मिनट

normalize("2 + 3 = 5", "tamil")
# இரண்டு கூட்டல் மூன்று சமம் ஐந்து
```

From the command line:

```bash
python -m openarcane.text -l kannada "ಬಿಲ್ ₹1,250.50"
```

## With Volt-TTS

Normalise the text, then pass it to Volt-TTS. The full setup, with the built-in voices and voice cloning, is in
the [model card's Quickstart](https://huggingface.co/openarcane/Volt-TTS#quickstart).

```python
from openarcane import normalize

# tts and speaker() are set up in the model card's Quickstart
text = normalize("ನಿಮ್ಮ ಬಿಲ್ ₹2,250.50 ಆಗಿದೆ", "kannada")
wavs, sr = tts.generate_voice_clone(text=text, language="kannada", voice_clone_prompt=speaker("arjun"))
```

## Details

- **Languages:** Assamese, Bengali, Bhojpuri, Bodo, Chhattisgarhi, Dogri, English, Gujarati, Hindi, Kannada,
  Kashmiri, Konkani, Magahi, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali,
  Sindhi, Tamil, Telugu and Urdu. Use the same names as Volt-TTS's `language=`.
- **No dependencies:** standard library only, no network calls and no state between calls.
- **Safe by default:** if it fails on some input, it logs the error and returns the text unchanged.
- **Review status:** a review set of Kannada and Hindi outputs was approved by a native speaker. The other
  languages are a preview: their words come from Unicode CLDR and the Volt-TTS training text, but no native
  speaker has checked them yet.

Per-language coverage and known gaps are in [REPORT.md](docs/text/REPORT.md). The design is in
[DESIGN.md](docs/text/DESIGN.md).

## Tests

```bash
uv run --no-project --with pytest pytest -q tests
```

## License

Apache-2.0, see [LICENSE](LICENSE). The normaliser includes number and word data derived from Unicode CLDR,
which is under the Unicode License v3; see [NOTICE](NOTICE).
