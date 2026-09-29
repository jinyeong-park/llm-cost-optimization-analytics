"""
1_Is_Sonnet_Worth_It.py — Quality, Cost & Speed: Is Sonnet worth the premium?
Sonnet costs 4–6× more and responds 2× slower. This page shows when that premium is justified.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.data_loader import load_benchmark
from utils.theme import MODEL_COLORS, C_NAVY, C_MUTED, apply_layout

st.set_page_config(page_title="Is Sonnet Worth It?", layout="wide", page_icon="📊")

df = load_benchmark()
df["latency_s"] = df["latency_ms"] / 1000

TASK_ORDER = ["classification", "simple_extraction", "summary", "code_generation", "complex_reasoning"]
TASK_LABELS = {
    "classification":    "Classification",
    "simple_extraction": "Simple Extraction",
    "summary":           "Summary",
    "code_generation":   "Code Generation",
    "complex_reasoning": "Complex Reasoning",
}

st.title("Is Sonnet worth the extra cost?")
st.caption(
    "Sonnet costs 4–6× more per call and responds 2× slower. "
    "This page shows the one task where that premium is earned — and the three where it isn't."
)

st.divider()

# ── 01: Quality by Task ────────────────────────────────────────────────────────
st.subheader("01 — Quality: Sonnet only wins on Summarization")
st.caption(
    "Score = fraction of expected keywords found (1.0 = perfect). "
    "Gap ≥ 0.10 = Sonnet's quality premium is justified."
)

task_qual = df.groupby(["task_type", "model_label", "model_display"])["quality_score"].mean().reset_index()

fig1 = go.Figure()
for model in ["haiku", "sonnet"]:
    m = task_qual[task_qual["model_label"] == model]
    if len(m) == 0:
        continue
    display_name = m["model_display"].iloc[0]
    m = m.set_index("task_type").reindex(TASK_ORDER).reset_index()
    fig1.add_trace(go.Bar(
        x=[TASK_LABELS.get(t, t) for t in m["task_type"]],
        y=m["quality_score"],
        name=display_name,
        marker_color=MODEL_COLORS[model],
        text=m["quality_score"].apply(lambda x: f"{x:.2f}"),
        textposition="outside",
        textfont=dict(size=11),
    ))

apply_layout(fig1, height=340,
             yaxis=dict(range=[0, 1.25], title="Avg Quality Score"),
             xaxis=dict(title="Task Type"))
fig1.update_layout(barmode="group")
st.plotly_chart(fig1, use_container_width=True)
st.info(
    "**Simple Q&A & Code Generation:** Both score **1.0** — Haiku is fully sufficient. "
    "**Summarization:** Sonnet leads (0.93 vs 0.83) — the only task where the upgrade is earned. "
    "**Reasoning:** Haiku (0.75) outperforms Sonnet (0.68) — Sonnet is actively worse here."
)

st.divider()

# ── 02: Cost & Latency side by side ───────────────────────────────────────────
st.subheader("02 — Cost & Speed: Sonnet is 4–6× more expensive and 2× slower on every task")

col1, col2 = st.columns(2)

with col1:
    st.caption("Cost per call — Sonnet's premium vs Haiku")
    task_cost = df.groupby(["task_type", "model_label", "model_display"])["cost_usd"].mean().reset_index()

    fig2 = go.Figure()
    for model in ["haiku", "sonnet"]:
        m = task_cost[task_cost["model_label"] == model]
        if len(m) == 0:
            continue
        display_name = m["model_display"].iloc[0]
        m = m.set_index("task_type").reindex(TASK_ORDER).reset_index()
        fig2.add_trace(go.Bar(
            x=[TASK_LABELS.get(t, t) for t in m["task_type"]],
            y=m["cost_usd"],
            name=display_name,
            marker_color=MODEL_COLORS[model],
            text=m["cost_usd"].apply(lambda x: f"${x:.4f}"),
            textposition="outside",
            textfont=dict(size=10),
        ))
    apply_layout(fig2, height=320,
                 yaxis=dict(title="Avg Cost per Call (USD)"),
                 xaxis=dict(title=""))
    fig2.update_layout(barmode="group", showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.caption("Avg response time per task — Haiku is consistently faster")
    task_lat = df.groupby(["task_type", "model_label", "model_display"])["latency_s"].mean().reset_index()

    fig3 = go.Figure()
    for model in ["haiku", "sonnet"]:
        m = task_lat[task_lat["model_label"] == model]
        if len(m) == 0:
            continue
        display_name = m["model_display"].iloc[0]
        m = m.set_index("task_type").reindex(TASK_ORDER).reset_index()
        fig3.add_trace(go.Bar(
            x=[TASK_LABELS.get(t, t) for t in m["task_type"]],
            y=m["latency_s"],
            name=display_name,
            marker_color=MODEL_COLORS[model],
            text=m["latency_s"].apply(lambda x: f"{x:.1f} s"),
            textposition="outside",
            textfont=dict(size=10),
        ))
    apply_layout(fig3, height=320,
                 yaxis=dict(title="Avg Latency (s)"),
                 xaxis=dict(title=""))
    fig3.update_layout(barmode="group", showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

# Shared legend
st.markdown(
    f"<div style='text-align:center; font-size:0.85rem; color:#4E5B6B;'>"
    f"<span style='color:{C_NAVY}; font-weight:600;'>■</span> Claude Haiku 4.5 &nbsp;&nbsp;"
    f"<span style='color:{C_MUTED}; font-weight:600;'>■</span> Claude Sonnet 4.6"
    f"</div>",
    unsafe_allow_html=True,
)
st.info(
    "**Cost:** Sonnet is 4–6× more expensive on every task. "
    "Code Generation and Reasoning carry the highest cost — and Haiku wins quality on both. "
    "**Speed:** Haiku is ~2× faster across all tasks. "
    "Reasoning shows the largest gap — Sonnet is slower AND worse there."
)

st.divider()

# ── 03: Response time reliability ─────────────────────────────────────────────
st.subheader("03 — Reliability: Sonnet occasionally spikes past 11 s — Haiku stays predictable")
st.caption(
    "P50 = half of requests finish within this time. "
    "P95 = 95% finish within this time — the worst 1-in-20 case. "
    "Sonnet P95 = 11.5 s means 1 in 20 requests takes over 11 seconds."
)

pct_rows = []
for model in df["model_label"].unique():
    m = df[df["model_label"] == model]["latency_s"]
    display_name = df[df["model_label"] == model]["model_display"].iloc[0]
    pct_rows.append({
        "Model":        display_name,
        "P50 (median)": f"{np.percentile(m, 50):.1f} s",
        "P75":          f"{np.percentile(m, 75):.1f} s",
        "P95":          f"{np.percentile(m, 95):.1f} s",
        "P99":          f"{np.percentile(m, 99):.1f} s",
        "Max":          f"{m.max():.1f} s",
    })

pct_df = pd.DataFrame(pct_rows)

col3, col4 = st.columns(2)
with col3:
    st.dataframe(pct_df, use_container_width=True, hide_index=True)
    st.info(
        "**Haiku P95 = 5.5 s · Sonnet P95 = 11.5 s** — a 2× gap at the tail. "
        "For a 6-second response time target, Haiku passes comfortably; "
        "Sonnet fails 1 in 20 requests."
    )

with col4:
    fig4 = go.Figure()
    percentile_keys = ["P50 (median)", "P75", "P95", "P99"]
    for _, row in pct_df.iterrows():
        model_key = "haiku" if "Haiku" in row["Model"] else "sonnet"
        fig4.add_trace(go.Scatter(
            x=percentile_keys,
            y=[float(row[p].replace(" s", "")) for p in percentile_keys],
            mode="lines+markers",
            name=row["Model"],
            line=dict(color=MODEL_COLORS.get(model_key, C_MUTED), width=2.5),
            marker=dict(size=9),
        ))
    apply_layout(fig4, height=280, yaxis=dict(title="Latency (s)"))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── 04: Verdict ────────────────────────────────────────────────────────────────
st.subheader("Verdict — Use Sonnet only for Summarization")

verdict_data = {
    "Task":           ["Simple Q&A", "Code Generation", "Reasoning", "Summarization"],
    "Quality":        ["Tie (1.0 / 1.0)", "Tie (1.0 / 1.0)", "Haiku wins (0.75 vs 0.68)", "Sonnet wins (0.93 vs 0.83)"],
    "Speed":          ["Haiku faster", "Haiku faster", "Haiku faster", "Haiku faster"],
    "Cost":           ["Haiku 5× cheaper", "Haiku 5× cheaper", "Haiku 5× cheaper", "Haiku 5× cheaper"],
    "Use":            ["✅ Haiku", "✅ Haiku", "✅ Haiku", "⚠️ Sonnet"],
}
st.dataframe(pd.DataFrame(verdict_data), use_container_width=True, hide_index=True)
st.success(
    "**Sonnet earns its premium on exactly one task: Summarization.** "
    "On every other task, Haiku matches or beats Sonnet on quality while being 4–6× cheaper and 2× faster. "
    "See **Routing Rules** to configure which tasks route where."
)

# ── Provenance ─────────────────────────────────────────────────────────────────
st.caption(
    "Data source: Live benchmark — Claude Haiku 4.5 vs Claude Sonnet 4.6 · "
    "Quality = keyword-match scoring · Latency = wall-clock API response time"
)
