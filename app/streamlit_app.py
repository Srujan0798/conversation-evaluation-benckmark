"""
streamlit_app.py — Sample UI for the Conversation Evaluation Benchmark.

Features:
- Upload a conversation JSON file or type turns manually
- View per-turn facet scores in a table + heatmap
- Filter by category
- Download scores as CSV
"""

import streamlit as st
import requests
import pandas as pd
import json
import os
import plotly.express as px

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Ahoum Conversation Evaluator",
    page_icon="🧠",
    layout="wide",
)

# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🧠 Ahoum Conversation Evaluation Benchmark")
st.caption("Score every conversation turn across 399 psychological, linguistic, and emotional facets.")

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    batch_size = st.slider("Batch size (facets/call)", 10, 50, 25)
    category_filter = st.selectbox(
        "Filter results by category",
        ["All", "Emotion", "Cognitive", "Spiritual", "Linguistic", "Leadership",
         "Safety", "Social", "Personality", "Health/Bio", "Psychological", "Other"],
    )
    st.divider()

    # Backend health
    try:
        health = requests.get(f"{BACKEND_URL}/health", timeout=3).json()
        st.success(f"✅ Backend connected\n\nModel: `{health['model']}`\nFacets: {health['facets_loaded']}")
        mock_mode = health.get("mock_mode", "false") == "true"
        if mock_mode:
            st.warning("⚠️ Running in MOCK mode (no real model)")
    except Exception:
        st.error("❌ Backend not reachable. Is it running?")

    st.divider()
    st.markdown("**How to use:**\n1. Upload a conversation JSON\n2. Or enter turns manually\n3. Click Score\n4. Explore results by turn & category")

# ─── Input mode ───────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📁 Upload JSON", "✏️ Manual Entry"])

conversation = None

with tab1:
    uploaded = st.file_uploader(
        "Upload conversation JSON",
        type=["json"],
        help='Format: {"turns": [{"speaker": "User", "text": "..."}, ...]}'
    )
    if uploaded:
        try:
            conversation = json.load(uploaded)
            st.success(f"Loaded conversation with {len(conversation.get('turns', []))} turns.")
            with st.expander("Preview conversation"):
                for i, t in enumerate(conversation.get("turns", [])):
                    st.markdown(f"**Turn {i+1} [{t['speaker']}]:** {t['text']}")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

with tab2:
    st.markdown("Add turns one by one:")
    if "manual_turns" not in st.session_state:
        st.session_state.manual_turns = []

    col1, col2 = st.columns([1, 4])
    with col1:
        speaker = st.selectbox("Speaker", ["User", "Assistant"])
    with col2:
        turn_text = st.text_input("Turn text")

    if st.button("Add Turn") and turn_text.strip():
        st.session_state.manual_turns.append({"speaker": speaker, "text": turn_text})
        st.rerun()

    if st.session_state.manual_turns:
        for i, t in enumerate(st.session_state.manual_turns):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(f"**Turn {i+1} [{t['speaker']}]:** {t['text']}")
            with col_b:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.manual_turns.pop(i)
                    st.rerun()

        conversation = {"turns": st.session_state.manual_turns}

        if st.button("🗑️ Clear all turns"):
            st.session_state.manual_turns = []
            st.rerun()

# ─── Score button ──────────────────────────────────────────────────────────────
st.divider()

if conversation and conversation.get("turns"):
    if st.button("🚀 Score Conversation", type="primary", use_container_width=True):
        with st.spinner("Scoring all turns across 399 facets... (this may take a moment)"):
            try:
                payload = {
                    "turns": conversation["turns"],
                    "batch_size": batch_size,
                }
                resp = requests.post(
                    f"{BACKEND_URL}/score-conversation",
                    json=payload,
                    timeout=300,
                )
                resp.raise_for_status()
                data = resp.json()
                st.session_state["results"] = data
            except Exception as e:
                st.error(f"Scoring failed: {e}")

# ─── Results ──────────────────────────────────────────────────────────────────
if "results" in st.session_state:
    data = st.session_state["results"]
    results = data["results"]

    st.success(f"✅ Scored {data['total_turns']} turns × {data['total_facets']} facets using `{data['model']}`")

    # Build flat DataFrame
    rows = []
    for turn_res in results:
        for fs in turn_res["facet_scores"]:
            if category_filter != "All" and fs["category"] != category_filter:
                continue
            rows.append({
                "turn": turn_res["turn_index"] + 1,
                "speaker": turn_res["speaker"],
                "turn_text": turn_res["text"][:60] + "..." if len(turn_res["text"]) > 60 else turn_res["text"],
                "facet_id": fs["facet_id"],
                "facet_name": fs["name"],
                "category": fs["category"],
                "score": fs["score"],
                "confidence": fs["confidence"],
            })
    df = pd.DataFrame(rows)

    # ─── Per-turn tables ───────────────────────────────────────────────────────
    st.subheader("Per-Turn Scores")
    for turn_res in results:
        with st.expander(f"Turn {turn_res['turn_index']+1} — [{turn_res['speaker']}] {turn_res['text'][:80]}"):
            turn_df = pd.DataFrame(turn_res["facet_scores"])
            if category_filter != "All":
                turn_df = turn_df[turn_df["category"] == category_filter]
            turn_df = turn_df.sort_values("score", ascending=False)
            st.dataframe(
                turn_df[["facet_id", "name", "category", "score", "confidence"]],
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                f"⬇ Download Turn {turn_res['turn_index']+1} CSV",
                turn_df.to_csv(index=False),
                f"turn_{turn_res['turn_index']+1}_scores.csv",
                key=f"dl_{turn_res['turn_index']}",
            )

    # ─── Heatmap ──────────────────────────────────────────────────────────────
    st.subheader("📊 Score Heatmap (Score by Facet × Turn)")
    if not df.empty:
        pivot = df.pivot_table(index="facet_name", columns="turn", values="score", aggfunc="mean")
        fig = px.imshow(
            pivot,
            color_continuous_scale="RdYlGn",
            zmin=1, zmax=5,
            labels={"color": "Score"},
            title="Facet Scores Across Turns",
            height=max(400, len(pivot) * 15),
        )
        fig.update_layout(font_size=10)
        st.plotly_chart(fig, use_container_width=True)

    # ─── Category averages ─────────────────────────────────────────────────────
    st.subheader("📈 Average Score by Category")
    if not df.empty:
        cat_avg = df.groupby("category")["score"].mean().reset_index().sort_values("score", ascending=False)
        fig2 = px.bar(cat_avg, x="category", y="score", color="score",
                      color_continuous_scale="RdYlGn", range_color=[1, 5],
                      title="Mean Score per Category")
        st.plotly_chart(fig2, use_container_width=True)

    # ─── Full export ───────────────────────────────────────────────────────────
    st.divider()
    st.download_button(
        "⬇ Download Full Results CSV",
        df.to_csv(index=False),
        "all_scores.csv",
        use_container_width=True,
    )
