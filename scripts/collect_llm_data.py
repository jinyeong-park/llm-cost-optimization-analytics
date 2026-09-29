"""
collect_llm_data.py
─────────────────────────────────────────────────────────────────────
Benchmark any LLM across task types.
To add a new model: add an entry to MODELS + PRICE below.
Currently supports: Anthropic (Claude Haiku, Sonnet, Opus)
Extensible to:      OpenAI (GPT-4o, GPT-4o-mini), Google (Gemini)

Usage:
    python scripts/collect_llm_data.py
    python scripts/collect_llm_data.py --models haiku sonnet opus
    python scripts/collect_llm_data.py --tasks simple_qa reasoning
"""
import os
import time
import csv
import argparse
import anthropic
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ── Load env ───────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Model Registry ─────────────────────────────────────────────────────────────
# To add a new model: add it here + add pricing below.
# To add a new provider: implement a new caller in call_model() below.

MODELS = {
    # label        model_id
    "haiku":       "claude-haiku-4-5-20251001",
    "sonnet":      "claude-sonnet-4-6",
    # "opus":      "claude-opus-4-6",          # uncomment to include
    # "gpt4o":     "gpt-4o",                   # needs OpenAI key
    # "gpt4o_mini":"gpt-4o-mini",              # needs OpenAI key
    # "gemini_pro":"gemini-1.5-pro",           # needs Google key
}

# Price per 1M tokens (USD)
# Source: https://platform.claude.com/docs/en/about-claude/pricing (as of 2026-09-28)
PRICE = {
    "claude-haiku-4-5-20251001":  {"input": 1.00,  "output": 5.00},   # Haiku 4.5
    "claude-sonnet-4-6":          {"input": 3.00,  "output": 15.00},  # Sonnet 4.6
    "claude-opus-4-6":            {"input": 5.00,  "output": 25.00},  # Opus 4.6
    "gpt-4o":                     {"input": 5.00,  "output": 15.00},  # OpenAI GPT-4o
    "gpt-4o-mini":                {"input": 0.15,  "output": 0.60},   # OpenAI GPT-4o mini
    "gemini-1.5-pro":             {"input": 3.50,  "output": 10.50},  # Google Gemini 1.5 Pro
}

OUT = Path(__file__).parent.parent / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

# ── Task Dataset ───────────────────────────────────────────────────────────────
# To add new tasks: append to this list.
# expected = space-separated keywords that should appear in a correct answer.

TASKS = [
    # ── Simple Q&A ──────────────────────────────────────────────────────────
    {
        "task_type": "simple_qa", "difficulty": "easy",
        "prompt": "What is the capital of France?",
        "expected": "Paris",
    },
    {
        "task_type": "simple_qa", "difficulty": "easy",
        "prompt": "What does API stand for?",
        "expected": "Application Programming Interface",
    },
    {
        "task_type": "simple_qa", "difficulty": "easy",
        "prompt": "What year was the iPhone first released?",
        "expected": "2007",
    },

    # ── Summarization ────────────────────────────────────────────────────────
    {
        "task_type": "summarization", "difficulty": "medium",
        "prompt": (
            "Summarize the following in 2 sentences: "
            "Marketing Mix Modeling (MMM) is a statistical technique used by marketers "
            "to estimate the impact of various marketing tactics on sales and then forecast "
            "the impact of future sets of tactics. It is used to optimize ad spend and the "
            "marketing mix. It takes into account many variables that affect sales, such as "
            "price, distribution, media, promotions, economic conditions, and even weather."
        ),
        "expected": "statistical technique marketing impact sales",
    },
    {
        "task_type": "summarization", "difficulty": "medium",
        "prompt": (
            "Summarize in 2 sentences: "
            "Large language models (LLMs) are AI systems trained on massive text datasets "
            "using transformer architectures. They can generate human-like text, answer "
            "questions, write code, and perform many language tasks. However they have "
            "limitations including hallucinations, knowledge cutoffs, and high inference costs."
        ),
        "expected": "large language models AI text generation limitations",
    },

    # ── Code Generation ──────────────────────────────────────────────────────
    {
        "task_type": "code_generation", "difficulty": "medium",
        "prompt": (
            "Write a Python function that takes a list of numbers and returns "
            "the mean, median, and standard deviation as a dictionary."
        ),
        "expected": "def mean median std",
    },
    {
        "task_type": "code_generation", "difficulty": "hard",
        "prompt": (
            "Write a Python function that implements a simple LRU cache "
            "with get and put operations using OrderedDict."
        ),
        "expected": "def LRUCache OrderedDict get put",
    },

    # ── Reasoning ────────────────────────────────────────────────────────────
    {
        "task_type": "reasoning", "difficulty": "medium",
        "prompt": (
            "A company spends $100K on Paid Search with an average ROI of 3.0x "
            "and $20K on Podcast with a marginal ROI of 8.6x. "
            "If they shift $10K from Paid Search to Podcast, "
            "what is the estimated net weekly revenue change? Show your reasoning."
        ),
        "expected": "76000 gain positive revenue",
    },
    {
        "task_type": "reasoning", "difficulty": "hard",
        "prompt": (
            "You have a geo holdout experiment. "
            "Treatment region (email suppressed): pre 120 activations/week, exp 105/week. "
            "Control region (email live): pre 100 activations/week, exp 98/week. "
            "Calculate the Difference-in-Differences estimate and interpret the result."
        ),
        "expected": "DiD email incremental causal",
    },
    {
        "task_type": "reasoning", "difficulty": "hard",
        "prompt": (
            "Explain why multicollinearity is a problem in Marketing Mix Modeling "
            "and how Ridge regression addresses it. Be specific about what goes wrong "
            "with OLS when channels are correlated."
        ),
        "expected": "multicollinearity Ridge regression coefficients unstable",
    },
]


# ── Provider Callers ───────────────────────────────────────────────────────────
# Add a new elif block here to support a new provider.

def call_model(model_id: str, prompt: str, clients: dict) -> dict:
    """Route to the right provider based on model_id prefix."""

    if model_id.startswith("claude"):
        client = clients["anthropic"]
        start  = time.time()
        resp   = client.messages.create(
            model=model_id,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms    = round((time.time() - start) * 1000, 1)
        input_tokens  = resp.usage.input_tokens
        output_tokens = resp.usage.output_tokens
        response_text = resp.content[0].text

    elif model_id.startswith("gpt"):
        # Uncomment when OpenAI key is available
        # from openai import OpenAI
        # client = clients["openai"]
        # start  = time.time()
        # resp   = client.chat.completions.create(
        #     model=model_id,
        #     max_tokens=512,
        #     messages=[{"role": "user", "content": prompt}],
        # )
        # latency_ms    = round((time.time() - start) * 1000, 1)
        # input_tokens  = resp.usage.prompt_tokens
        # output_tokens = resp.usage.completion_tokens
        # response_text = resp.choices[0].message.content
        raise NotImplementedError("Set OPENAI_API_KEY and uncomment OpenAI caller")

    elif model_id.startswith("gemini"):
        # Uncomment when Google key is available
        raise NotImplementedError("Set GOOGLE_API_KEY and uncomment Gemini caller")

    else:
        raise ValueError(f"Unknown model_id: {model_id}")

    price_cfg = PRICE.get(model_id, {"input": 0, "output": 0})
    cost_usd  = round(
        (input_tokens  / 1_000_000) * price_cfg["input"] +
        (output_tokens / 1_000_000) * price_cfg["output"],
        6,
    )

    return {
        "response_text": response_text,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "total_tokens":  input_tokens + output_tokens,
        "latency_ms":    latency_ms,
        "cost_usd":      cost_usd,
    }


def score_quality(response_text: str, expected_keywords: str) -> float:
    keywords = [k.lower() for k in expected_keywords.split()]
    text     = response_text.lower()
    hits     = sum(1 for kw in keywords if kw in text)
    return round(hits / len(keywords), 3)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=list(MODELS.keys()),
                        help="Which model labels to run (default: all in MODELS)")
    parser.add_argument("--tasks",  nargs="+", default=None,
                        help="Filter by task_type (default: all)")
    args = parser.parse_args()

    # Filter models
    selected_models = {k: v for k, v in MODELS.items() if k in args.models}
    if not selected_models:
        print(f"No valid models. Choose from: {list(MODELS.keys())}")
        return

    # Filter tasks
    tasks = TASKS
    if args.tasks:
        tasks = [t for t in TASKS if t["task_type"] in args.tasks]

    # Init clients
    clients = {}
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")
    if anthropic_key:
        clients["anthropic"] = anthropic.Anthropic(api_key=anthropic_key)

    rows   = []
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    total  = len(tasks) * len(selected_models)
    done   = 0

    print(f"\nModels : {list(selected_models.keys())}")
    print(f"Tasks  : {len(tasks)} tasks")
    print(f"Total  : {total} API calls\n")

    for task in tasks:
        for label, model_id in selected_models.items():
            done += 1
            print(f"[{done}/{total}] {label} | {task['task_type']} ({task['difficulty']})...", end=" ", flush=True)

            try:
                result  = call_model(model_id, task["prompt"], clients)
                quality = score_quality(result["response_text"], task["expected"])

                rows.append({
                    "run_id":        run_id,
                    "model_label":   label,
                    "model_id":      model_id,
                    "task_type":     task["task_type"],
                    "difficulty":    task["difficulty"],
                    "quality_score": quality,
                    "latency_ms":    result["latency_ms"],
                    "input_tokens":  result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "total_tokens":  result["total_tokens"],
                    "cost_usd":      result["cost_usd"],
                    "response_text": result["response_text"][:300],
                })
                print(f"✓  {result['latency_ms']}ms  ${result['cost_usd']:.5f}  q={quality}")

            except Exception as e:
                print(f"✗  {e}")

            time.sleep(0.3)

    # Save
    out_path   = OUT / "llm_benchmark.csv"
    fieldnames = [
        "run_id", "model_label", "model_id", "task_type", "difficulty",
        "quality_score", "latency_ms", "input_tokens", "output_tokens",
        "total_tokens", "cost_usd", "response_text",
    ]

    # Append if file exists (so you can accumulate runs)
    file_exists = out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows → {out_path}")

    # Summary
    print(f"\n── Summary ──────────────────────────────")
    for label in selected_models:
        subset = [r for r in rows if r["model_label"] == label]
        if not subset:
            continue
        avg_cost = sum(r["cost_usd"] for r in subset) / len(subset)
        avg_q    = sum(r["quality_score"] for r in subset) / len(subset)
        avg_lat  = sum(r["latency_ms"] for r in subset) / len(subset)
        print(f"{label:12s}  cost/call=${avg_cost:.5f}  quality={avg_q:.2f}  latency={avg_lat:.0f}ms")


if __name__ == "__main__":
    main()
