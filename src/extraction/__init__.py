from __future__ import annotations

from pathlib import Path
from typing import Any

from . import text_input


def extract_text(source: str | Path) -> dict[str, Any]:
    """Extract structured text from a .txt file path or a raw text string."""
    # If the source is short enough to be a file path, check if it exists
    source_str = str(source)
    if len(source_str) < 500:
        try:
            path = Path(source_str)
            if path.exists() and path.is_file():
                return text_input.parse(path)
        except OSError:
            pass

    # Raw text string
    return text_input.parse(source_str)
