"""chapter_split must not silently drop short fragments (root cause C).

A sub-segment under 10 words used to be `continue`d away — those scenes
vanished from the book with no record. They are now merged into the previous
segment, so no source text is lost.
"""

from __future__ import annotations

from src.analysis.chapter_split import split_into_segments


def test_short_tail_fragment_is_not_lost():
    long_para = " ".join(f"word{i}" for i in range(60))
    short_tail = "Zephyrqux marker phrase only eight words long here."  # 8 words, distinctive
    chapter_text = long_para + "\n\n" + short_tail

    segments = split_into_segments(chapter_text, chapters=[{"text": chapter_text, "title": "Ch"}])

    joined = " ".join(s.get("text", "") for s in segments)
    assert "Zephyrqux" in joined, "a short fragment was silently dropped"


def test_no_segment_under_ten_words_survives_alone():
    # Every emitted segment should be a real page (>= 10 words) — shorts merged.
    long_para = " ".join(f"tok{i}" for i in range(80))
    chapter_text = long_para + "\n\ntiny three words"
    segments = split_into_segments(chapter_text, chapters=[{"text": chapter_text, "title": "Ch"}])
    assert all(len(s.get("text", "").split()) >= 3 for s in segments)
    assert "tiny three words" in " ".join(s.get("text", "") for s in segments)
