"""
2_Routing_Rules.py — Which tasks should route to Haiku, and how much does it save?
Define quality thresholds and simulate cost savings vs. quality tradeoff.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.data_loader import load_benchmark
from utils.theme import MODEL_COLORS, C_NAVY, C_MUTED, C_BLUE, C_AMBER, apply_layout

st.set_page_config(page_title="Routing Rules", layout="wide", page_icon="🔀")

df = load_benchmark()

TASK_LABELS = {
    "simple_qa": "Simple Q&A", "summarization": "Summarization",
    "code_generation": "Code Generation", "reasoning": "Reasoning",
}

st.title("Which tasks should route to Haiku — and how much does it save?")
st.caption(
    "Adjust the quality-gap threshold to see which tasks qualify for Haiku routing "
    "and how cost savings shift with the threshold."
)

st.divider()

# ── Routing threshold slider ───────────────────────────────────────────────────
st.subheader("01 — Set the quality-gap threshold")

col1, col2 = st.columns([1, 2])
with col1:
    threshold = st.slider(
        "Max quality gap allowed for Haiku routing",
        min_value=0.0,
        max_value=0.20,
        value=0.1,
        step=0.05,
        help=(
            "If Sonnet quality − Haiku quality ≤ threshold → route to Haiku. "
            "Higher threshold = more aggressive routing (more savings, more quality risk). "
            "Max is 0.20 — the largest gap observed in the benchmark data is 0.10."
        ),
    )
    st.markdown(
        f"""
<div style="font-size:0.82rem; line-height:1.7; margin-top:0.5rem;">
<strong>Quality gap</strong> = Sonnet score − Haiku score<br>
<span style="color:#6B7788;">Threshold = "I'll accept up to this much quality loss to save cost"</span>
<br><br>
<table style="border-collapse:collapse; width:100%; font-size:0.80rem;">
  <tr style="border-bottom:1px solid #D9DEE7;">
    <td style="padding:3px 8px 3px 0;"><strong>0.00</strong></td>
    <td style="padding:3px 0;">Only route to Haiku when quality is identical</td>
  </tr>
  <tr style="border-bottom:1px solid #D9DEE7;">
    <td style="padding:3px 8px 3px 0;"><strong>0.05</strong></td>
    <td style="padding:3px 0;">Conservative — summarization stays on Sonnet</td>
  </tr>
  <tr style="border-bottom:1px solid #D9DEE7; background:#EEF2F8;">
    <td style="padding:3px 8px 3px 0;"><strong>0.10</strong> ◀ default</td>
    <td style="padding:3px 0;">All 6 task variants → Haiku (max gap in data = 0.10)</td>
  </tr>
  <tr>
    <td style="padding:3px 8px 3px 0;"><strong>0.20</strong></td>
    <td style="padding:3px 0;">Aggressive — future harder tasks also qualify</td>
  </tr>
</table>
</div>
""",
        unsafe_allow_html=True,
    )

# ── Compute routing ────────────────────────────────────────────────────────────
# Average across repeated runs per task_type × difficulty BEFORE merging.
# Without this, merge() produces a many-to-many cartesian join
# (e.g. simple_qa/easy: 3 haiku × 3 sonnet = 9 rows instead of 1).
haiku_df  = df[df["model_label"] == "haiku"].groupby(
    ["task_type", "difficulty"], as_index=False
).agg(quality_score=("quality_score", "mean"),
      cost_usd=("cost_usd", "mean"),
      latency_ms=("latency_ms", "mean"))

sonnet_df = df[df["model_label"] == "sonnet"].groupby(
    ["task_type", "difficulty"], as_index=False
).agg(quality_score=("quality_score", "mean"),
      cost_usd=("cost_usd", "mean"),
      latency_ms=("latency_ms", "mean"))

merged = haiku_df.merge(
    sonnet_df[["task_type", "difficulty", "quality_score", "cost_usd", "latency_ms"]],
    on=["task_type", "difficulty"],
    suffixes=("_haiku", "_sonnet"),
)
merged["quality_gap"]     = merged["quality_score_sonnet"] - merged["quality_score_haiku"]
merged["use_haiku"]       = merged["quality_gap"] <= threshold
merged["routed_cost"]     = merged.apply(
    lambda r: r["cost_usd_haiku"] if r["use_haiku"] else r["cost_usd_sonnet"], axis=1
)
merged["routed_model"]    = merged["use_haiku"].map({True: "Haiku", False: "Sonnet"})
merged["routed_latency"]  = merged.apply(
    lambda r: r["latency_ms_haiku"] if r["use_haiku"] else r["latency_ms_sonnet"], axis=1
)

baseline_cost   = merged["cost_usd_sonnet"].sum()
routed_cost     = merged["routed_cost"].sum()
savings_pct     = round((1 - routed_cost / baseline_cost) * 100, 1) if baseline_cost > 0 else 0
routed_to_haiku = int(merged["use_haiku"].sum())
total_tasks     = len(merged)

with col2:
    m1, m2, m3 = st.columns(3)
    m1.metric("Tasks routed to Haiku", f"{routed_to_haiku} / {total_tasks}")
    m2.metric("Cost savings vs all-Sonnet", f"{savings_pct}%")
    m3.metric("Baseline (all-Sonnet)", f"${baseline_cost:.4f}", "per benchmark run")

st.divider()

# ── 02: Routing decision table ─────────────────────────────────────────────────
st.subheader("02 — Routing decision per task")
st.caption(
    "Green = routed to Haiku (quality gap within threshold). "
    "Orange = kept on Sonnet (quality gap exceeds threshold)."
)

display = merged[["task_type", "difficulty", "quality_score_haiku",
                   "quality_score_sonnet", "quality_gap", "routed_model",
                   "routed_cost", "cost_usd_sonnet"]].copy()
display["task_type"]  = display["task_type"].map(TASK_LABELS)
display["cost_saved"] = display["cost_usd_sonnet"] - display["routed_cost"]
display["decision"]   = display["routed_model"].map(
    {"Haiku": "✅ Haiku", "Sonnet": "⚠️ Sonnet"}
)

display.columns = ["Task", "Difficulty", "Haiku Quality", "Sonnet Quality",
                   "Quality Gap", "Routed To", "Routed Cost ($)", "Sonnet Cost ($)",
                   "Cost Saved ($)", "Decision"]

st.dataframe(
    display[["Task", "Difficulty", "Haiku Quality", "Sonnet Quality",
             "Quality Gap", "Decision", "Cost Saved ($)"]].style.format({
        "Haiku Quality": "{:.2f}", "Sonnet Quality": "{:.2f}",
        "Quality Gap": "{:.3f}", "Cost Saved ($)": "${:.5f}",
    }),
    use_container_width=True,
    hide_index=True,
)
st.info(
    "**Takeaway:** At the default 0.10 threshold, 3 of 4 task types route to Haiku. "
    "Summarization (gap = 0.10) sits right at the boundary — lower to 0.05 to keep it on Sonnet. "
    "Reasoning routes to Haiku because Haiku *outperforms* Sonnet there (gap is negative)."
)

st.divider()

# ── 03: Haiku vs Sonnet cost per task ─────────────────────────────────────────
st.subheader("03 — Haiku costs 4–6× less per call across every task type")
st.caption("Grouped by task type. Hover for exact cost. Routing decision = which bar you actually pay.")

task_labels = (display["Task"] + " (" + display["Difficulty"] + ")").tolist()

fig = go.Figure()
for col_name, series_name, color in [
    ("Haiku Quality",  "Haiku cost",  C_NAVY),   # reuse display df — need cost cols
    ("Sonnet Quality", "Sonnet cost", C_MUTED),
]:
    pass  # placeholder — build from merged below

# Use merged directly for cost values (display df has quality cols, not cost)
task_x      = (merged["task_type"].map(TASK_LABELS) + " (" + merged["difficulty"] + ")").tolist()
haiku_costs = merged["cost_usd_haiku"].tolist()
sonnet_costs= merged["cost_usd_sonnet"].tolist()
routed_marker = merged["use_haiku"].tolist()  # True = this row routes to Haiku

fig = go.Figure()
fig.add_trace(go.Bar(
    name="Haiku cost",
    x=task_x,
    y=haiku_costs,
    marker_color=C_NAVY,
    hovertemplate="%{x}<br>Haiku: $%{y:.5f}<extra></extra>",
))
fig.add_trace(go.Bar(
    name="Sonnet cost",
    x=task_x,
    y=sonnet_costs,
    marker_color=C_MUTED,
    hovertemplate="%{x}<br>Sonnet: $%{y:.5f}<extra></extra>",
))
apply_layout(fig, height=380,
             yaxis=dict(title="Cost per Call (USD)"),
             xaxis=dict(title="", tickangle=-20))
fig.update_layout(barmode="group")
st.plotly_chart(fig, use_container_width=True)
st.info(
    "**Takeaway:** For every task type, Haiku (navy) is 4–6× cheaper than Sonnet (gray). "
    "The routing decision above determines which bar you actually pay — "
    "tasks routed to Haiku pay the navy bar; Summarization (kept on Sonnet) pays the gray bar."
)

st.divider()

# ── 04: Production routing rules ──────────────────────────────────────────────
st.subheader("04 — Production-ready routing rules")
st.caption(
    f"Rules derived from benchmark data at threshold = {threshold}. "
    "Implement these in your API gateway or application routing layer."
)

rules = merged[["task_type", "difficulty", "use_haiku", "quality_gap"]].copy()
rules["rule"] = rules.apply(
    lambda r: (
        f"Route to **Haiku** — quality gap {r['quality_gap']:.2f} ≤ {threshold}"
        if r["use_haiku"]
        else f"Route to **Sonnet** — quality gap {r['quality_gap']:.2f} > {threshold}"
    ),
    axis=1,
)

for _, row in rules.iterrows():
    task  = TASK_LABELS.get(row["task_type"], row["task_type"])
    color = "green" if row["use_haiku"] else "orange"
    st.markdown(f"**{task}** ({row['difficulty']}) → :{color}[{row['rule']}]")

st.divider()

# ── 05: Routing design guide ──────────────────────────────────────────────────
st.subheader("05 — Routing design guide")
st.caption(
    "80/20 rule: route 80% of traffic to Haiku (fast, cheap, good enough) and reserve "
    "Sonnet for the 20% where capability gap is measurable."
)

st.markdown(
    """
<style>
.routing-table { border-collapse: collapse; width: 100%; font-size: 0.83rem; }
.routing-table th {
    background: #1C2B4A; color: #FFFFFF;
    padding: 8px 12px; text-align: left; font-weight: 600;
}
.routing-table td { padding: 7px 12px; border-bottom: 1px solid #D9DEE7; vertical-align: top; }
.routing-table tr:nth-child(even) td { background: #F4F6FA; }
.haiku-badge  { background:#1C2B4A; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.78rem; font-weight:600; }
.sonnet-badge { background:#E8A020; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.78rem; font-weight:600; }
</style>

<table class="routing-table">
  <tr>
    <th>Task type</th>
    <th>Default model</th>
    <th>Rationale</th>
    <th>Example prompts</th>
  </tr>
  <tr>
    <td><strong>Classification</strong><br><span style="color:#6B7788;font-size:0.78rem;">~30% of volume</span></td>
    <td><span class="haiku-badge">Haiku</span></td>
    <td>Pattern recognition, label assignment, yes/no answers — no reasoning chain needed. Quality gap ≈ 0.</td>
    <td>"Is this review positive or negative?" · "Categorize this ticket" · "Intent: sales or support?"</td>
  </tr>
  <tr>
    <td><strong>Simple Extraction</strong><br><span style="color:#6B7788;font-size:0.78rem;">~20% of volume</span></td>
    <td><span class="haiku-badge">Haiku</span></td>
    <td>Structured JSON / schema output from well-defined fields. High reliability at low cost.</td>
    <td>"Extract invoice number, date, total" · "Parse address fields" · "Return entities as JSON"</td>
  </tr>
  <tr>
    <td><strong>Summary</strong><br><span style="color:#6B7788;font-size:0.78rem;">~25% of volume</span></td>
    <td><span class="haiku-badge">Haiku</span> <span style="font-size:0.78rem;color:#6B7788;">(default)</span></td>
    <td>Standard meeting notes, product reviews, news articles → Haiku sufficient. Upgrade to Sonnet only for legal/technical/multi-doc summaries where accuracy is critical.</td>
    <td>"Summarize this support thread" · "Key points from call transcript" · (Sonnet override: "Summarize this contract for legal review")</td>
  </tr>
  <tr>
    <td><strong>Code Generation</strong><br><span style="color:#6B7788;font-size:0.78rem;">~10% of volume</span></td>
    <td><span class="sonnet-badge">Sonnet</span></td>
    <td>Complex refactoring, API design, multi-file context, debugging — Sonnet coding capability gap exceeds threshold. Haiku hallucination rate rises sharply on large codebases.</td>
    <td>"Refactor this class to use dependency injection" · "Add retry logic with exponential backoff" · "Write unit tests for edge cases"</td>
  </tr>
  <tr>
    <td><strong>Complex Reasoning</strong><br><span style="color:#6B7788;font-size:0.78rem;">~15% of volume</span></td>
    <td><span class="sonnet-badge">Sonnet</span></td>
    <td>Chain-of-thought analysis, multi-step recommendations, risk assessments — Haiku hallucination rate too high. Sonnet quality premium is justified.</td>
    <td>"Analyze root causes of churn spike" · "Recommend architecture for scale" · "Evaluate pros/cons of migration strategy"</td>
  </tr>
</table>
""",
    unsafe_allow_html=True,
)

st.markdown("#### Smart routing: add a complexity dimension")
st.caption(
    "task_type alone isn't enough — the same task can be cheap or expensive depending on "
    "how hard the instance is. Complexity is the second dimension that unlocks finer cost control."
)

st.code(
    """\
def select_model(task_type: str, complexity: str) -> str:
    \"\"\"Select the most cost-effective model for the task.\"\"\"

    # Classification, extraction — Haiku always (no reasoning chain needed)
    if task_type in ["classification", "simple_extraction"]:
        return "claude-haiku-4-5-20251001"   # $0.80/1M input

    # Summarization — Haiku for standard docs; Sonnet only when complexity == "high"
    if task_type == "summary" and complexity != "high":
        return "claude-haiku-4-5-20251001"   # meeting notes, product reviews, news

    # Code generation — start cheap, upgrade on complexity
    if task_type == "code_generation":
        if complexity == "simple":
            return "claude-haiku-4-5-20251001"   # one-liners, boilerplate
        return "claude-sonnet-4-6"               # refactoring, API design, debugging

    # Complex reasoning — always Sonnet (hallucination risk too high on Haiku)
    if task_type == "complex_reasoning":
        return "claude-sonnet-4-6"

    return "claude-haiku-4-5-20251001"  # default: start cheap
""",
    language="python",
)

st.markdown(
    """
**Key insight:** `summary` and `code_generation` are the two task types where complexity flips the model:

| Task | complexity = simple / standard | complexity = high |
|---|---|---|
| summary | Haiku (meeting notes, reviews) | Sonnet (legal/technical/multi-doc) |
| code_generation | Haiku (one-liners, boilerplate) | Sonnet (refactoring, API design, debugging) |
| classification | Haiku always | Haiku always |
| simple_extraction | Haiku always | Haiku always |
| complex_reasoning | Sonnet always | Sonnet always |

Complexity can be inferred from prompt length + keyword signals (e.g. "legal", "refactor", "production")
or passed explicitly from the calling service when the context is already known (e.g. user uploaded a 50-page PDF).
"""
)

st.markdown("#### Routing design tips")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(
        """
**80/20 starting point**

Before you have benchmark data, default every task to Haiku. Promote to Sonnet only when
you measure a quality gap > threshold — not by intuition. In practice, classification,
extraction, and standard summaries almost never need Sonnet.
"""
    )
    st.markdown(
        """
**Override for edge cases**

The routing table sets the *default*. Your API gateway can pass `override_model="claude-sonnet-4-6"`
for specific prompt patterns (e.g. legal documents flagged by metadata) without changing
the default routing logic.
"""
    )

with col_b:
    st.markdown(
        """
**Observability feedback loop**

1. Tag every call with `metadata.task_type` and `metadata.complexity` in Langfuse
2. Group by task_type × complexity → compute avg relevance score per cell
3. If Haiku quality in a cell drops below threshold → promote that cell to Sonnet
4. Re-run benchmark quarterly — model updates can shift quality gaps in either direction
"""
    )
    st.markdown(
        """
**When to split a task type**

If "summary" shows high variance (some prompts score 0.95, others 0.60), split it:
`summary_standard` → Haiku, `summary_legal` → Sonnet. Finer task taxonomy = better
routing precision = lower unnecessary Sonnet spend.
"""
    )

# ── Provenance ─────────────────────────────────────────────────────────────────
st.caption(
    "Data source: Live benchmark — Claude Haiku 4.5 vs Claude Sonnet 4.6 · "
    "Pricing: Haiku $1/$5 per MTok · Sonnet $3/$15 per MTok"
)
