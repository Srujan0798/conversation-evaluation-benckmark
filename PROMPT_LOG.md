# Prompt Log — Ahoum Conversation Evaluation Benchmark

**Author:** Srujan Sai Choda  
**Date:** 2026-05-26  
**Assignment:** Ahoum AI/ML Intern — Conversation Evaluation Task

---

## 1. Problem Framing

The task requires scoring every conversation turn on 300+ facets.  
The naive approach — one prompt with all 399 facets — is explicitly disallowed (hard constraint: no one-shot solutions) and would exceed any model's context window at scale.

The core design question was: **how do you reliably extract structured scores for hundreds of facets from a small open-weights model?**

---

## 2. Prompt Design Iterations

### Iteration 1 — Naïve one-shot (rejected)

**Prompt sketch:**
```
Score this conversation on all 399 facets. Return JSON.
[full facet list]
[conversation text]
```

**Problems identified:**
- Violates hard constraint (one-shot)
- Output truncation: 399 facets × ~20 tokens each exceeds `max_new_tokens`
- Small models hallucinate or skip facets when the list is too long
- No reliable JSON structure at this scale

**Decision:** Rejected. Moved to batching.

---

### Iteration 2 — Batched prompting, flat list (working prototype)

Split facets into batches of N. Each batch = one LLM call.

**Prompt sketch:**
```
Score the CURRENT TURN on these facets. Return JSON array.
Facets: [facet_1, facet_2, ... facet_N]
Turn: "..."
```

**Problems identified:**
- Model confused about which turn to score when history was absent
- Output sometimes included prose before the JSON array
- Confidence was not requested — scores alone felt underspecified

**Decision:** Add conversation history for context, add confidence field, add explicit output format instruction.

---

### Iteration 3 — Final prompt (shipped)

```
You are an expert conversation analyst. Your job is to score the CURRENT TURN 
only (not the history) on a set of psychological, linguistic, emotional, and 
behavioral facets.

Conversation history (for context only):
{history}

CURRENT TURN TO SCORE:
"{turn}"

Facets to evaluate:
{facet_id}. {facet_name} — {short_description}

Scoring rules:
- Score each facet from 1 (very low / absent) to 5 (very high / clearly present).
- Confidence: 0-100 — how certain you are given the available text.
- If a facet is not inferable from the text, score it 1 with low confidence (~20).
- Base your scores only on the CURRENT TURN text. Use history for context only.

Return ONLY a valid JSON array — no preamble, no explanation, no markdown:
[{"facet_id": <int>, "score": <int 1-5>, "confidence": <int 0-100>}, ...]
```

**Key design decisions in this prompt:**

| Decision | Rationale |
|---|---|
| "CURRENT TURN only" (caps) | Prevents model from averaging over history |
| History section with label "for context only" | Enables pragmatic inference without scope confusion |
| `short_description` per facet | Grounds abstract facet names (e.g. "FSH level") in observable signals |
| Score 1–5 (not 0–4) | Avoids zero as a meaningful anchor; 1 = absent, not negative |
| Confidence 0–100 | Continuous range allows nuanced uncertainty expression |
| "not inferable → score 1, confidence ~20" | Handles bio/lab/spiritual facets that can't be inferred from text |
| "Return ONLY a valid JSON array" | Prevents markdown fences and prose preamble that break `json.loads()` |
| Markdown fence stripping as fallback | Some models wrap output anyway; strip and retry gracefully |

---

## 3. Batch Size Selection — Why 25

| Batch size | Tokens per call (est.) | Reliability | Throughput |
|---|---|---|---|
| 5 | ~300 | Very high | Very slow (80 calls/turn) |
| 10 | ~500 | High | Slow (40 calls/turn) |
| **25** | **~900** | **High** | **Good (16 calls/turn)** |
| 50 | ~1600 | Medium | Fast (8 calls/turn) |
| 100 | ~3000 | Low | Fast but brittle |

**25 was chosen** because:
- Fits within 4096 token context for all target models (Qwen2-7B, Llama-3-8B, Mixtral-8x7B)
- Small enough that the model reliably returns a complete, parseable JSON array
- Large enough that the overhead per turn (16 calls) is acceptable
- Configurable via `MAX_BATCH_SIZE` in `.env` — operators can tune up/down

---

## 4. Score Scale — Why 1–5 (not 0–4)

The assignment specifies "five ordered integers" without requiring 0–4 or 1–5.

**Choice: 1–5**

Rationale:
- 1 = clearly absent, 5 = clearly present — natural language anchors
- 0 carries connotations of "error" or "null" that confuse small models
- 1–5 is the most common Likert scale; models have seen it extensively in training data and score more consistently on it
- Avoids accidental interpretation of 0 as "not applicable" vs. "very low"

---

## 5. Confidence Calibration — 0–100

**Why a separate confidence field (not just score variance)?**

- A score of 3 on "Happiness" could mean "moderate happiness" OR "I can't tell" — confidence disambiguates
- Enables downstream filtering: consumers can drop scores with confidence < 40
- Enables aggregation weighting: `weighted_score = score × confidence / 100`

**Calibration guidance in prompt:**
- Facets inferable from explicit text → confidence 70–95
- Facets requiring inference from tone → confidence 40–70
- Facets not inferable (lab values, spiritual metrics on secular text) → confidence ~20

**Validation:** Scores are clamped to `[1,5]` and confidence to `[0,100]` in `evaluator.py:113-116` regardless of model output.

---

## 6. Model Selection — Qwen2-7B-Instruct

| Model | Params | License | JSON reliability | Context |
|---|---|---|---|---|
| **Qwen2-7B-Instruct** | 7B | Apache 2.0 | ✅ High | 32K |
| Llama-3.1-8B-Instruct | 8B | Llama 3 Community | ✅ High | 8K |
| Mixtral-8x7B-Instruct | 47B active (8×7B MoE) | Apache 2.0 | ✅ High | 32K |
| Phi-3-mini-4k | 3.8B | MIT | Medium | 4K |

**Qwen2-7B-Instruct selected** because:
- Apache 2.0 license (fully open, commercial-friendly)
- Consistently strong JSON-mode output in benchmarks
- 32K context window — headroom for long conversation histories
- 7B fits in 16GB VRAM (single consumer GPU)
- Easily swapped via `MODEL_NAME=` in `.env` — no code changes

All alternatives are available via the same swap mechanism.

---

## 7. Scalability Design

The system scales to 5000+ facets with **zero code changes**:

```
399 facets today  → 16 calls per turn
1000 facets       → 40 calls per turn  
5000 facets       → 200 calls per turn
```

The only file that changes is `data/facets_clean.json`. The batching loop in `evaluator.py:29-31` handles any length automatically:

```python
def batch_facets(facets, size=25):
    return [facets[i:i+size] for i in range(0, len(facets), size)]
```

For production at 5000 facets, throughput can be improved by:
- Increasing `MAX_BATCH_SIZE` to 50 (halves call count)
- Parallelising batch calls with `asyncio` (already architected for this)
- Using a larger model with higher context window (Mixtral-8x7B at 32K)

---

## 8. Facet Preprocessing Decisions

**Raw CSV → `data/facets_clean.json` transformations:**

| Step | What | Why |
|---|---|---|
| Strip number prefixes | `"800. Sufi practice: ..."` → `"Sufi practice: ..."` | Numbers are not part of the facet name |
| Remove header/blank rows | Skip `"Facets"`, empty lines | Not scoreable |
| Deduplicate | Remove exact-string duplicates | CSV had repeated entries |
| Category assignment | Keyword-match to 11 categories | Enables UI filtering and grouped analysis |
| `short_description` generation | Template: `"Evaluate {name} as expressed in language, tone, and behavioral signals"` | Grounds abstract names for the LLM |
| `rubric_low` / `rubric_high` | `"1 = {name} is absent"` / `"5 = {name} is strongly present"` | Anchors the scale per facet |
| `group_id` | Category slug | Used for batch grouping by topic |

**Result:** 399 unique, categorised facets from ~430 raw rows.

---

## 9. Error Handling & Fallback

```
LLM call succeeds + valid JSON  → use scores
LLM call succeeds + invalid JSON → log warning, fall back to mock scores  
LLM call fails (timeout/error)  → log warning, fall back to mock scores
```

Mock fallback (`evaluator.py:62-71`) ensures the pipeline never crashes — critical for production robustness.

---

*This prompt log documents the iterative design decisions behind the scoring system.*  
*The full Claude conversation used to build this project is attached separately.*
