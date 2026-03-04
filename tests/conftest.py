from __future__ import annotations

import sys
from pathlib import Path

# adiciona a raiz do projeto ao sys.path para pytest encontrar o package `okavango`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))