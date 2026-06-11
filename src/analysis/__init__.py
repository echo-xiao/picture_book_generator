"""NLP analysis modules for picture book text.

Only chapter_split (TextTiling segmentation) is live — the visual_score /
complexity / key_events modules were never called and have been removed.
"""

from src.analysis.chapter_split import split_into_segments

__all__ = ["split_into_segments"]
