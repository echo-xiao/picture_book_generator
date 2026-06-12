"""QAAgent.discard_result (src/agents/qa.py).

Self-correction checks a page twice (original + retry) but keeps one image.
The losing check used to stay in (or get duplicated into) per_page_results
and per_character_scores, double-counting the page in the chapter summary.
"""

from __future__ import annotations

from src.agents.qa import QAAgent


def _result(page: int, score: int, char_score: int) -> dict:
    return {
        "page": page,
        "overall_score": score,
        "character_consistency": {
            "score": score,
            "characters": [{"name": "Lucie Manette", "score": char_score}],
        },
    }


def _agent_with(*results: dict) -> QAAgent:
    qa = QAAgent("book")
    for r in results:
        qa.record_cached(r)
    return qa


def test_discard_removes_page_entry_and_character_score():
    old, new = _result(5, 40, 41), _result(5, 90, 91)
    qa = _agent_with(old, new)

    qa.discard_result(old)

    assert qa.per_page_results == [new]
    assert qa.per_character_scores["Lucie Manette"] == [91]


def test_discard_loser_when_old_kept():
    old, new = _result(5, 40, 41), _result(5, 30, 31)
    qa = _agent_with(old, new)

    qa.discard_result(new)

    assert qa.per_page_results == [old]
    assert qa.per_character_scores["Lucie Manette"] == [41]


def test_discard_unrecorded_result_is_noop():
    recorded = _result(5, 40, 41)
    qa = _agent_with(recorded)

    qa.discard_result(_result(6, 70, 71))

    assert qa.per_page_results == [recorded]
    assert qa.per_character_scores["Lucie Manette"] == [41]


def test_discard_identity_not_equality():
    # Two equal dicts (cached report re-read from disk) — only the exact
    # object passed in may be removed.
    a, b = _result(5, 40, 41), _result(5, 40, 41)
    qa = _agent_with(a, b)

    qa.discard_result(b)

    assert len(qa.per_page_results) == 1
    assert qa.per_page_results[0] is a
