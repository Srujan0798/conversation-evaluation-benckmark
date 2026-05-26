# Ahoum AI/ML Assignment — Conversation Evaluation Benchmark

Production-ready system that scores **every conversation turn** across **399 facets** covering linguistic quality, pragmatics, safety, emotion, spirituality, cognition, and more. Scales to **5000+ facets with zero architectural changes**.

---

## Hard Constraints Satisfied

| Constraint | How |
|---|---|
| No one-shot prompts | Batched few-shot JSON prompting (25 facets/call) |
| Open-weights ≤ 16B | Qwen2-7B-Instruct (Apache 2.0) — swap via `.env` |
| Scales to 5000+ facets | Facets are pure data; architecture is data-driven |

## Brownie Points Delivered

- ✅ Confidence score (0–100) per facet per turn
- ✅ Fully Dockerised (multi-container, one command)
- ✅ Sample Streamlit UI
- ✅ 50 diverse conversations + full scores (ZIP ready)

---

## Architecture

```
conversation-evaluation-benchmark/
├── data/
│   └── facets_clean.json        # 399 cleaned + categorised facets
├── src/
│   ├── evaluator.py             # Core batched scoring logic
│   ├── main.py                  # FastAPI backend
│   └── models.py                # Model abstraction layer
├── app/
│   └── streamlit_app.py         # Sample UI
├── sample_conversations/        # 50 conversations + scores (Deliverable 3)
├── scripts/
│   ├── generate_facets.py       # Regenerate facets from CSV
│   └── generate_samples.py      # Regenerate sample conversations
├── tests/
│   └── test_evaluator.py
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.ui
└── requirements.txt
```

**Pipeline per turn:**
1. Load conversation turn + full history
2. Chunk 399 facets into batches of 25 (by category group)
3. LLM call per batch → structured JSON output (score + confidence)
4. Aggregate all batches → full turn score vector
5. Store results

**Model:** Qwen2-7B-Instruct (Apache 2.0). Swap to `Llama-3.1-8B` or `Mixtral-8x7B` by changing one line in `.env`.

---

## Quick Start (One Command)

```bash
git clone https://github.com/YOURUSERNAME/conversation-evaluation-benchmark
cd conversation-evaluation-benchmark
cp .env.example .env
docker-compose up --build
```

- **API:** http://localhost:8000
- **UI:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

---

## Running Without Docker (Local Dev)

```bash
pip install -r requirements.txt
cp .env.example .env

# Start backend
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Start UI (new terminal)
streamlit run app/streamlit_app.py
```

**Note:** Without a GPU you can set `USE_MOCK=true` in `.env` to test the pipeline with a mock model.

---

## API Usage

### Score a single turn

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "history": "User: Hi how are you?\nAssistant: I am good thanks!",
    "turn": "User: I have been feeling really anxious lately and I don't know why."
  }'
```

**Response:**
```json
{
  "scores": [
    {"facet_id": 1, "name": "Risktaking", "score": 2, "confidence": 71},
    {"facet_id": 3, "name": "Acidity", "score": 1, "confidence": 88},
    ...
  ],
  "total_facets": 399,
  "model": "Qwen/Qwen2-7B-Instruct"
}
```

### Score a full conversation

```bash
curl -X POST http://localhost:8000/score-conversation \
  -H "Content-Type: application/json" \
  -d @sample_conversations/conversations.json
```

---

## Facet Dataset

The `data/facets_clean.json` file contains 399 cleaned facets from `Facets Assignment.csv`.

**Columns added:**
| Column | Description |
|---|---|
| `facet_id` | Unique integer ID |
| `name` | Cleaned facet name (prefixes stripped) |
| `category` | Smart category (Emotion, Cognitive, Spiritual, etc.) |
| `short_description` | Evaluation prompt for the LLM |
| `rubric_low` | What score 1 looks like |
| `rubric_high` | What score 5 looks like |
| `group_id` | Batch grouping key |

**Category distribution:**
- Other: 208 | Cognitive: 43 | Spiritual: 40 | Emotion: 26
- Health/Bio: 22 | Social: 20 | Personality: 14 | Linguistic: 10
- Leadership: 9 | Safety: 5 | Psychological: 2

---

## Deliverables

| Deliverable | Location |
|---|---|
| GitHub repo + docs | This repo |
| Cleaned facet dataset | `data/facets_clean.json` |
| Scoring system | `src/evaluator.py` + `src/main.py` |
| Sample UI | `app/streamlit_app.py` |
| 50 conversations + scores | `sample_conversations/` → zip this folder |
| Prompt log | Attached separately |

---

## Scaling to 5000+ Facets

To scale from 399 to 5000 facets:
1. Add entries to `data/facets_clean.json` (or regenerate from a larger CSV)
2. Adjust `MAX_BATCH_SIZE` in `.env` if needed (default 25 is optimal)
3. `docker-compose restart backend`

**No code changes required.** The batching loop in `evaluator.py` handles any number of facets automatically.

---

## Model Swapping

Change one line in `.env`:

```env
# Default
MODEL_NAME=Qwen/Qwen2-7B-Instruct

# Alternatives (all Apache 2.0 or similar open licenses, ≤16B)
MODEL_NAME=meta-llama/Meta-Llama-3.1-8B-Instruct
MODEL_NAME=mistralai/Mixtral-8x7B-Instruct-v0.1
MODEL_NAME=microsoft/Phi-3-mini-4k-instruct
```

Restart the backend container and you're done.
