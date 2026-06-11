#!/usr/bin/env python3
"""Thin CLI entry point for book preprocessing.

The pipeline itself lives in src/preprocessing/pipeline.py — this shell exists
only so the server can invoke preprocessing as an isolated subprocess (see
src/routes/books.py), mirroring scripts/generate_chapter.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.preprocessing.pipeline import main

if __name__ == "__main__":
    main()
