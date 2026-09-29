"""
4_Request_Health.py
Visualises the 5 dimensions captured by scripts/llm_observer.py:
  1. Token usage   — input/output ratio by task type
  2. Latency       — per-step breakdown (classify / api / evaluate)
  3. Cost          — per feature and per user
  4. Quality       — relevance scores + hallucination rate
  5. Errors        — breakdown by type, model, feature
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import load_observability_data
from utils.theme import (
    C_NAVY, C_BLUE, C_MUTED, C_GREEN, C_RED, C_AMBER,
    C_TEXT_PRIMARY, C_TEXT_SECONDARY, C_TEXT_MUTED,
    C_CANVAS, C_BORDER,
    apply_layout,
)

st.set_page_config(page_title="Observability", layout="wide", page_icon="📡")

# ── Data ─────────────────────────────────────────────────────────────────────
df = load_observability_data()
eval_df  = df[df["relevance_score"] >= 0]   # rows where quality eval ran
error_df = df[df["error_type"] != "none"]

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <h1 style="font-size:1.6rem; font-weight:700; color:{C_TEXT_PRIMARY};
               margin-bottom:0.15rem;">📡 Observability</h1>
    <p style="color:{C_TEXT_MUTED}; font-size:0.85rem; margin-bottom:1.2rem;">
        5-dimension observability from <code>llm_observer.py</code> ·
        {len(df):,} requests · 2025-01-06 → 2025-01-12
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Hero KPIs ─────────────────────────────────────────────────────────────────
total_cost     = df["cost_usd"].sum()
avg_cost       = df["cost_usd"].mean()
error_rate     = len(error_df) / len(df)
avg_relevance  = eval_df["relevance_score"].mean() if len(eval_df) else 0
halluc_rate    = df["hallucination"].mean()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Requests",   f"{len(df):,}")
k2.metric("Total Cost",       f"${total_cost:.4f}")
k3.metric("Avg Cost / Req",   f"${avg_cost:.5f}")
k4.metric("Error Rate",       f"{error_rate*100:.1f}%",  delta=f"-{error_rate*100:.1f}%" if error_rate > 0.05 else None, delta_color="inverse")
k5.metric("Avg Relevance",    f"{avg_relevance:.2f}",    help="Only evaluated requests (~30%)")

st.markdown(f"<hr style='border:none;border-top:1px solid {C_BORDER};margin:0.5rem 0 1.5rem;'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 01  TOKEN USAGE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<p style='font-size:0.75rem;font-weight:600;color:{C_TEXT_MUTED};letter-spacing:.08em;text-transform:uppercase;'>01 · Token Usage</p>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='font-size:1rem;font-weight:600;color:{C_TEXT_PRIMARY};margin:-0.3rem 0 0.8rem;'>Code generation is output-heavy (2.5×); summary and classification are input-heavy (0.3×)</p>",
    unsafe_allow_html=True,
)

tok_by_task = (
    df.groupby("task_type")
    .agg(avg_input=("input_tokens", "mean"), avg_output=("output_tokens", "mean"))
    .reset_index()
)
ratio_by_task = df.groupby("task_type")["token_ratio"].mean().reset_index()

col_a, col_b = st.columns([3, 2])

with col_a:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Avg input tokens",
        x=tok_by_task["task_type"],
        y=tok_by_task["avg_input"],
        marker_color=C_MUTED,
    ))
    fig.add_trace(go.Bar(
        name="Avg output tokens",
        x=tok_by_task["task_type"],
        y=tok_by_task["avg_output"],
        marker_color=C_NAVY,
    ))
    fig.update_layout(barmode="group")
    apply_layout(fig, height=310,
                 title=dict(text="Avg tokens per request by task type", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="Tokens"),
                 legend=dict(orientation="h", x=0.6, y=1.12, xanchor="left"))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=ratio_by_task["task_type"],
        y=ratio_by_task["token_ratio"].round(2),
        marker_color=[C_NAVY if r > 1.0 else C_MUTED for r in ratio_by_task["token_ratio"]],
        text=ratio_by_task["token_ratio"].round(2),
        textposition="outside",
    ))
    fig2.add_hline(y=1.0, line_dash="dot", line_color=C_AMBER,
                   annotation_text="ratio = 1×", annotation_font_size=10)
    apply_layout(fig2, height=310,
                 title=dict(text="Output / input ratio  (>1 = more output than input)", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="ratio", rangemode="tozero"))
    st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 02  LATENCY BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
st.markdown(
    f"<p style='font-size:0.75rem;font-weight:600;color:{C_TEXT_MUTED};letter-spacing:.08em;text-transform:uppercase;'>02 · Latency</p>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='font-size:1rem;font-weight:600;color:{C_TEXT_PRIMARY};margin:-0.3rem 0 0.8rem;'>API call accounts for >97% of latency — classify step costs &lt;1 ms</p>",
    unsafe_allow_html=True,
)

lat_by_task = (
    df.groupby("task_type")
    .agg(
        classify=("latency_classify", "mean"),
        api=("latency_api", "mean"),
        evaluate=("latency_evaluate", "mean"),
    )
    .reset_index()
)

col_c, col_d = st.columns([3, 2])

with col_c:
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="API call",      x=lat_by_task["task_type"], y=lat_by_task["api"],      marker_color=C_NAVY))
    fig3.add_trace(go.Bar(name="Quality eval",  x=lat_by_task["task_type"], y=lat_by_task["evaluate"], marker_color=C_BLUE))
    fig3.add_trace(go.Bar(name="Classify",      x=lat_by_task["task_type"], y=lat_by_task["classify"], marker_color=C_MUTED))
    fig3.update_layout(barmode="stack")
    apply_layout(fig3, height=310,
                 title=dict(text="Avg latency per step (seconds)", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="Seconds"),
                 legend=dict(orientation="h", x=0.6, y=1.12, xanchor="left"))
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    # P50 / P95 table
    pct_df = (
        df.groupby("task_type")["latency_total"]
        .quantile([0.50, 0.95])
        .unstack()
        .rename(columns={0.50: "P50 (s)", 0.95: "P95 (s)"})
        .reset_index()
    )
    pct_df["P50 (s)"] = pct_df["P50 (s)"].round(3)
    pct_df["P95 (s)"] = pct_df["P95 (s)"].round(3)
    pct_df.columns = ["Task type", "P50 (s)", "P95 (s)"]

    st.markdown(
        f"<p style='font-size:0.80rem;font-weight:600;color:{C_TEXT_SECONDARY};margin-bottom:0.4rem;'>Latency percentiles</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(pct_df, hide_index=True, use_container_width=True)

    st.markdown(
        f"""<div style='background:#EEF2F8;border-left:3px solid {C_NAVY};
            padding:0.6rem 0.8rem;border-radius:4px;margin-top:0.6rem;font-size:0.82rem;color:{C_TEXT_SECONDARY};'>
            <strong>P95</strong> = worst-case latency for 95% of requests.<br>
            Summarization P95 can hit 2.5 s — set client timeout ≥ 5 s.
        </div>""",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# 03  COST
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
st.markdown(
    f"<p style='font-size:0.75rem;font-weight:600;color:{C_TEXT_MUTED};letter-spacing:.08em;text-transform:uppercase;'>03 · Cost</p>",
    unsafe_allow_html=True,
)

cost_by_feature = (
    df.groupby("feature")
    .agg(total_cost=("cost_usd", "sum"), avg_cost=("cost_usd", "mean"), requests=("cost_usd", "count"))
    .reset_index()
    .sort_values("total_cost", ascending=False)
)
cost_by_user = (
    df.groupby("user_id")
    .agg(total_cost=("cost_usd", "sum"))
    .reset_index()
    .sort_values("total_cost", ascending=False)
    .head(10)
)

cheapest_feat = cost_by_feature.iloc[-1]["feature"]
priciest_feat = cost_by_feature.iloc[0]["feature"]
ratio_feat    = cost_by_feature.iloc[0]["avg_cost"] / cost_by_feature.iloc[-1]["avg_cost"]

st.markdown(
    f"<p style='font-size:1rem;font-weight:600;color:{C_TEXT_PRIMARY};margin:-0.3rem 0 0.8rem;'>"
    f"{priciest_feat} costs {ratio_feat:.0f}× more per request than {cheapest_feat}</p>",
    unsafe_allow_html=True,
)

col_e, col_f = st.columns(2)

with col_e:
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        x=cost_by_feature["feature"],
        y=cost_by_feature["avg_cost"].round(5),
        marker_color=[C_NAVY if f == priciest_feat else C_MUTED for f in cost_by_feature["feature"]],
        text=cost_by_feature["avg_cost"].round(5),
        texttemplate="$%{text:.5f}",
        textposition="outside",
    ))
    apply_layout(fig4, height=310,
                 title=dict(text="Avg cost per request by feature  (USD)", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="USD ($)"))
    st.plotly_chart(fig4, use_container_width=True)

with col_f:
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        x=cost_by_user["user_id"],
        y=cost_by_user["total_cost"].round(2),
        marker_color=C_NAVY,
        text=cost_by_user["total_cost"].round(2),
        texttemplate="$%{text:.2f}",
        textposition="outside",
    ))
    apply_layout(fig5, height=310,
                 title=dict(text="Total cost per user — 7-day period  (USD)", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="USD ($)"))
    st.plotly_chart(fig5, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 04  QUALITY
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
st.markdown(
    f"<p style='font-size:0.75rem;font-weight:600;color:{C_TEXT_MUTED};letter-spacing:.08em;text-transform:uppercase;'>04 · Quality</p>",
    unsafe_allow_html=True,
)

rel_by_task  = eval_df.groupby("task_type")["relevance_score"].mean().reset_index()
halluc_by_model = df.groupby("model")["hallucination"].mean().reset_index()

best_task  = rel_by_task.loc[rel_by_task["relevance_score"].idxmax(), "task_type"]
best_score = rel_by_task["relevance_score"].max()
halluc_pct = df["hallucination"].mean() * 100

st.markdown(
    f"<p style='font-size:1rem;font-weight:600;color:{C_TEXT_PRIMARY};margin:-0.3rem 0 0.8rem;'>"
    f"{best_task.replace('_',' ').title()} scores highest ({best_score:.2f}) — "
    f"{halluc_pct:.1f}% hallucination rate across all requests</p>",
    unsafe_allow_html=True,
)

col_g, col_h = st.columns([3, 2])

with col_g:
    fig6 = go.Figure()
    fig6.add_trace(go.Bar(
        x=rel_by_task["task_type"],
        y=rel_by_task["relevance_score"].round(3),
        marker_color=[C_NAVY if t == best_task else C_MUTED for t in rel_by_task["task_type"]],
        text=rel_by_task["relevance_score"].round(2),
        textposition="outside",
    ))
    fig6.add_hline(y=0.60, line_dash="dot", line_color=C_RED,
                   annotation_text="pass threshold 0.60", annotation_font_size=10)
    apply_layout(fig6, height=310,
                 title=dict(text="Avg relevance score by task type  (LLM-as-judge, 0–1)", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="Relevance (0–1)", range=[0, 1.1]))
    st.plotly_chart(fig6, use_container_width=True)

with col_h:
    MODEL_LABEL = {
        "claude-haiku-4-5-20251001": "Haiku 4.5",
        "claude-sonnet-4-6":         "Sonnet 4.6",
    }
    halluc_by_model["model_label"] = halluc_by_model["model"].map(MODEL_LABEL)

    fig7 = go.Figure()
    fig7.add_trace(go.Bar(
        x=halluc_by_model["model_label"],
        y=(halluc_by_model["hallucination"] * 100).round(2),
        marker_color=[C_NAVY, C_MUTED],
        text=(halluc_by_model["hallucination"] * 100).round(1),
        texttemplate="%{text:.1f}%",
        textposition="outside",
    ))
    apply_layout(fig7, height=310,
                 title=dict(text="Hallucination rate by model  (uncertainty-marker heuristic)", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 yaxis=dict(title="% flagged", rangemode="tozero"))
    st.plotly_chart(fig7, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 05  ERRORS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
st.markdown(
    f"<p style='font-size:0.75rem;font-weight:600;color:{C_TEXT_MUTED};letter-spacing:.08em;text-transform:uppercase;'>05 · Errors</p>",
    unsafe_allow_html=True,
)

err_counts = (
    df[df["error_type"] != "none"]
    .groupby("error_type")
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
err_by_feature = (
    df[df["error_type"] != "none"]
    .groupby("feature")["error_type"]
    .count()
    .reset_index(name="errors")
    .merge(
        df.groupby("feature").size().reset_index(name="total"),
        on="feature",
    )
)
err_by_feature["error_rate"] = err_by_feature["errors"] / err_by_feature["total"]

top_err   = err_counts.iloc[0]["error_type"] if len(err_counts) else "none"
top_feat  = err_by_feature.sort_values("error_rate", ascending=False).iloc[0]["feature"] if len(err_by_feature) else "—"

st.markdown(
    f"<p style='font-size:1rem;font-weight:600;color:{C_TEXT_PRIMARY};margin:-0.3rem 0 0.8rem;'>"
    f"{error_rate*100:.1f}% error rate — <em>{top_err.replace('_',' ')}</em> is the top error type, "
    f"concentrated in <em>{top_feat.replace('_',' ')}</em></p>",
    unsafe_allow_html=True,
)

ERR_COLORS = {
    "quality_fail":   C_AMBER,
    "hallucination":  C_AMBER,
    "api_error":      C_RED,
    "timeout":        C_RED,
    "context_length": C_BLUE,
}

col_i, col_j = st.columns([2, 3])

with col_i:
    fig8 = go.Figure()
    fig8.add_trace(go.Bar(
        x=err_counts["count"],
        y=err_counts["error_type"],
        orientation="h",
        marker_color=[ERR_COLORS.get(e, C_MUTED) for e in err_counts["error_type"]],
        text=err_counts["count"],
        textposition="outside",
    ))
    apply_layout(fig8, height=280,
                 title=dict(text="Error count by type", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 xaxis=dict(title="Count"),
                 yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig8, use_container_width=True)

with col_j:
    fig9 = go.Figure()
    err_feat_sorted = err_by_feature.sort_values("error_rate", ascending=True)
    fig9.add_trace(go.Bar(
        x=(err_feat_sorted["error_rate"] * 100).round(1),
        y=err_feat_sorted["feature"],
        orientation="h",
        marker_color=[C_RED if r > 0.06 else C_AMBER if r > 0.04 else C_MUTED
                      for r in err_feat_sorted["error_rate"]],
        text=(err_feat_sorted["error_rate"] * 100).round(1),
        texttemplate="%{text:.1f}%",
        textposition="outside",
    ))
    apply_layout(fig9, height=280,
                 title=dict(text="Error rate by feature  (red > 6%, amber > 4%)", font=dict(size=12, color=C_TEXT_SECONDARY)),
                 xaxis=dict(title="Error rate (%)"),
                 yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig9, use_container_width=True)

# Recent errors table
st.markdown(
    f"<p style='font-size:0.80rem;font-weight:600;color:{C_TEXT_SECONDARY};margin:0.8rem 0 0.3rem;'>Recent errors</p>",
    unsafe_allow_html=True,
)
recent_err = (
    df[df["error_type"] != "none"]
    .sort_values("timestamp", ascending=False)
    .head(10)
    [["timestamp", "user_id", "feature", "model", "task_type", "error_type",
      "latency_total", "cost_usd", "relevance_score"]]
    .copy()
)
recent_err["timestamp"]     = recent_err["timestamp"].dt.strftime("%m-%d %H:%M")
recent_err["latency_total"] = recent_err["latency_total"].round(2).astype(str) + " s"
recent_err["cost_usd"]      = recent_err["cost_usd"].apply(lambda x: f"${x:.5f}")
recent_err["relevance_score"] = recent_err["relevance_score"].apply(
    lambda x: f"{x:.2f}" if x >= 0 else "—"
)
recent_err["model"] = recent_err["model"].map({
    "claude-haiku-4-5-20251001": "Haiku",
    "claude-sonnet-4-6":         "Sonnet",
})
recent_err.columns = ["Time", "User", "Feature", "Model", "Task", "Error", "Latency", "Cost", "Relevance"]
st.dataframe(recent_err, hide_index=True, use_container_width=True)

# ── Provenance note ───────────────────────────────────────────────────────────
st.markdown(
    f"""<p style='font-size:0.75rem;color:{C_TEXT_MUTED};margin-top:1.5rem;'>
    Data source: <code>scripts/llm_observer.py</code> → Langfuse Observations API ·
    Production: <code>GET /api/public/observations?type=GENERATION&groupBy=metadata.feature</code>
    </p>""",
    unsafe_allow_html=True,
)
