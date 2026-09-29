# LLM Cost & Performance Routing Analytics

> **Dynamic model routing that cuts LLM API cost by ~70% with no meaningful quality loss.**
> Benchmarks Claude Haiku 4.5 vs Claude Sonnet 4.6 across 4 task types, identifies where each model earns its cost, and simulates routing savings at production call volumes.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude%20API-blue.svg)

---

## The problem

Most LLM-powered products send every request to the same frontier model (e.g., Sonnet) regardless of task complexity.
Sonnet costs 4–6× more than Haiku and responds 2× slower — but on 3 of 4 task types, the quality is identical.
That cost difference is recoverable waste.

**[Dashboard](https://jennypark-llm-cost-analysis.streamlit.app/)**

---

## The solution

Benchmark both models on the same tasks, measure the quality gap, and route automatically:

```
Quality gap ≤ 0.10  →  route to Haiku  (cheap, fast)
Quality gap > 0.10  →  route to Sonnet (quality premium is earned)
```

From the benchmark:

| Task            | Haiku quality | Sonnet quality |  Gap  | Route to  |
| --------------- | :-----------: | :------------: | :---: | --------- |
| Simple Q&A      |     1.00      |      1.00      | 0.00  | ✅ Haiku  |
| Code Generation |     1.00      |      1.00      | 0.00  | ✅ Haiku  |
| Reasoning       |     0.75      |      0.68      | −0.07 | ✅ Haiku  |
| Summarization   |     0.83      |      0.93      | +0.10 | ⚠️ Sonnet |

**Result: ~70% cost reduction vs all-Sonnet baseline. Haiku is faster on every task.**

---

## Dashboard pages

| Page                    | Question answered                                                   |
| ----------------------- | ------------------------------------------------------------------- |
| **Summary**             | What are the key findings and recommended action?                   |
| **Is Sonnet Worth It?** | Where does Sonnet's quality premium show up — and where doesn't it? |
| **Routing Rules**       | Which tasks route to Haiku at a given quality threshold?            |
| **Cost Projection**     | How much does routing save at my actual call volume?                |

---

## Observability stack

This project uses two complementary tools:

### Langfuse — operational monitoring

[Langfuse](https://langfuse.com) (open-source, self-hostable) captures every API call in production:

```python
langfuse.generation(
    name="llm_call",
    model="claude-haiku-4-5-20251001",
    metadata={"task_type": "simple_qa"},   # tag that drives the groupby
    usage={"input": 45, "output": 82},
)
```

Query back via `GET /api/public/observations?type=GENERATION`, group by `metadata.task_type` → get monthly call counts per task type.

**Langfuse answers:** How much did we use? What did it cost? What was the latency?

### This Streamlit dashboard — routing strategy

Uses the Langfuse aggregated counts as input to project:

- Which tasks should route where (quality benchmark)
- How much routing saves at actual production volume
- What the threshold should be

**This dashboard answers:** How should we configure routing? What's the ROI?

```
Langfuse dashboard      →  ops team monitors daily usage
This Streamlit dashboard →  PM / leadership decides routing strategy
```

The Cost Projection page reads directly from a Langfuse Observations API sample response (`data/raw/langfuse_usage_sample.json`) and pre-fills call volumes automatically.

---

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Collect benchmark data (requires ANTHROPIC_API_KEY in .env)
python scripts/collect_llm_data.py

# Launch dashboard
streamlit run app/Summary.py
```

---

## Project structure

```
0A_llm_cost_performance_routing/
├── app/
│   ├── Summary.py                      # Executive summary page
│   ├── pages/
│   │   ├── 1_Is_Sonnet_Worth_It.py     # Quality + speed + cost comparison
│   │   ├── 2_Routing_Rules.py          # Threshold simulator + routing decisions
│   │   └── 3_Cost_Projection.py        # ROI calculator (Langfuse-connected)
│   └── utils/
│       ├── data_loader.py              # Benchmark + Langfuse data loaders
│       └── theme.py                    # Centralized design tokens (colors, layout)
├── data/raw/
│   ├── llm_benchmark.csv               # Benchmark results from collect_llm_data.py
│   └── langfuse_usage_sample.json      # Sample Langfuse Observations API response
├── scripts/
│   └── collect_llm_data.py             # Benchmarks Haiku vs Sonnet via Anthropic API
├── process/
│   └── model_pricing_reference.md      # Pricing reference (updated 2026-09-28)
└── .env                                # ANTHROPIC_API_KEY (not committed)
```

---

## Pricing reference (as of 2026-09-28)

| Model             |      Input |      Output |
| ----------------- | ---------: | ----------: |
| Claude Haiku 4.5  | $1.00/MTok |  $5.00/MTok |
| Claude Sonnet 4.6 | $3.00/MTok | $15.00/MTok |

Source: console.anthropic.com/settings/billing

---

## Author
Jenny Park - 
Product Analyst / Technical PM — focused on LLM FinOps and data-driven product strategy.
