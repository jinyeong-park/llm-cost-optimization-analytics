# 01 — Problem Framing

> **Question:** Are we paying for model capability we're not actually using?

---

## Business context

Most LLM-powered products start simple: one model, one API key, every request goes to the same endpoint.
That works fine at prototype scale. It breaks at production scale — not in correctness, but in cost.

The pattern I kept seeing:
- Teams default to Sonnet (or GPT-4o) for everything because "it's the safest choice"
- No one checks whether the expensive model is actually better for every task type
- No system exists to route differently — so the default never gets challenged

At 100,000 requests/month across a product with 5 LLM features, this is a recoverable cost problem.
The open question is: *how much* quality do you actually give up by routing cheaper?

---

## The hypothesis

**Not all tasks need the same model.**

Some tasks (labeling, extraction, standard summarization) are well-defined enough that a smaller,
cheaper model can match a frontier model's quality. Others (complex code, multi-step reasoning)
genuinely benefit from higher capability.

If that's true, the optimal strategy is:
1. Benchmark both models on each task type
2. Measure the quality gap empirically (not by intuition)
3. Route based on gap vs. an acceptable threshold
4. Monitor quality in production to confirm the routing holds

---

## What I wanted to measure

Five dimensions that matter in production — not just accuracy:

| Dimension | Why it matters |
|---|---|
| **Token usage** | Input/output ratio determines which pricing tier hurts most |
| **Latency per step** | Routing adds classify latency; must be sub-ms to be invisible |
| **Cost by feature / user** | Chargeback and budget allocation require this breakdown |
| **Quality** | Relevance score + hallucination rate — the two things routing can degrade |
| **Error taxonomy** | Timeout / context_length / api_error / quality_fail / hallucination — needed for SLA monitoring |

---

## What I was not trying to solve

- Prompt engineering (separate optimization lever)
- Fine-tuning (different cost/quality tradeoff surface)
- Caching (orthogonal — applies after routing)
- Multi-provider routing (GPT-4o vs Claude) — scoped to Anthropic only for this benchmark

---

## Success criteria

1. Identify which task types can route to Haiku with < 0.10 quality gap
2. Quantify the cost saving at production call volume (100k requests/month)
3. Build a simulator that lets a PM or EM adjust the threshold and see the tradeoff in real time
4. Wire an observability layer so the routing decision can be monitored and adjusted over time

---

## Why this problem is worth solving

At 100k requests/month, the difference between all-Sonnet and smart routing is roughly **$1,500–2,500/month**
depending on task mix and token lengths. That compounds fast as call volume grows.

More importantly: without a routing framework, every new LLM feature defaults to the expensive model,
and no one ever goes back to check if that was the right call. The framework creates a repeatable
process for making that decision correctly the first time.
