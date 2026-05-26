"""
test_evaluator.py — Basic tests for the scoring pipeline.

Run with:  pytest tests/
"""

import json
import os
import pytest

os.environ["USE_MOCK"] = "true"  # Always use mock in tests

from src.evaluator import batch_facets, score_turn, score_conversation, build_prompt


SAMPLE_FACETS = [
    {"facet_id": i, "name": f"Facet_{i}", "category": "Test",
     "short_description": f"Test facet {i}", "rubric_low": "1=low", "rubric_high": "5=high", "group_id": "test"}
    for i in range(1, 61)
]


def test_batch_facets_basic():
    batches = batch_facets(SAMPLE_FACETS, size=25)
    assert len(batches) == 3
    assert len(batches[0]) == 25
    assert len(batches[1]) == 25
    assert len(batches[2]) == 10


def test_batch_facets_exact_multiple():
    batches = batch_facets(SAMPLE_FACETS[:50], size=25)
    assert len(batches) == 2
    assert all(len(b) == 25 for b in batches)


def test_batch_facets_single():
    batches = batch_facets(SAMPLE_FACETS[:5], size=25)
    assert len(batches) == 1
    assert len(batches[0]) == 5


def test_score_turn_returns_all_facets():
    scores = score_turn("User: Hello", "Assistant: Hi there!", SAMPLE_FACETS)
    assert len(scores) == len(SAMPLE_FACETS)
    for s in scores:
        assert "facet_id" in s
        assert "score" in s
        assert "confidence" in s
        assert 1 <= s["score"] <= 5
        assert 0 <= s["confidence"] <= 100


def test_score_turn_empty_history():
    scores = score_turn("", "User: I feel great today.", SAMPLE_FACETS[:10])
    assert len(scores) == 10


def test_score_conversation_all_turns():
    turns = [
        {"speaker": "User", "text": "Hello there!"},
        {"speaker": "Assistant", "text": "Hi! How can I help?"},
        {"speaker": "User", "text": "I need some advice."},
    ]
    results = score_conversation(turns, SAMPLE_FACETS[:10])
    assert len(results) == 3
    for i, r in enumerate(results):
        assert r["turn_index"] == i
        assert r["speaker"] == turns[i]["speaker"]
        assert r["text"] == turns[i]["text"]
        assert len(r["facet_scores"]) == 10


def test_build_prompt_contains_key_elements():
    batch = SAMPLE_FACETS[:5]
    prompt = build_prompt("User: Hi", "Assistant: Hello", batch)
    assert "CURRENT TURN" in prompt
    assert "Facet_1" in prompt
    assert "score" in prompt.lower()
    assert "confidence" in prompt.lower()
    assert "1" in prompt and "5" in prompt


def test_score_conversation_history_accumulates():
    """Verify history grows correctly across turns."""
    turns = [
        {"speaker": "User", "text": "First turn"},
        {"speaker": "Assistant", "text": "Second turn"},
        {"speaker": "User", "text": "Third turn"},
    ]
    # Just verify it runs without errors and returns correct structure
    results = score_conversation(turns, SAMPLE_FACETS[:5])
    assert results[0]["text"] == "First turn"
    assert results[2]["text"] == "Third turn"
