#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
MATPLOTLIB_CONFIG_ROOT = REPO_ROOT / ".matplotlib"

MATPLOTLIB_CONFIG_ROOT.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CONFIG_ROOT))

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gh_reliability.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
