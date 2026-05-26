"""
generate_facets.py — Regenerate data/facets_clean.json from the raw CSV.

Usage:
    python scripts/generate_facets.py
    python scripts/generate_facets.py --csv path/to/Facets_Assignment.csv

The script:
1. Reads the raw CSV
2. Strips number prefixes (e.g. "800. ")
3. Deduplicates
4. Assigns categories via keyword matching
5. Generates short_description, rubric_low, rubric_high per facet
6. Saves to data/facets_clean.json
"""

import re
import json
import argparse
from pathlib import Path
from collections import Counter

DEFAULT_CSV = "Facets Assignment.csv"

CATEGORY_MAP = [
    ("Leadership",    ["leadership","democratic","transactional","delegat","initiative","ethical leadership","delegation"]),
    ("Emotion",       ["emotion","depress","happi","burnout","joy","irritab","mood","affect","anger","fear","sad","bliss","merriness","morose","contentment","joyful","ardency","vivacity","high-spirit","discontentment"]),
    ("Safety",        ["safety","harm","violence","hostil","abus","danger","physical-violence","harmfulness"]),
    ("Spiritual",     ["spiritual","relig","sufi","quran","hindu","buddhist","kabbalah","i ching","meditat","yoga","prayer","pilgrimage","holiness","reiki","astrology","sikh","kirtan","seerah","zohar","ridvan","satya","mantra","gnostic","jewish","sukkot","eightfold","dhikr","vrata","bhagavad","new-age","discernment","sacred text","scripture","ego dissolution","aura"]),
    ("Cognitive",     ["reason","memory","iq","decis","logic","intellig","attent","focus","learn","comprehension","working memory","synthesis","spatial","auditory","sequential","numerical reasoning","mental arith","rapid cognitive","estimat"]),
    ("Linguistic",    ["sentence","language","story","listen","communic","speak","verbal","spelling","storytelling","brevity","outspoken","talkativeness","non-verbal"]),
    ("Personality",   ["big five","hexaco","enneagram","neuroticism","conscientiousness","openness","psychoticism","impulsiv","rebellious","individuality","attachment"]),
    ("Health/Bio",    ["fsh","parathyroid","serotonin","basophil","chromatin","immune","metabolic","caffeine","sleep","chronic pain","drug-use","polygenic","macronutrient","dietary","snacking","breakfast","processed-food","commute","wake-time"]),
    ("Social",        ["social","community","peer","collaboration","cultural","multicultur","ethnocentr","patriot","nationality","civic","civility","volunteer","participation"]),
    ("Psychological", ["psychological","self-efficacy","self-esteem","self-compassion","resilience","hope scale","acculturative","executive-function","perfectionist","identity diffusion","excuse-making","operant","need for achievement","social desirability","consummatory","social conformity","cultural intelligence"]),
]


def assign_category(name: str):
    n = name.lower()
    for cat_name, keywords in CATEGORY_MAP:
        if any(k in n for k in keywords):
            return cat_name, cat_name.lower().replace("/", "_")
    return "Other", "other"


def generate_facets(csv_path: str) -> list:
    facets = []
    seen = set()
    skip = {"facets", "nan", ""}

    with open(csv_path, encoding="utf-8") as f:
        for line in f:
            raw = line.strip().strip("\r")
            text = re.sub(r"^\d+\.\s*", "", raw).strip().rstrip(":")
            if not text or text.lower() in skip or len(text) < 3:
                continue
            if text in seen:
                continue
            seen.add(text)

            category, group_id = assign_category(text)

            facets.append({
                "facet_id": len(facets) + 1,
                "name": text,
                "category": category,
                "short_description": (
                    f"Evaluate {text.lower()} as expressed in the speaker's language, "
                    f"tone, and behavioral signals during this conversation turn."
                ),
                "rubric_low": f"1 = {text} is absent or barely detectable",
                "rubric_high": f"5 = {text} is strongly and clearly present",
                "group_id": group_id,
            })

    return facets


def main():
    parser = argparse.ArgumentParser(description="Generate facets_clean.json from CSV")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to the raw facets CSV")
    parser.add_argument("--out", default="data/facets_clean.json", help="Output path")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"❌ CSV not found: {args.csv}")
        print(f"   Place your 'Facets Assignment.csv' in the repo root or pass --csv <path>")
        return

    facets = generate_facets(args.csv)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    with open(args.out, "w") as f:
        json.dump(facets, f, indent=2)

    print(f"✅ Generated {len(facets)} unique facets → {args.out}")
    print("\nCategory distribution:")
    cats = Counter(f["category"] for f in facets)
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<20} {count}")


if __name__ == "__main__":
    main()
