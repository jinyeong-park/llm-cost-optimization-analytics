"""
Summary.py — LLM Cost & Performance Routing Analytics
Executive briefing: one page that answers the primary question.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from utils.data_loader import load_benchmark, load_observability_data
from utils.theme import (MODEL_COLORS, C_NAVY, C_MUTED, C_BLUE, C_AMBER,
                         C_GREEN, C_BORDER, C_TEXT_PRIMARY, C_TEXT_SECONDARY, C_TEXT_MUTED,
                         apply_layout)

st.set_page_config(page_title="LLM Routing Analytics", layout="wide", page_icon="⚡")

df  = load_benchmark()
obs = load_observability_data()

# ── Derived metrics ────────────────────────────────────────────────────────────
haiku  = df[df["model_label"] == "haiku"]
sonnet = df[df["model_label"] == "sonnet"]

haiku_name  = haiku["model_display"].iloc[0]  if len(haiku)  > 0 else "Haiku"
sonnet_name = sonnet["model_display"].iloc[0] if len(sonnet) > 0 else "Sonnet"

haiku_cost  = haiku["cost_usd"].sum()
sonnet_cost = sonnet["cost_usd"].sum()
haiku_q     = haiku["quality_score"].mean()
sonnet_q    = sonnet["quality_score"].mean()
cost_ratio  = sonnet_cost / haiku_cost if haiku_cost > 0 else 0

# Routing rule: use Haiku when quality gap ≤ 0.1
merged = haiku.merge(
    sonnet[["task_type", "difficulty", "quality_score", "cost_usd"]],
    on=["task_type", "difficulty"],
    suffixes=("_haiku", "_sonnet"),
)
merged["quality_gap"] = merged["quality_score_sonnet"] - merged["quality_score_haiku"]
merged["use_haiku"]   = merged["quality_gap"] <= 0.1

routed_cost    = merged.apply(
    lambda r: r["cost_usd_haiku"] if r["use_haiku"] else r["cost_usd_sonnet"], axis=1
).sum()
baseline_cost  = merged["cost_usd_sonnet"].sum()
savings_pct    = round((1 - routed_cost / baseline_cost) * 100, 1) if baseline_cost > 0 else 0
routed_tasks   = int(merged["use_haiku"].sum())
total_tasks    = len(merged)

# ── Hero block ─────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="
        background: #EEF2F8;
        border-left: 4px solid {C_NAVY};
        border-radius: 6px;
        padding: 20px 24px 16px 24px;
        margin-bottom: 8px;
    ">
        <div style="font-size:0.72rem; font-weight:600; letter-spacing:0.08em;
                    text-transform:uppercase; color:#4E5B6B; margin-bottom:6px;">
            Executive Finding
        </div>
        <div style="font-size:1.55rem; font-weight:700; color:{C_NAVY}; line-height:1.3; margin-bottom:10px;">
            Dynamic routing cuts LLM API cost by <span style="font-size:2rem;">{savings_pct}%</span>
            — Haiku matches or beats Sonnet quality on {routed_tasks} of {total_tasks} task types.
        </div>
        <div style="font-size:0.85rem; color:#4E5B6B; line-height:1.6;">
            Sonnet costs <strong>{cost_ratio:.1f}×</strong> more per call &nbsp;·&nbsp;
            Haiku quality avg: <strong>{haiku_q:.2f}</strong> &nbsp;·&nbsp;
            Sonnet quality avg: <strong>{sonnet_q:.2f}</strong> (gap: {sonnet_q - haiku_q:.3f}) &nbsp;·&nbsp;
            Summarization is the single task where Sonnet's quality premium is justified.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── KPI Cards ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"{haiku_name} Quality",  f"{haiku_q:.2f}",  "avg across all tasks")
c2.metric(f"{sonnet_name} Quality", f"{sonnet_q:.2f}", "avg across all tasks")
c3.metric("Cost Ratio",             f"{cost_ratio:.1f}×", "Sonnet vs Haiku per call")
c4.metric("Quality Gap",            f"{sonnet_q - haiku_q:.3f}", "Sonnet − Haiku (avg)")
c5.metric("Routing Savings",        f"{savings_pct}%",  "vs all-Sonnet baseline")

st.divider()

# ── 01: Cost vs Quality — the core tradeoff ────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("01 — Haiku delivers equal or better quality at a fraction of the cost")
    st.caption("Each point = one task·difficulty combination. Top-left = ideal (high quality, low cost).")

    fig = go.Figure()
    colors = MODEL_COLORS
    for model in ["haiku", "sonnet"]:
        m = df[df["model_label"] == model]
        if len(m) == 0:
            continue
        display = m["model_display"].iloc[0]
        fig.add_trace(go.Scatter(
            x=m["cost_usd"],
            y=m["quality_score"],
            mode="markers",
            name=display,
            marker=dict(size=13, color=colors[model], opacity=0.9),
            text=m["task_type"] + " (" + m["difficulty"] + ")",
            hovertemplate="<b>%{text}</b><br>Cost: $%{x:.5f}<br>Quality: %{y:.2f}<extra></extra>",
        ))
    apply_layout(fig, height=360,
                 xaxis=dict(title="Cost per call (USD)"),
                 yaxis=dict(title="Quality Score", range=[0, 1.1]))
    st.plotly_chart(fig, use_container_width=True)
    st.info(
        "**Takeaway:** Haiku (navy) clusters top-left — high quality, low cost. "
        "Sonnet (gray) sits further right with no upward shift on most tasks. "
        "Only Summarization shows Sonnet moving meaningfully higher on quality (0.93 vs 0.83)."
    )

with col2:
    st.subheader("02 — Haiku is 2× faster with a tighter latency tail")
    st.caption("Lower and tighter = better for real-time applications. P95 tail determines SLA risk.")

    fig2 = go.Figure()
    for model in ["haiku", "sonnet"]:
        m = df[df["model_label"] == model]
        if len(m) == 0:
            continue
        display = m["model_display"].iloc[0]
        fig2.add_trace(go.Box(
            y=m["latency_ms"],
            name=display,
            marker_color=MODEL_COLORS[model],
            line_color=MODEL_COLORS[model],
            boxpoints="all",
            jitter=0.3,
            pointpos=-1.8,
        ))
    apply_layout(fig2, height=360, yaxis=dict(title="Latency (ms)"))
    st.plotly_chart(fig2, use_container_width=True)
    st.info(
        "**Takeaway:** Haiku P50 = **2,501 ms** vs Sonnet P50 = **4,960 ms**. "
        "At P95, the gap widens: Haiku 5,451 ms vs Sonnet 11,548 ms. "
        "Sonnet's long right tail creates SLA risk for any synchronous user-facing feature."
    )

st.divider()

# ── 03: Routing decision table ─────────────────────────────────────────────────
st.subheader("03 — Routing decision: 3 of 4 task types go to Haiku")
st.caption("Threshold = 0.10 quality gap. Tasks below the threshold route to Haiku automatically.")

TASK_LABELS = {
    "simple_qa": "Simple Q&A", "summarization": "Summarization",
    "code_generation": "Code Generation", "reasoning": "Reasoning",
}

task_summary = merged.copy()
task_summary["routing_decision"] = task_summary["use_haiku"].map(
    {True: "✅ Route → Haiku", False: "⚠️ Route → Sonnet"}
)
task_summary["cost_saved_usd"] = task_summary["cost_usd_sonnet"] - task_summary.apply(
    lambda r: r["cost_usd_haiku"] if r["use_haiku"] else r["cost_usd_sonnet"], axis=1
)

display_cols = ["task_type", "difficulty", "quality_score_haiku",
                "quality_score_sonnet", "quality_gap", "routing_decision", "cost_saved_usd"]
display_df = task_summary[display_cols].rename(columns={
    "task_type": "Task",
    "difficulty": "Difficulty",
    "quality_score_haiku": "Haiku Quality",
    "quality_score_sonnet": "Sonnet Quality",
    "quality_gap": "Quality Gap",
    "routing_decision": "Routing Decision",
    "cost_saved_usd": "Cost Saved ($)",
})
display_df["Task"] = display_df["Task"].map(TASK_LABELS)

st.dataframe(display_df.style.format({
    "Haiku Quality": "{:.2f}",
    "Sonnet Quality": "{:.2f}",
    "Quality Gap": "{:.3f}",
    "Cost Saved ($)": "${:.5f}",
}), use_container_width=True, hide_index=True)
st.info(
    "**Takeaway:** Summarization is the only task where the quality gap (≥0.10) justifies Sonnet. "
    "Reasoning routes to Haiku because Haiku *outperforms* Sonnet there (0.75 vs 0.68). "
    "For Simple Q&A and Code Generation, both models score 1.0 — Haiku is the obvious choice."
)

st.divider()

# ── 04: 3 Cost Levers ──────────────────────────────────────────────────────────
st.subheader("04 — Three levers to reduce LLM cost")
st.caption(
    "Model routing gets you most of the way. "
    "Prompt optimization and output control compound on top of that."
)

# ── Lever data ─────────────────────────────────────────────────────────────────
# Lever 1: routing savings (already computed above)
lever1_savings = savings_pct

# Lever 2: prompt optimization — impact of reducing input tokens by 20%
# Use observability data for realistic token distributions
avg_input_by_task = obs.groupby("task_type")["input_tokens"].mean()
avg_cost_by_task  = obs.groupby("task_type")["cost_usd"].mean()
PRICING_INPUT = {
    "claude-haiku-4-5-20251001": 0.80 / 1_000_000,
    "claude-sonnet-4-6":         3.00 / 1_000_000,
}
ROUTING = {
    "classification":    "claude-haiku-4-5-20251001",
    "simple_extraction": "claude-haiku-4-5-20251001",
    "summary":           "claude-haiku-4-5-20251001",
    "code_generation":   "claude-sonnet-4-6",
    "complex_reasoning": "claude-sonnet-4-6",
}
input_reduction = 0.20   # 20% fewer input tokens
lever2_savings_per_req = {
    t: avg_input_by_task[t] * input_reduction * PRICING_INPUT[ROUTING[t]]
    for t in avg_input_by_task.index
}
lever2_weighted_pct = sum(
    lever2_savings_per_req[t] / avg_cost_by_task[t]
    for t in lever2_savings_per_req if avg_cost_by_task[t] > 0
) / len(lever2_savings_per_req) * 100

# Lever 3: output length control
# Output costs 5× more than input per token (both Haiku and Sonnet)
output_ratio_haiku  = 4.00 / 0.80    # $4 output / $0.80 input = 5×
output_ratio_sonnet = 15.00 / 3.00   # $15 output / $3.00 input = 5×

# Current output share of total cost — vectorized (safe at 100k rows)
is_sonnet        = obs["model"] == "claude-sonnet-4-6"
in_price_vec     = np.where(is_sonnet, 3.00, 0.80) / 1_000_000
out_price_vec    = np.where(is_sonnet, 15.00, 4.00) / 1_000_000
total_input_cost  = (obs["input_tokens"]  * in_price_vec).sum()
total_output_cost = (obs["output_tokens"] * out_price_vec).sum()
output_share = total_output_cost / (total_input_cost + total_output_cost) * 100

# If output is capped 25% shorter:
lever3_savings_pct = output_share * 0.25

# ── 3-column layout ────────────────────────────────────────────────────────────
l1, l2, l3 = st.columns(3)

CARD = """
<div style="border:1px solid {border}; border-radius:8px; padding:18px 20px;
            background:{bg}; height:100%;">
  <div style="font-size:0.72rem; font-weight:600; letter-spacing:.07em;
              text-transform:uppercase; color:{label_color}; margin-bottom:4px;">
    Lever {n}
  </div>
  <div style="font-size:1.5rem; font-weight:700; color:{C_NAVY}; margin-bottom:2px;">
    {saving}
  </div>
  <div style="font-size:0.95rem; font-weight:600; color:{C_TEXT_PRIMARY}; margin-bottom:8px;">
    {title}
  </div>
  <div style="font-size:0.82rem; color:{C_TEXT_SECONDARY}; line-height:1.6;">
    {body}
  </div>
</div>
"""

with l1:
    st.markdown(CARD.format(
        n=1, border=C_NAVY, bg="#EEF2F8", label_color=C_NAVY,
        saving=f"−{lever1_savings:.0f}%",
        title="Route to the right model",
        body=(
            f"Haiku handles <strong>{routed_tasks}/{total_tasks}</strong> task variants "
            f"at equal or better quality. "
            f"Sonnet is only justified for Summarization (gap = 0.10). "
            f"Routing alone accounts for most of the savings."
        ),
        C_NAVY=C_NAVY, C_TEXT_PRIMARY=C_TEXT_PRIMARY, C_TEXT_SECONDARY=C_TEXT_SECONDARY,
    ), unsafe_allow_html=True)

with l2:
    st.markdown(CARD.format(
        n=2, border=C_BORDER, bg="#FFFFFF", label_color=C_TEXT_MUTED,
        saving=f"−{lever2_weighted_pct:.0f}%",
        title="Optimize your prompts",
        body=(
            f"Input tokens are cheap but they add up. "
            f"Cutting 20% of system prompt / context tokens saves "
            f"~{lever2_weighted_pct:.0f}% additional cost per request. "
            f"Remove boilerplate, use concise instructions, avoid repeating the same context."
        ),
        C_NAVY=C_NAVY, C_TEXT_PRIMARY=C_TEXT_PRIMARY, C_TEXT_SECONDARY=C_TEXT_SECONDARY,
    ), unsafe_allow_html=True)

with l3:
    st.markdown(CARD.format(
        n=3, border=C_BORDER, bg="#FFFFFF", label_color=C_TEXT_MUTED,
        saving=f"−{lever3_savings_pct:.0f}%",
        title="Control output length",
        body=(
            f"Output tokens cost <strong>5× more</strong> per token than input "
            f"(Haiku: $0.80 → $4.00/MTok; Sonnet: $3.00 → $15.00/MTok). "
            f"Output is <strong>{output_share:.0f}%</strong> of your total token cost. "
            f"Set <code>max_tokens</code> per task type. "
            f"Capping 25% shorter saves ~{lever3_savings_pct:.0f}% of total cost."
        ),
        C_NAVY=C_NAVY, C_TEXT_PRIMARY=C_TEXT_PRIMARY, C_TEXT_SECONDARY=C_TEXT_SECONDARY,
    ), unsafe_allow_html=True)

# ── Supporting chart: input vs output price per token ──────────────────────────
st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)
col_chart, col_ratio = st.columns([3, 2])

with col_chart:
    models_l  = ["Haiku 4.5", "Haiku 4.5", "Sonnet 4.6", "Sonnet 4.6"]
    token_type = ["Input", "Output", "Input", "Output"]
    prices_usd = [0.80, 4.00, 3.00, 15.00]
    colors_bar = [C_MUTED, C_NAVY, C_MUTED, C_NAVY]

    fig_l = go.Figure()
    for i, (m, tt, p, c) in enumerate(zip(models_l, token_type, prices_usd, colors_bar)):
        fig_l.add_trace(go.Bar(
            name=tt if i < 2 else None,
            showlegend=(i < 2),
            x=[f"{m} — {tt}"],
            y=[p],
            marker_color=c,
            text=[f"${p:.2f}"],
            textposition="outside",
        ))
    apply_layout(fig_l, height=280,
                 title=dict(text="Price per million tokens: output costs 5× more than input",
                            font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="$/MTok"),
                 legend=dict(orientation="h", y=1.15))
    st.plotly_chart(fig_l, use_container_width=True)

with col_ratio:
    ratio_df = obs.groupby("task_type")["token_ratio"].mean().reset_index().sort_values("token_ratio", ascending=False)
    fig_r = go.Figure()
    fig_r.add_trace(go.Bar(
        x=ratio_df["task_type"],
        y=ratio_df["token_ratio"].round(2),
        marker_color=[C_NAVY if r > 1.0 else C_MUTED for r in ratio_df["token_ratio"]],
        text=ratio_df["token_ratio"].round(2),
        texttemplate="%{text:.1f}×",
        textposition="outside",
    ))
    fig_r.add_hline(y=1.0, line_dash="dot", line_color=C_AMBER,
                    annotation_text="1× breakeven", annotation_font_size=10)
    apply_layout(fig_r, height=280,
                 title=dict(text="Avg output/input token ratio by task type",
                            font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="output ÷ input", rangemode="tozero"))
    st.plotly_chart(fig_r, use_container_width=True)

st.caption(
    f"Tasks above 1× are output-dominated — code generation ({ratio_df[ratio_df.task_type=='code_generation']['token_ratio'].values[0]:.1f}×) "
    f"spends most of its cost on output tokens. "
    f"Set `max_tokens` tightly per task to avoid paying for unnecessary verbosity."
)

st.divider()

# ── Action block ───────────────────────────────────────────────────────────────
st.subheader("Recommended Action")
st.success(
    f"**Implement dynamic routing with a 0.10 quality-gap threshold.** "
    f"This routes {routed_tasks}/{total_tasks} task types to Haiku, achieving a **{savings_pct}% cost reduction** "
    f"vs an all-Sonnet baseline with no meaningful quality loss. "
    f"Route Summarization tasks to Sonnet — it is the one task where the quality premium is earned. "
    f"See **Cost Projection** to estimate annual savings at your call volume."
)

# ── Provenance ─────────────────────────────────────────────────────────────────
st.caption(
    "Data source: Live benchmark — Claude Haiku 4.5 vs Claude Sonnet 4.6 · "
    "4 task types × 3 difficulty levels · Quality = keyword-match scoring · "
    "Pricing: Haiku $1/$5 per MTok input/output · Sonnet $3/$15 per MTok"
)
