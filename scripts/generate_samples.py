"""
generate_samples.py — Generate 50 diverse sample conversations and score them.

Usage:
    python scripts/generate_samples.py
    python scripts/generate_samples.py --facets data/facets_clean.json --out sample_conversations/

Produces:
    sample_conversations/conversations.json  — 50 conversations (various scenarios)
    sample_conversations/scores.json         — Per-turn facet scores for all 50 conversations
    sample_conversations/summary_report.md   — Human-readable summary
"""

import json
import os
import random
import argparse
from pathlib import Path
from datetime import datetime

os.environ.setdefault("USE_MOCK", "true")

# ─── Conversation templates ────────────────────────────────────────────────────
SCENARIOS = [
    ("therapy_session",          ["User", "Assistant"]),
    ("job_interview",            ["Interviewer", "Candidate"]),
    ("customer_support",         ["Customer", "Support"]),
    ("medical_consultation",     ["Patient", "Doctor"]),
    ("conflict_resolution",      ["Person A", "Person B"]),
    ("mentorship",               ["Mentor", "Mentee"]),
    ("academic_tutoring",        ["Student", "Tutor"]),
    ("sales_negotiation",        ["Buyer", "Seller"]),
    ("crisis_support",           ["User", "Counselor"]),
    ("casual_chat",              ["User", "Friend"]),
]

TEMPLATES = {
    "therapy_session": [
        [("User", "I've been feeling really overwhelmed lately. Like nothing I do is ever good enough."),
         ("Assistant", "That sounds exhausting. Can you tell me more about what's been making you feel that way?"),
         ("User", "Work mostly. My manager never acknowledges my efforts. I work 12-hour days and it's like I don't exist."),
         ("Assistant", "I hear you. That kind of invisible labor takes a real toll. Have you been able to talk to anyone about this?"),
         ("User", "No. I don't want to burden my friends. They have their own problems."),
         ("Assistant", "Sharing how you feel isn't a burden — it's connection. Do you feel like you matter to the people around you?")],
        [("User", "I can't stop thinking about what happened. It keeps replaying in my head."),
         ("Assistant", "That sounds like it's really affecting your peace of mind. How long has this been going on?"),
         ("User", "About three weeks now. Ever since the accident."),
         ("Assistant", "Three weeks is a long time to carry that alone. Are you sleeping okay?"),
         ("User", "Not really. I wake up at 3am and just stare at the ceiling."),
         ("Assistant", "Sleep disruption after a traumatic event is very common. Let's talk about some grounding techniques.")],
    ],
    "job_interview": [
        [("Interviewer", "Tell me about yourself and why you're interested in this role."),
         ("Candidate", "I'm a software engineer with 5 years of experience in backend systems. I'm excited about this role because of the scale challenges your team faces."),
         ("Interviewer", "Can you walk me through a challenging technical problem you've solved?"),
         ("Candidate", "Sure — I redesigned our payment processing pipeline to handle 10x traffic during peak sales events."),
         ("Interviewer", "What was the biggest technical risk in that redesign?"),
         ("Candidate", "Race conditions under concurrent load. We solved it with idempotency keys and a distributed lock manager.")],
    ],
    "customer_support": [
        [("Customer", "My order still hasn't arrived and it's been 10 days. This is unacceptable!"),
         ("Support", "I completely understand your frustration. Let me look up your order right away."),
         ("Customer", "Order number 87432. I paid for express shipping!"),
         ("Support", "I see it here. There was a carrier delay in your region. I'm so sorry about this."),
         ("Customer", "Sorry doesn't help me. I needed this for an event that already passed."),
         ("Support", "That's truly unfortunate. I'd like to offer you a full refund and a 20% credit for your next order.")],
    ],
    "medical_consultation": [
        [("Patient", "I've been having chest pains on and off for about a week."),
         ("Doctor", "I'm glad you came in. Can you describe the pain — is it sharp, dull, or pressure-like?"),
         ("Patient", "More like pressure. Especially when I climb stairs."),
         ("Doctor", "Does it radiate anywhere — your arm, jaw, or back?"),
         ("Patient", "Sometimes my left arm feels a bit numb."),
         ("Doctor", "We need to run an EKG today. These symptoms need to be evaluated promptly.")],
    ],
    "conflict_resolution": [
        [("Person A", "You never listen to me. Every decision gets made without my input."),
         ("Person B", "That's not fair. I asked you about the timeline last week and you said you didn't care."),
         ("Person A", "Because I was exhausted! That doesn't mean I want to be excluded entirely."),
         ("Person B", "I didn't realize you felt excluded. I thought you were just busy."),
         ("Person A", "I need you to check in with me even when I seem disengaged."),
         ("Person B", "Okay, I can do that. Can we set up a standing 15-minute check-in each week?")],
    ],
    "mentorship": [
        [("Mentee", "I'm struggling to figure out my career path. I don't know if I should specialize or stay broad."),
         ("Mentor", "That's a question most people face in their first 5 years. What energizes you most day-to-day?"),
         ("Mentee", "I love solving ambiguous problems, not routine tasks."),
         ("Mentor", "That's a strong signal toward strategy or architecture roles. Have you explored product management?"),
         ("Mentee", "A little. But I worry I'd miss the technical depth."),
         ("Mentor", "Technical PMs are in high demand. You don't have to give up the depth — you channel it differently.")],
    ],
    "academic_tutoring": [
        [("Student", "I don't understand integration by parts at all. Can we go over it?"),
         ("Tutor", "Of course. The key insight is that it's the reverse of the product rule. Do you remember the product rule?"),
         ("Student", "d/dx[uv] = u'v + uv'. Yes."),
         ("Tutor", "Perfect. Integration by parts rearranges that: ∫u dv = uv - ∫v du. The trick is choosing u and dv wisely."),
         ("Student", "How do I know which part to call u?"),
         ("Tutor", "Use LIATE: Logarithmic, Inverse trig, Algebraic, Trig, Exponential — pick u from earlier in the list.")],
    ],
    "sales_negotiation": [
        [("Buyer", "Your quoted price is 30% above our budget. We can't proceed at that number."),
         ("Seller", "I appreciate your candor. Can you share what your budget ceiling is?"),
         ("Buyer", "Around $45,000 for the full implementation."),
         ("Seller", "At $45k we'd need to reduce the scope. What features are non-negotiable for you?"),
         ("Buyer", "Core integration and the analytics dashboard. We can skip the mobile app."),
         ("Seller", "That works. We can deliver core + analytics for $44,500 with a 6-week timeline.")],
    ],
    "crisis_support": [
        [("User", "I don't see the point anymore. Everything feels hopeless."),
         ("Counselor", "I'm really glad you reached out. Can you tell me more about what's been happening?"),
         ("User", "I lost my job, my relationship ended, and I've been alone for months."),
         ("Counselor", "That's an enormous amount of loss in a short time. You're carrying a heavy weight."),
         ("User", "I just don't know how to keep going."),
         ("Counselor", "Right now, you don't need to figure out everything — just this moment. Are you somewhere safe?")],
    ],
    "casual_chat": [
        [("User", "Ugh, Mondays are the worst. How do you stay motivated?"),
         ("Friend", "Honestly? I bribe myself with good coffee and a playlist that slaps."),
         ("User", "Ha! That's a solid system. What playlist?"),
         ("Friend", "It's called 'focused chaos'. Lot of lo-fi hip-hop and some unexpected 80s synth."),
         ("User", "I need that in my life. Share it?"),
         ("Friend", "Already sending it. Prepare for your productivity to go through the roof.")],
    ],
}


def get_turns_for_scenario(scenario_type: str, variant: int) -> list:
    templates = TEMPLATES.get(scenario_type)
    if not templates:
        # Fallback: generate generic turns
        speakers = dict(SCENARIOS)[scenario_type]
        return [
            {"speaker": speakers[i % 2], "text": f"This is turn {i+1} of a {scenario_type.replace('_', ' ')} conversation."}
            for i in range(6)
        ]
    template = templates[variant % len(templates)]
    return [{"speaker": spk, "text": txt} for spk, txt in template]


def generate_conversations(n: int = 50) -> list:
    conversations = []
    scenario_cycle = SCENARIOS * (n // len(SCENARIOS) + 1)
    for i in range(n):
        scenario_type, _ = scenario_cycle[i]
        variant = i // len(SCENARIOS)
        turns = get_turns_for_scenario(scenario_type, variant)
        conversations.append({
            "conversation_id": i + 1,
            "scenario_type": scenario_type,
            "variant": variant + 1,
            "turns": turns,
        })
    return conversations


def score_conversations(conversations: list, facets: list) -> list:
    from src.evaluator import score_conversation

    all_scores = []
    total = len(conversations)
    for i, conv in enumerate(conversations):
        print(f"  Scoring conversation {i+1}/{total} ({conv['scenario_type']})...", end="\r")
        turn_scores = score_conversation(conv["turns"], facets)
        all_scores.append({
            "conversation_id": conv["conversation_id"],
            "scenario_type": conv["scenario_type"],
            "turn_scores": turn_scores,
        })
    print()
    return all_scores


def write_summary(conversations: list, scores: list, out_dir: Path):
    lines = [
        f"# Sample Conversations — Summary Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Total conversations: {len(conversations)}",
        f"Facets per turn: {len(scores[0]['turn_scores'][0]['facet_scores']) if scores else 'N/A'}",
        "",
        "## Scenario Distribution",
        "",
    ]
    from collections import Counter
    counts = Counter(c["scenario_type"] for c in conversations)
    for scenario, count in sorted(counts.items()):
        lines.append(f"- **{scenario.replace('_', ' ').title()}**: {count}")
    lines += ["", "## Sample Scores (first conversation, first turn)", ""]
    if scores:
        first_turn = scores[0]["turn_scores"][0]
        lines.append(f"**Turn:** [{first_turn['speaker']}] {first_turn['text'][:80]}...")
        lines.append("")
        lines.append("| Facet | Score | Confidence |")
        lines.append("|-------|-------|------------|")
        for fs in first_turn["facet_scores"][:10]:
            lines.append(f"| {fs['name']} | {fs['score']} | {fs['confidence']}% |")

    (out_dir / "summary_report.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Generate sample conversations and scores")
    parser.add_argument("--facets", default="data/facets_clean.json")
    parser.add_argument("--out", default="sample_conversations")
    parser.add_argument("--n", type=int, default=50)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.facets) as f:
        facets = json.load(f)
    print(f"Loaded {len(facets)} facets.")

    print(f"Generating {args.n} conversations...")
    conversations = generate_conversations(args.n)
    (out_dir / "conversations.json").write_text(json.dumps(conversations, indent=2))
    print(f"Saved conversations → {out_dir}/conversations.json")

    print("Scoring conversations (mock mode)...")
    scores = score_conversations(conversations, facets)
    (out_dir / "scores.json").write_text(json.dumps(scores, indent=2))
    print(f"Saved scores → {out_dir}/scores.json")

    write_summary(conversations, scores, out_dir)
    print(f"Saved summary → {out_dir}/summary_report.md")
    print(f"\nDone. {args.n} conversations × {len(facets)} facets scored.")


if __name__ == "__main__":
    main()
