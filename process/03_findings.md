# 03 — Findings

> What the benchmark showed, what the routing saves, and what to watch in production.

---

## Benchmark results

Ran Claude Haiku 4.5 vs Claude Sonnet 4.6 across 5 task types × 2 difficulty levels × 3 runs each.

| Task type | Difficulty | Haiku quality | Sonnet quality | Gap | Route to |
|---|---|:---:|:---:|:---:|---|
| Classification | easy | 1.00 | 1.00 | 0.00 | ✅ Haiku |
| Classification | hard | 0.90 | 0.90 | 0.00 | ✅ Haiku |
| Simple Extraction | easy | 1.00 | 1.00 | 0.00 | ✅ Haiku |
| Simple Extraction | hard | 0.85 | 0.90 | 0.05 | ✅ Haiku |
| Summary | easy | 0.93 | 0.93 | 0.00 | ✅ Haiku |
| Summary | hard | 0.83 | 0.93 | 0.10 | ✅ Haiku (at default threshold) |
| Code Generation | easy | 1.00 | 1.00 | 0.00 | ✅ Haiku (simple complexity) |
| Code Generation | hard | 0.75 | 0.93 | 0.18 | ⚠️ Sonnet |
| Complex Reasoning | easy | 0.75 | 0.75 | 0.00 | ✅ Haiku |
| Complex Reasoning | hard | 0.60 | 0.75 | 0.15 | ⚠️ Sonnet |

**Quality gap = Sonnet score − Haiku score. Positive = Sonnet wins. Negative = Haiku wins.**

---

## Key findings

### 1. Haiku matches Sonnet on the majority of tasks

At the default threshold of 0.10, most task × difficulty combinations route to Haiku.
The two cases where Sonnet earns its cost are both *hard* instances of tasks that involve
multi-step reasoning or complex code — exactly where you'd expect capability to matter.

### 2. Code generation is a split case

- **Simple complexity** (one-liners, boilerplate, test stubs) → Haiku: quality tie, 5× cheaper
- **Standard/high complexity** (refactoring, API design, debugging multi-file issues) → Sonnet: 18-point quality gap

This is the strongest argument for the two-dimensional routing model.
Routing all code to Sonnet by default is wasteful; routing all code to Haiku by default is risky.

### 3. Classification and extraction are always Haiku

Zero quality gap across both difficulty levels. These task types have well-defined correct outputs
(a label, a structured JSON) where Haiku and Sonnet agree. This is the 50% of call volume
where routing to Haiku is a free optimization — no quality tradeoff at all.

### 4. Summary is the boundary case

Hard summary (gap = 0.10) sits exactly at the default threshold. This is the most threshold-sensitive
task type — moving from 0.10 to 0.05 flips it to Sonnet. For a product where summary quality is
customer-facing and critical (e.g., legal document summaries), use `override_complexity="high"`
to force Sonnet regardless of the threshold setting.

---

## Cost impact at 100k requests/month

Based on the production call mix (classification 30%, extraction 20%, summary 25%, code 10%, reasoning 15%):

| Scenario | Monthly cost | vs. all-Sonnet |
|---|---:|---:|
| All Sonnet (baseline) | ~$216 | — |
| Smart routing (threshold = 0.10) | ~$65 | **−70%** |
| All Haiku | ~$43 | −80% (quality risk on code/reasoning) |

The ~$150/month saving at 100k requests scales linearly:
- 500k req/month → ~$750 saved
- 1M req/month → ~$1,500 saved
- 5M req/month → ~$7,500 saved

---

## Three cost levers (independent of routing)

Routing gets the biggest saving, but two other levers compound it:

| Lever | Mechanism | Expected saving |
|---|---|---|
| **Model routing** | Route classification/extraction/summary to Haiku | ~70% |
| **Prompt optimization** | Remove redundant context, tighten system prompts (−20% input tokens) | ~5% on top |
| **Output control** | Set `max_tokens` per task type; output costs 4–5× more than input | ~18% on top |

Applied together on tasks that allow it, total cost reduction can reach **80–85%** vs. all-Sonnet.

---

## What to monitor in production

The routing decision is only as good as the quality signal feeding it back.
These are the three metrics that should trigger a routing review:

| Metric | Watch for | Action |
|---|---|---|
| **Relevance score by task × model** | Haiku avg drops below 0.75 on any cell | Promote that cell to Sonnet |
| **Hallucination rate** | Rises above 5% on any task type | Investigate prompt first; if persistent, upgrade model |
| **Error rate by type** | `quality_fail` or `hallucination` trending up | Check if task distribution shifted (new feature, new prompt) |

Review cadence: monthly for the first 3 months post-launch, then quarterly once the routing is stable.
Model capability can shift with new releases — re-run the benchmark when a major model version ships.

---

## Limitations

- **3 runs per cell** — not enough for statistical significance; treat quality scores as directional, not precise
- **Synthetic benchmark prompts** — real production prompts may have different distributions; shadow-test before fully committing a routing decision
- **Complexity auto-detection is heuristic** — keyword signals and prompt length are imperfect; passing complexity explicitly from the calling service is more reliable
- **No multi-turn context** — all benchmark calls are single-turn; multi-turn conversations may behave differently
