"""
3_Cost_Projection.py — How much does routing save at your call volume?
Call volumes are pulled from a Helicone property query (task_type tag).
In production, swap the sample JSON for a live Helicone or Langfuse API call.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.data_loader import load_benchmark, load_langfuse_usage
from utils.theme import MODEL_COLORS, C_NAVY, C_MUTED, C_BORDER, apply_layout

st.set_page_config(page_title="Cost Projection", layout="wide", page_icon="💰")

df         = load_benchmark()
usage, raw = load_langfuse_usage()

TASK_LABELS = {
    "classification":    "Classification",
    "simple_extraction": "Simple Extraction",
    "summary":           "Summary",
    "code_generation":   "Code Generation",
    "complex_reasoning": "Complex Reasoning",
}

st.title("How much does routing save at your call volume?")

# ── Data source banner ─────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="
        background:#F0F4FA;
        border:1px solid {C_BORDER};
        border-radius:6px;
        padding:12px 18px;
        font-size:0.83rem;
        color:#4E5B6B;
        margin-bottom:8px;
    ">
        <strong>Data source:</strong> Langfuse Observations API (open-source, self-hostable)
        &nbsp;·&nbsp; <code>GET /api/public/observations?type=GENERATION</code>
        &nbsp;·&nbsp; Grouped by: <code>metadata.task_type</code>
        &nbsp;·&nbsp; Period: {raw['period_start'][:10]} → {raw['period_end'][:10]}
        &nbsp;·&nbsp; Last synced: {raw['pulled_at'][:10]}
        &nbsp;·&nbsp; Total observations: {raw['meta']['total_observations']:,}
        <br/>
        <span style="color:#6B7788;">
        In production, tag each generation:
        <code>langfuse.generation(metadata={{"task_type": "simple_qa"}})</code>.
        Langfuse aggregates by tag automatically — this page reads the result and pre-fills call volumes.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── Avg cost per call from benchmark ──────────────────────────────────────────
haiku_df  = df[df["model_label"] == "haiku"]
sonnet_df = df[df["model_label"] == "sonnet"]

merged = haiku_df.merge(
    sonnet_df[["task_type", "difficulty", "quality_score", "cost_usd"]],
    on=["task_type", "difficulty"],
    suffixes=("_haiku", "_sonnet"),
)
merged["quality_gap"] = merged["quality_score_sonnet"] - merged["quality_score_haiku"]
merged["use_haiku"]   = merged["quality_gap"] <= 0.1
merged["routed_cost"] = merged.apply(
    lambda r: r["cost_usd_haiku"] if r["use_haiku"] else r["cost_usd_sonnet"], axis=1
)

task_costs = merged.groupby("task_type").agg(
    haiku_cost=("cost_usd_haiku",  "mean"),
    sonnet_cost=("cost_usd_sonnet", "mean"),
    routed_cost=("routed_cost",     "mean"),
).reset_index()

# ── 01: Call volume — auto-filled from Helicone ────────────────────────────────
st.subheader("01 — Monthly call volume by task type")
st.caption(
    "Pre-filled from Helicone. Adjust if your current month is not yet complete "
    "or you want to model a different scenario."
)

col_input, col_metrics = st.columns([1, 2])

volumes = {}
with col_input:
    for task in task_costs["task_type"]:
        label        = TASK_LABELS.get(task, task)
        langfuse_val = usage.get(task, {}).get("observation_count", 10_000)
        volumes[task] = st.number_input(
            f"{label} (calls/month)",
            min_value=0,
            max_value=10_000_000,
            value=int(langfuse_val),
            step=1_000,
            format="%d",
            help=f"Langfuse reported {langfuse_val:,} observations this period.",
        )

total_calls = sum(volumes.values())

# ── Compute projections ────────────────────────────────────────────────────────
rows = []
for _, r in task_costs.iterrows():
    vol = volumes.get(r["task_type"], 0)
    rows.append({
        "task":       r["task_type"],
        "volume":     vol,
        "all_haiku":  r["haiku_cost"]  * vol,
        "all_sonnet": r["sonnet_cost"] * vol,
        "routed":     r["routed_cost"] * vol,
    })

proj              = pd.DataFrame(rows)
total_haiku       = proj["all_haiku"].sum()
total_sonnet      = proj["all_sonnet"].sum()
total_routed      = proj["routed"].sum()
savings_vs_sonnet = total_sonnet - total_routed
savings_pct       = round((1 - total_routed / total_sonnet) * 100, 1) if total_sonnet > 0 else 0

with col_metrics:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total calls/month",  f"{total_calls:,}")
    m2.metric("All-Sonnet cost",     f"${total_sonnet:,.2f}", "baseline")
    m3.metric("Routed cost",         f"${total_routed:,.2f}", "with routing")
    m4.metric("Monthly savings",     f"${savings_vs_sonnet:,.2f}", f"−{savings_pct}%")

st.divider()

# ── 02: Raw Helicone response viewer ──────────────────────────────────────────
with st.expander("View raw Langfuse response (what the API actually returns)"):
    langfuse_rows = []
    for task, row in usage.items():
        langfuse_rows.append({
            "metadata.task_type":   row["metadata_task_type"],
            "observation_count":    f"{row['observation_count']:,}",
            "total_input_tokens":   f"{row['total_input_tokens']:,}",
            "total_output_tokens":  f"{row['total_output_tokens']:,}",
            "total_cost_usd":       f"${row['total_cost_usd']:.2f}",
            "avg_cost_usd":         f"${row['avg_cost_usd']:.6f}",
            "avg_latency (s)":      f"{row['avg_latency_seconds']:.3f} s",
        })
    st.dataframe(pd.DataFrame(langfuse_rows), use_container_width=True, hide_index=True)
    st.caption(
        "This is the shape of a Langfuse Observations API response after client-side groupby. "
        "In production, page through `GET /api/public/observations?type=GENERATION` "
        "and aggregate by `metadata.task_type` — or use Langfuse SDK: "
        "`langfuse.get_observations(type='GENERATION', from_start_time=...)`"
    )

st.divider()

# ── 03: Monthly cost bar chart ─────────────────────────────────────────────────
st.subheader("02 — Dynamic Routing tracks near the All-Haiku cost floor")
st.caption(
    "All-Sonnet = expensive baseline. All-Haiku = theoretical floor. "
    "Dynamic Routing (navy) gets close to the floor while protecting Summarization quality."
)

fig = go.Figure()
task_labels_list = [TASK_LABELS.get(t, t) for t in proj["task"]]

for col_name, series_name, opacity in [
    ("all_sonnet", "All Sonnet (baseline)", 0.5),
    ("all_haiku",  "All Haiku (floor)",     0.4),
    ("routed",     "Dynamic Routing",        1.0),
]:
    fig.add_trace(go.Bar(
        x=task_labels_list,
        y=proj[col_name],
        name=series_name,
        marker=dict(color=C_NAVY if opacity == 1.0 else C_MUTED, opacity=opacity),
        hovertemplate="%{x}<br>" + series_name + ": $%{y:,.2f}<extra></extra>",
    ))

apply_layout(fig, height=380,
             yaxis=dict(title="Monthly Cost (USD)"),
             xaxis=dict(title="Task Type"))
fig.update_layout(barmode="group")
st.plotly_chart(fig, use_container_width=True)
st.info(
    "**Takeaway:** Dynamic Routing (dark navy) sits close to the All-Haiku floor. "
    "The gap between All-Sonnet and Routed is the recoverable waste eliminated by routing."
)

st.divider()

# ── 04: Annual projection ──────────────────────────────────────────────────────
st.subheader("03 — Annual savings")

col_a, col_b = st.columns(2)

with col_a:
    annual_df = pd.DataFrame({
        "Strategy":    ["All Haiku", "All Sonnet", "Dynamic Routing"],
        "Monthly ($)": [total_haiku,      total_sonnet,      total_routed],
        "Annual ($)":  [total_haiku * 12, total_sonnet * 12, total_routed * 12],
    })
    st.dataframe(
        annual_df.style.format({"Monthly ($)": "${:,.2f}", "Annual ($)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.success(
        f"**Dynamic Routing saves ${savings_vs_sonnet * 12:,.0f}/year** "
        f"vs all-Sonnet — a **{savings_pct}% reduction** with no meaningful quality loss."
    )

with col_b:
    fig2 = go.Figure(go.Bar(
        x=["All Haiku", "All Sonnet", "Dynamic Routing"],
        y=[total_haiku * 12, total_sonnet * 12, total_routed * 12],
        marker_color=[C_MUTED, C_MUTED, C_NAVY],
        marker_opacity=[0.4, 0.55, 1.0],
        hovertemplate="%{x}: $%{y:,.0f}/yr<extra></extra>",
    ))
    apply_layout(fig2, height=300, yaxis=dict(title="Annual Cost (USD)"))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── 05: Scale scenarios ────────────────────────────────────────────────────────
st.subheader("04 — Savings at scale")
st.caption("Routing is a one-time engineering cost. Savings compound every month.")

scale_rows = []
for multiplier in [1, 5, 10, 50, 100]:
    scale_rows.append({
        "Scale":         f"{multiplier}× current volume",
        "Monthly calls": f"{total_calls * multiplier:,}",
        "All-Sonnet/mo": f"${total_sonnet * multiplier:,.0f}",
        "Routed/mo":     f"${total_routed * multiplier:,.0f}",
        "Savings/month": f"${savings_vs_sonnet * multiplier:,.0f}",
        "Savings/year":  f"${savings_vs_sonnet * multiplier * 12:,.0f}",
    })

st.dataframe(pd.DataFrame(scale_rows), use_container_width=True, hide_index=True)
st.info(
    f"**Takeaway:** At 100× current volume ({total_calls * 100:,} calls/month), "
    f"annual savings reach **${savings_vs_sonnet * 100 * 12:,.0f}** vs all-Sonnet. "
    "Routing logic is a one-time cost; savings scale linearly with volume."
)

# ── Provenance ─────────────────────────────────────────────────────────────────
st.caption(
    "Call volumes: Langfuse Observations API — metadata.task_type (sample data) · "
    "Cost per call: live benchmark — Claude Haiku 4.5 vs Sonnet 4.6 · "
    "Routing threshold: quality gap ≤ 0.10 → Haiku · "
    "Pricing: Haiku $1/$5 per MTok · Sonnet $3/$15 per MTok"
)
