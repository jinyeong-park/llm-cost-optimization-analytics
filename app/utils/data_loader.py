import pandas as pd
import numpy as np
import json
from pathlib import Path

DATA = Path(__file__).parent.parent.parent / "data" / "raw"

# Full model display names for dashboard
MODEL_DISPLAY = {
    "haiku":   "Claude Haiku 4.5",
    "sonnet":  "Claude Sonnet 4.6",
    "opus":    "Claude Opus 4.6",
    "gpt4o":   "GPT-4o",
    "gpt4o_mini": "GPT-4o mini",
    "gemini":  "Gemini 1.5 Pro",
}

# Model ID → display name fallback
MODEL_ID_DISPLAY = {
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "claude-sonnet-4-6":         "Claude Sonnet 4.6",
    "claude-opus-4-6":           "Claude Opus 4.6",
    "gpt-4o":                    "GPT-4o",
    "gpt-4o-mini":               "GPT-4o mini",
    "gemini-1.5-pro":            "Gemini 1.5 Pro",
}

def load_langfuse_usage() -> tuple:
    """
    Load usage data aggregated from the Langfuse Observations API.

    In production, this would be:
        GET /api/public/observations?type=GENERATION
            &fromStartTime=2025-01-06T00:00:00Z
            &toStartTime=2025-01-12T23:59:59Z
        → page through results, groupby metadata.task_type client-side

    Or via Python SDK:
        langfuse.get_observations(type="GENERATION", from_start_time=...)

    Langfuse observation fields used:
        metadata.task_type  — tag set at trace creation time
        usageDetails.input  — input token count
        usageDetails.output — output token count
        totalCost           — USD cost (inputCost + outputCost)
        latency             — seconds (Langfuse >= 2026-04-01 integrations)

    Returns:
        usage  — dict keyed by task_type
        raw    — full JSON for display in dashboard
    """
    path = DATA / "langfuse_usage_sample.json"
    with open(path) as f:
        raw = json.load(f)

    usage = {
        row["metadata_task_type"]: row
        for row in raw["data"]
    }
    return usage, raw


def load_observability_data(n: int = 100_000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic request-level observability data that mirrors the
    ObservationRecord output of scripts/llm_observer.py.

    In production this would be read from Langfuse Observations API:
        GET /api/public/observations?type=GENERATION
        → flatten metadata.* fields into rows

    Fields match llm_observer.ObservationRecord:
        token usage, latency per step, cost, quality, error
    """
    rng = np.random.default_rng(seed)

    # Task type distribution (realistic production mix)
    task_types = rng.choice(
        ["classification", "simple_extraction", "summary", "code_generation", "complex_reasoning"],
        size=n,
        p=[0.30, 0.20, 0.25, 0.10, 0.15],
    )

    # Model routing — complex_reasoning + code_generation → Sonnet; rest → Haiku
    sonnet_tasks = (task_types == "complex_reasoning") | (task_types == "code_generation")
    models = np.where(sonnet_tasks, "claude-sonnet-4-6", "claude-haiku-4-5-20251001")

    # Token usage — realistic distributions per task type
    token_params = {
        "classification":    (120, 30,   80, 20),   # short prompt, short label output
        "simple_extraction": (280, 60,  140, 35),   # context + schema → compact JSON
        "summary":           (900, 200, 280, 60),   # long input, moderate output
        "code_generation":   (180, 40,  450, 120),  # brief spec → large code output
        "complex_reasoning": (320, 70,  420, 90),   # detailed prompt → long CoT output
    }
    # Vectorized token sampling — draw all at once per task type
    input_tokens  = np.empty(n, dtype=int)
    output_tokens = np.empty(n, dtype=int)
    for task, (in_mu, in_sd, out_mu, out_sd) in token_params.items():
        mask = task_types == task
        input_tokens[mask]  = np.maximum(50,  rng.normal(in_mu,  in_sd,  mask.sum()).astype(int))
        output_tokens[mask] = np.maximum(20,  rng.normal(out_mu, out_sd, mask.sum()).astype(int))
    token_ratio   = output_tokens / np.maximum(input_tokens, 1)

    # Per-step latency (seconds)
    lat_classify = rng.uniform(0.00015, 0.00035, n)   # pure regex — sub-ms

    api_lat_params = {
        "classification":    (0.35, 0.08),
        "simple_extraction": (0.42, 0.10),
        "summary":           (1.60, 0.40),
        "code_generation":   (0.95, 0.22),
        "complex_reasoning": (1.40, 0.35),
    }
    lat_api = np.empty(n)
    for task, (mu, sd) in api_lat_params.items():
        mask = task_types == task
        lat_api[mask] = np.maximum(0.1, rng.normal(mu, sd, mask.sum()))

    # ~30% of calls have quality eval enabled
    eval_mask       = rng.random(n) < 0.30
    lat_evaluate    = np.where(eval_mask, rng.uniform(0.08, 0.18, n), 0.0)
    lat_total       = lat_classify + lat_api + lat_evaluate

    # Cost — exact formula from llm_observer.py
    PRICING = {
        "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
        "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    }
    input_price  = np.where(models == "claude-sonnet-4-6", 3.00, 0.80) / 1_000_000
    output_price = np.where(models == "claude-sonnet-4-6", 15.00, 4.00) / 1_000_000
    cost_usd     = input_tokens * input_price + output_tokens * output_price

    # Quality scores — only set for rows where eval ran
    rel_score_params = {
        "classification":    (0.88, 0.07),
        "simple_extraction": (0.85, 0.08),
        "summary":           (0.80, 0.10),
        "code_generation":   (0.82, 0.09),
        "complex_reasoning": (0.84, 0.08),
    }
    rel_raw = np.empty(n)
    for task, (mu, sd) in rel_score_params.items():
        mask = task_types == task
        rel_raw[mask] = np.clip(rng.normal(mu, sd, mask.sum()), 0.0, 1.0)
    relevance_score = np.where(eval_mask, rel_raw, -1.0)

    # Hallucination — 4% base rate; higher for lower-confidence tasks
    hallucination = rng.random(n) < np.where(
        task_types == "summarization", 0.06,
        np.where(task_types == "code_generation", 0.03, 0.04)
    )

    # Error assignment (mutually exclusive priority: timeout > context_length > api > quality > hallucination)
    error_type = np.full(n, "none", dtype=object)
    error_type[lat_total > 8.0]                                   = "timeout"
    error_type[(error_type == "none") & (rng.random(n) < 0.003)]  = "context_length"
    error_type[(error_type == "none") & (rng.random(n) < 0.008)]  = "api_error"
    error_type[(error_type == "none") & eval_mask
               & (relevance_score < 0.60) & (relevance_score >= 0)]  = "quality_fail"
    error_type[(error_type == "none") & hallucination]             = "hallucination"

    # Feature mapping — which product feature triggered the call
    feature_map = {
        "classification":    "intent_classifier",
        "simple_extraction": "data_extractor",
        "summary":           "report_summarizer",
        "code_generation":   "code_assistant",
        "complex_reasoning": "decision_advisor",
    }
    features = np.array([feature_map[t] for t in task_types])

    # User IDs — 10 users with uneven load (power-law-ish)
    user_ids = rng.choice(
        [f"user_{i:02d}" for i in range(1, 11)],
        size=n,
        p=[0.20, 0.18, 0.14, 0.12, 0.10, 0.08, 0.07, 0.05, 0.04, 0.02],
    )

    # Timestamps — spread over the last 7 days
    base_ts = pd.Timestamp("2025-01-06 00:00:00")
    seconds_offset = rng.integers(0, 7 * 24 * 3600, n)
    timestamps = [base_ts + pd.Timedelta(seconds=int(s)) for s in seconds_offset]

    return pd.DataFrame({
        "timestamp":      timestamps,
        "user_id":        user_ids,
        "feature":        features,
        "task_type":      task_types,
        "model":          models,
        "input_tokens":   input_tokens,
        "output_tokens":  output_tokens,
        "token_ratio":    token_ratio,
        "latency_classify": lat_classify,
        "latency_api":    lat_api,
        "latency_evaluate": lat_evaluate,
        "latency_total":  lat_total,
        "cost_usd":       cost_usd,
        "relevance_score": relevance_score,
        "hallucination":  hallucination,
        "error_type":     error_type,
    }).sort_values("timestamp").reset_index(drop=True)


def load_benchmark() -> pd.DataFrame:
    df = pd.read_csv(DATA / "llm_benchmark.csv")
    # Add full display name column
    df["model_display"] = df["model_label"].map(MODEL_DISPLAY).fillna(
        df["model_id"].map(MODEL_ID_DISPLAY)
    ).fillna(df["model_label"])
    return df
