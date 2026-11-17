import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repository root, so `import openarcane` works

os.environ["OPENARCANE_TEXT_STRICT"] = "1"  # errors must raise in tests, not fall back
