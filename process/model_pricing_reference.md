# LLM Model Pricing Reference

> Source: https://platform.claude.com/docs/en/about-claude/pricing
> Last updated: 2026-09-28
> Unit: USD per 1M tokens (MTok)

---

## Anthropic Claude (Direct API)

| Model | Input ($/MTok) | Output ($/MTok) | Notes |
|---|---|---|---|
| Claude Haiku 4.5 | $1.00 | $5.00 | Fastest, cheapest |
| Claude Sonnet 4.6 | $3.00 | $15.00 | Balanced |
| Claude Opus 4.6 | $5.00 | $25.00 | Most capable |
| Claude Haiku 3.5 *(retired)* | $0.80 | $4.00 | Bedrock/GCP only |
| Claude Opus 4.1 *(retired)* | $15.00 | $75.00 | Bedrock/GCP only |

**Batch API (50% discount):**
| Model | Batch Input | Batch Output |
|---|---|---|
| Claude Haiku 4.5 | $0.50 | $2.50 |
| Claude Sonnet 4.6 | $1.50 | $7.50 |
| Claude Opus 4.6 | $2.50 | $12.50 |

**Prompt Caching multipliers:**
- 5-min cache write: 1.25x base input price
- 1-hour cache write: 2x base input price
- Cache read (hit): 0.1x base input price

---

## OpenAI (for future comparison)

| Model | Input ($/MTok) | Output ($/MTok) |
|---|---|---|
| GPT-4o | $5.00 | $15.00 |
| GPT-4o mini | $0.15 | $0.60 |

> Source: openai.com/api/pricing

---

## Google Gemini (for future comparison)

| Model | Input ($/MTok) | Output ($/MTok) |
|---|---|---|
| Gemini 1.5 Pro | $3.50 | $10.50 |
| Gemini 1.5 Flash | $0.075 | $0.30 |

> Source: ai.google.dev/pricing

---

## Cost Optimization Notes

1. **Use appropriate models**: Haiku for simple tasks, Sonnet for most production workloads, Opus for complex reasoning
2. **Batch API**: 50% discount for non-time-sensitive tasks
3. **Prompt caching**: Cache read = 10% of input price → big savings on repeated context
4. **Routing strategy**: Route simple tasks to Haiku → significant cost reduction with minimal quality loss

---

## How to Update This File

When pricing changes, update:
1. This file with new prices and date
2. `scripts/collect_llm_data.py` → `PRICE` dictionary
3. Note the date of change

Pricing pages:
- Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
- OpenAI: https://openai.com/api/pricing
- Google: https://ai.google.dev/pricing
