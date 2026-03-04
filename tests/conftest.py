from __future__ import annotations

import sys
from pathlib import Path

# Adds the project root to sys.path so that pytest can find the `okavango` package
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))