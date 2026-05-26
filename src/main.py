"""
main.py — FastAPI backend for the Conversation Evaluation Benchmark.

Endpoints:
  POST /score              → Score a single turn on all 399 facets
  POST /score-conversation → Score all turns in a full conversation
  GET  /facets             → List all loaded facets
  GET  /health             → Health check
"""

import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from src.evaluator import score_turn, score_conversation

load_dotenv()

app = FastAPI(
    title="Ahoum Conversation Evaluation API",
    description="Score every conversation turn on 399 psychological, linguistic, and emotional facets.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Load facets at startup ────────────────────────────────────────────────────
FACETS_PATH = Path("data/facets_clean.json")
if not FACETS_PATH.exists():
    raise RuntimeError(f"Facets file not found at {FACETS_PATH}. Run scripts/generate_facets.py first.")

with open(FACETS_PATH) as f:
    ALL_FACETS = json.load(f)

MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2-7B-Instruct")
BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "25"))


# ─── Request / Response Models ─────────────────────────────────────────────────
class TurnRequest(BaseModel):
    history: str = ""
    turn: str
    batch_size: Optional[int] = None


class TurnItem(BaseModel):
    speaker: str
    text: str


class ConversationRequest(BaseModel):
    turns: List[TurnItem]
    batch_size: Optional[int] = None


class FacetScore(BaseModel):
    facet_id: int
    name: str
    category: str
    score: int
    confidence: int


class TurnResponse(BaseModel):
    scores: List[FacetScore]
    total_facets: int
    model: str


class TurnResult(BaseModel):
    turn_index: int
    speaker: str
    text: str
    facet_scores: List[FacetScore]


class ConversationResponse(BaseModel):
    results: List[TurnResult]
    total_turns: int
    total_facets: int
    model: str


# ─── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "facets_loaded": len(ALL_FACETS),
        "model": MODEL_NAME,
        "mock_mode": os.getenv("USE_MOCK", "false"),
    }


@app.get("/facets")
def list_facets(category: Optional[str] = None):
    """List all facets, optionally filtered by category."""
    facets = ALL_FACETS
    if category:
        facets = [f for f in facets if f["category"].lower() == category.lower()]
    return {"facets": facets, "total": len(facets)}


@app.post("/score", response_model=TurnResponse)
def score_single_turn(request: TurnRequest):
    """Score a single conversation turn across all facets."""
    if not request.turn.strip():
        raise HTTPException(status_code=400, detail="Turn text cannot be empty.")

    batch_size = request.batch_size or BATCH_SIZE

    scores = score_turn(
        history=request.history,
        turn=request.turn,
        all_facets=ALL_FACETS,
        batch_size=batch_size,
    )

    return TurnResponse(
        scores=scores,
        total_facets=len(scores),
        model=MODEL_NAME,
    )


@app.post("/score-conversation", response_model=ConversationResponse)
def score_full_conversation(request: ConversationRequest):
    """Score every turn in a full conversation."""
    if not request.turns:
        raise HTTPException(status_code=400, detail="Turns list cannot be empty.")

    batch_size = request.batch_size or BATCH_SIZE
    turns_dicts = [{"speaker": t.speaker, "text": t.text} for t in request.turns]

    results = score_conversation(
        turns=turns_dicts,
        all_facets=ALL_FACETS,
        batch_size=batch_size,
    )

    return ConversationResponse(
        results=results,
        total_turns=len(results),
        total_facets=len(ALL_FACETS),
        model=MODEL_NAME,
    )
