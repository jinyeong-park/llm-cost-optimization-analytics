# 02 — Design Decisions

> Key choices made during the build — and why.

---

## Task type taxonomy

**Decision:** 5 task types — classification, simple_extraction, summary, code_generation, complex_reasoning

**Why these 5:**
The goal was to cover the realistic distribution of calls in a B2B SaaS product with LLM features,
not to be exhaustive. These 5 represent the 80%+ of production call patterns I've seen:

| Task type | Production analog | Expected % of volume |
|---|---|---|
| classification | Intent routing, ticket triage, sentiment | ~30% |
| simple_extraction | Form parsing, entity extraction, data normalization | ~20% |
| summary | Call transcripts, support threads, news digests | ~25% |
| code_generation | IDE assistants, code review, test generation | ~10% |
| complex_reasoning | Root cause analysis, strategy recommendations, audits | ~15% |

Starting with fewer (e.g., 2–3) would miss the nuance that *summary* is a split case:
standard summaries route cheap, legal/technical docs need Sonnet.

---

## Two-dimensional routing: task_type × complexity

**Decision:** Add a `complexity` dimension (simple / standard / high) on top of task_type

**Why:**
A single task type can span a wide cost range. "Summarize this" could mean a 3-sentence
meeting note (Haiku, 200 tokens) or a 50-page legal contract (Sonnet, 15,000 tokens).
Task type alone doesn't distinguish them.

Complexity adds the second dimension that makes routing precise:

```python
def select_model(task_type: str, complexity: str) -> str:
    if task_type in ["classification", "simple_extraction"]:
        return "claude-haiku-4-5-20251001"    # always cheap
    if task_type == "summary" and complexity != "high":
        return "claude-haiku-4-5-20251001"    # cheap for standard docs
    if task_type == "code_generation" and complexity == "simple":
        return "claude-haiku-4-5-20251001"    # cheap for boilerplate
    return "claude-sonnet-4-6"                # everything else
```

Complexity is auto-detected from prompt length + keyword signals (legal, refactor, enterprise)
or passed explicitly from the calling service when the context is already known.

---

## Quality threshold: 0.10

**Decision:** Default threshold = 0.10 (Sonnet quality − Haiku quality ≤ 0.10 → route to Haiku)

**Why 0.10:**
From the benchmark data, the maximum observed quality gap across all task types is 0.10 (on summary).
Setting the default at 0.10 means: "route to Haiku when Sonnet's quality advantage is at most 10 percentage
points." This is conservative — most teams would accept up to 5–8 points — but it's a safe starting point
that routes 3 of 4 task types to Haiku while keeping the one task where Sonnet earns its premium on Sonnet.

The threshold is exposed as a slider in the dashboard precisely because the right value depends on the
product's quality SLA. A customer-facing chatbot might use 0.05; an internal analytics tool might use 0.15.

---

## Observability: Langfuse

**Decision:** Use Langfuse for production observability, not a custom logging solution

**Why Langfuse:**
1. It captures token usage, latency, cost, and custom metadata (task_type, complexity) per call out of the box
2. `GET /api/public/observations?type=GENERATION` + groupby `metadata.task_type` gives exactly the
   aggregated call counts the Cost Projection page needs — no custom aggregation pipeline required
3. The `@observe()` decorator makes per-step latency tracking trivial without polluting application code
4. Open-source and self-hostable — no vendor lock-in for cost-sensitive teams

The dashboard is designed to read from a Langfuse sample response (`langfuse_usage_sample.json`),
so the Cost Projection page pre-fills call volumes automatically in production.

---

## Dashboard audience split

**Decision:** Two distinct consumers — ops team and PM/leadership

```
Langfuse dashboard        →  ops team monitors daily: errors, latency, cost by feature
This Streamlit dashboard  →  PM/leadership decides routing strategy: threshold, savings, ROI
```

This split mattered for the design of each page. The Observability page is operational
(error rates, latency P50/P95, per-user cost). The Routing Rules and Cost Projection pages
are strategic (threshold sensitivity, savings at volume, production routing rules).

---

## What I deliberately left out

| Decision | Rationale |
|---|---|
| Multi-provider comparison (OpenAI, Gemini) | Scoped to Anthropic — adding providers is a separate benchmark exercise with different auth and pricing |
| Prompt caching | Orthogonal optimization — applies after routing, not instead of it |
| Fine-tuning | Different cost/quality surface entirely; would require a separate eval framework |
| Real-time routing dashboard | Langfuse already serves this; duplicating it adds maintenance burden |
| Statistical significance tests on benchmark | With 3 runs per cell, p-values aren't meaningful — noted as a limitation |
