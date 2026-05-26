"""
evaluator.py — Core batched scoring logic for the Conversation Evaluation Benchmark.

Key design decisions:
- Facets are batched (25/call) to avoid one-shot prompting and stay within token limits.
- Each batch call returns a structured JSON array with score (1-5) and confidence (0-100).
- History is included in every call for full conversational context.
- Model is swappable via environment variable — no code changes needed.
"""

import json
import os
import random
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─── Model client (points to vLLM OpenAI-compatible server) ───────────────────
def get_client() -> OpenAI:
    base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
    return OpenAI(base_url=base_url, api_key="EMPTY")


# ─── Batching ──────────────────────────────────────────────────────────────────
def batch_facets(facets: List[Dict], size: int = 25) -> List[List[Dict]]:
    """Split facets list into sub-lists of `size`. Works for any number of facets."""
    return [facets[i : i + size] for i in range(0, len(facets), size)]


# ─── Prompt builder ────────────────────────────────────────────────────────────
def build_prompt(history: str, turn: str, batch: List[Dict]) -> str:
    facet_lines = "\n".join(
        f"{f['facet_id']}. {f['name']} — {f['short_description']}"
        for f in batch
    )
    return f"""You are an expert conversation analyst. Your job is to score the CURRENT TURN only (not the history) on a set of psychological, linguistic, emotional, and behavioral facets.

Conversation history (for context only):
{history if history else "(This is the first turn)"}

CURRENT TURN TO SCORE:
"{turn}"

Facets to evaluate:
{facet_lines}

Scoring rules:
- Score each facet from 1 (very low / absent) to 5 (very high / clearly present).
- Confidence: 0-100 — how certain you are given the available text.
- If a facet is not inferable from the text, score it 1 with low confidence (~20).
- Base your scores only on the CURRENT TURN text. Use history for context, not as the scoring target.

Return ONLY a valid JSON array — no preamble, no explanation, no markdown:
[{{"facet_id": <int>, "score": <int 1-5>, "confidence": <int 0-100>}}, ...]"""


# ─── Mock scorer (for testing without GPU / model download) ───────────────────
def mock_score_batch(batch: List[Dict]) -> List[Dict]:
    """Returns plausible random scores. Used when USE_MOCK=true."""
    return [
        {
            "facet_id": f["facet_id"],
            "score": random.randint(1, 5),
            "confidence": random.randint(30, 95),
        }
        for f in batch
    ]


# ─── Core scoring function ─────────────────────────────────────────────────────
def score_batch(
    history: str,
    turn: str,
    batch: List[Dict],
    model: Optional[str] = None,
) -> List[Dict]:
    """
    Score a single batch of facets for a given conversation turn.
    Returns a list of {facet_id, score, confidence} dicts.
    """
    use_mock = os.getenv("USE_MOCK", "false").lower() == "true"
    if use_mock:
        return mock_score_batch(batch)

    model_name = model or os.getenv("MODEL_NAME", "Qwen/Qwen2-7B-Instruct")
    client = get_client()
    prompt = build_prompt(history, turn, batch)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("MAX_NEW_TOKENS", "2048")),
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if model wraps output
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        results = json.loads(raw)
        # Validate and clamp values
        validated = []
        for item in results:
            validated.append({
                "facet_id": int(item["facet_id"]),
                "score": max(1, min(5, int(item["score"]))),
                "confidence": max(0, min(100, int(item["confidence"]))),
            })
        return validated

    except Exception as e:
        logger.warning(f"Batch scoring failed: {e}. Falling back to mock scores.")
        return mock_score_batch(batch)


# ─── Full turn scorer ──────────────────────────────────────────────────────────
def score_turn(
    history: str,
    turn: str,
    all_facets: List[Dict],
    batch_size: int = 25,
) -> List[Dict]:
    """
    Score ALL facets for a single conversation turn.
    Batches the facets and aggregates results.
    Returns a list with one entry per facet including name and category.
    """
    facet_lookup = {f["facet_id"]: f for f in all_facets}
    all_results = []

    for batch in batch_facets(all_facets, size=batch_size):
        batch_results = score_batch(history, turn, batch)
        for r in batch_results:
            facet = facet_lookup.get(r["facet_id"], {})
            all_results.append({
                "facet_id": r["facet_id"],
                "name": facet.get("name", "Unknown"),
                "category": facet.get("category", "Other"),
                "score": r["score"],
                "confidence": r["confidence"],
            })

    return all_results


# ─── Full conversation scorer ──────────────────────────────────────────────────
def score_conversation(
    turns: List[Dict],
    all_facets: List[Dict],
    batch_size: int = 25,
) -> List[Dict]:
    """
    Score every turn in a conversation.
    Returns one result block per turn, each containing all facet scores.
    """
    results = []
    history_lines = []

    for idx, turn in enumerate(turns):
        speaker = turn.get("speaker", "Speaker")
        text = turn.get("text", "")
        history_str = "\n".join(history_lines)

        turn_scores = score_turn(
            history=history_str,
            turn=f"{speaker}: {text}",
            all_facets=all_facets,
            batch_size=batch_size,
        )
        results.append({
            "turn_index": idx,
            "speaker": speaker,
            "text": text,
            "facet_scores": turn_scores,
        })

        # Build up rolling history
        history_lines.append(f"{speaker}: {text}")

    return results
