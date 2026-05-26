# Sample Conversations — Summary Report

## Overview

| Metric | Value |
|---|---|
| Total conversations | 50 |
| Scenario types | 10 |
| Variants per scenario | 5 |
| Facets scored per turn | 399 |
| Total (turn × facet) scores | 175,560 |
| Score scale | 1–5 (ordered integers) |
| Confidence scale | 0–100 |

---

## Scenario Types

| Scenario | Description |
|---|---|
| `therapy_session` | Therapist-client emotional disclosure and support |
| `heated_argument` | Interpersonal conflict with emotional escalation |
| `spiritual_discussion` | Exploration of Sufi, Hindu, Buddhist, Kabbalah practices |
| `sales_call` | B2B sales pitch with objection handling |
| `crisis_intervention` | User expressing emotional emptiness, suicidal ideation context |
| `tech_support` | BSOD / RAM diagnostic walkthrough |
| `casual_philosophical` | Dream, consciousness, grief discussion |
| `team_meeting` | Sprint blocker review, project timeline negotiation |
| `customer_complaint` | Delayed order, escalation and resolution |
| `philosophical_debate` | Free will, determinism, moral responsibility |

---

## Files

| File | Description |
|---|---|
| `conversations.json` | 50 full conversations (turns + speakers) |
| `scores.json` | Full facet scores per turn per conversation |
| `summary_report.md` | This file |

---

## Score Distribution Notes

Scores are biased by scenario type to reflect realistic facet expression:
- **Crisis/Emotion scenarios** → high Emotion, Safety, Psychological scores
- **Spiritual discussions** → high Spiritual, Linguistic scores
- **Tech support** → high Cognitive scores, low Emotion
- **Philosophical debates** → high Cognitive, Linguistic scores

---

## How Scores Were Generated

Scores in this sample were produced using the same pipeline architecture as the main system (`src/evaluator.py`), with `USE_MOCK=true` for reproducibility in the sample submission. The production system uses **Qwen2-7B-Instruct** via vLLM to produce real LLM-grounded scores.

To regenerate real scores from the model:
```bash
USE_MOCK=false python -c "
from src.evaluator import score_conversation
import json
with open('sample_conversations/conversations.json') as f:
    convs = json.load(f)
with open('data/facets_clean.json') as f:
    facets = json.load(f)
# Score and save...
"
```
