"""
llm_observer.py — 5-dimension LLM observability wrapper

Instruments every call through the routing pipeline and captures:

  1. Token usage    — input_tokens, output_tokens, output/input ratio
  2. Latency        — per step: classify → cache_check → api_call → evaluate
  3. Cost           — per request, per feature (task_type), per user_id
  4. Quality        — relevance score (LLM-as-judge, optional), hallucination flag (heuristic)
  5. Errors         — categorized: timeout / context_length / api_error / quality_fail / hallucination

Langfuse integration:
  - Each pipeline step is a child span via @observe()
  - ObservationRecord fields are written to span metadata
  - Groupby metadata.feature or metadata.user_id in Langfuse → per-feature / per-user cost

How to use:
    from scripts.llm_observer import observe_llm_call

    record = observe_llm_call(
        prompt="Summarize the Q3 earnings report...",
        user_id="user_42",
        feature="report_summarizer",
        evaluate_quality=True,
    )
    print(f"cost=${record.cost_usd:.6f}  relevance={record.relevance_score:.2f}  error={record.error_type.value}")

Based on:
  - instrumented_llm.py   → LLMResponse dataclass, PRICING, per-request cost
  - rag_pipeline_obs.py   → per-step @observe() pattern
  - routing_engine.py     → TaskClassifier, ModelRouter, ROUTING_TABLE
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from dotenv import load_dotenv
import anthropic

load_dotenv()

# ── Pricing (per 1M tokens, September 2026) ──────────────────────────────────
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
}

# ── Thresholds ────────────────────────────────────────────────────────────────
LATENCY_TIMEOUT_S    = 30.0   # flag as timeout if total latency exceeds this
QUALITY_PASS_SCORE   = 0.60   # relevance score below this → quality_fail error
HALLUCINATION_RATIO  = 0.15   # uncertainty marker density above this → hallucination flag

# Phrases that signal model uncertainty / hedging
UNCERTAINTY_MARKERS = [
    r"\bi (think|believe|guess|assume)\b",
    r"\b(might|may|could) be\b",
    r"\bi'?m not (sure|certain|confident)\b",
    r"\bit('s| is) (possible|likely|probably)\b",
    r"\bperhaps\b",
    r"\bapparently\b",
    r"\bseems? (like|to be)\b",
    r"\bi (don'?t|do not) (know|have) (enough|complete|full)\b",
    r"\bunable to (confirm|verify)\b",
]


# ── Error taxonomy ────────────────────────────────────────────────────────────
class ErrorType(Enum):
    NONE           = "none"
    TIMEOUT        = "timeout"          # total latency > LATENCY_TIMEOUT_S
    CONTEXT_LENGTH = "context_length"   # prompt exceeds model context window
    API_ERROR      = "api_error"        # provider returned 4xx / 5xx
    QUALITY_FAIL   = "quality_fail"     # relevance_score < QUALITY_PASS_SCORE
    HALLUCINATION  = "hallucination"    # uncertainty marker density too high


# ── Observation record — all 5 dimensions ────────────────────────────────────
@dataclass
class ObservationRecord:
    """
    One record per LLM call. Written to Langfuse span metadata so you can:
      - Filter by error_type to see failure breakdown by type / model / prompt
      - Groupby feature to get per-feature cost in Langfuse metrics
      - Groupby user_id to get per-user cost
      - Plot relevance_score distribution over time
    """

    # Identity
    request_id:  str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id:     str = "anonymous"
    feature:     str = "unset"           # e.g. "report_summarizer", "chat_support"

    # ── 1. Token usage ────────────────────────────────────────────────────────
    input_tokens:  int   = 0
    output_tokens: int   = 0
    token_ratio:   float = 0.0           # output / input — high ratio = verbose responses

    # ── 2. Latency (seconds) ─────────────────────────────────────────────────
    latency_classify:  float = 0.0       # regex classification step
    latency_cache:     float = 0.0       # cache lookup step (0 if no cache)
    latency_api:       float = 0.0       # model API round-trip
    latency_evaluate:  float = 0.0       # quality eval step (0 if skipped)
    latency_total:     float = 0.0       # wall-clock end-to-end

    # ── 3. Cost ───────────────────────────────────────────────────────────────
    cost_usd:       float = 0.0
    model:          str   = ""           # model that was called
    task_type:      str   = ""           # classified task type → used as "feature" in Langfuse
    complexity:     str   = "standard"  # simple / standard / high — second routing dimension

    # ── 4. Quality ────────────────────────────────────────────────────────────
    relevance_score:  float = -1.0       # 0.0–1.0; -1 = not evaluated
    hallucination:    bool  = False      # uncertainty marker density check

    # ── 5. Error ──────────────────────────────────────────────────────────────
    error_type:   ErrorType = ErrorType.NONE
    error_detail: str       = ""

    # Response payload
    response_text: str = ""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (
        (input_tokens  / 1_000_000) * pricing["input"] +
        (output_tokens / 1_000_000) * pricing["output"]
    )


def _detect_hallucination(text: str) -> bool:
    """
    Heuristic: count uncertainty markers as fraction of sentences.
    Flags the response if density > HALLUCINATION_RATIO.

    Not a replacement for ground-truth eval — catches hedged, low-confidence
    answers that a production system may want to filter or re-route.
    """
    text_lower = text.lower()
    sentences  = [s.strip() for s in re.split(r"[.!?]", text_lower) if s.strip()]
    if not sentences:
        return False

    flagged = sum(
        1 for s in sentences
        if any(re.search(pat, s) for pat in UNCERTAINTY_MARKERS)
    )
    return (flagged / len(sentences)) > HALLUCINATION_RATIO


def _evaluate_relevance(
    prompt: str,
    response: str,
    client: anthropic.Anthropic,
) -> float:
    """
    LLM-as-judge: ask Haiku to score how well the response answers the prompt.
    Returns 0.0–1.0. Uses Haiku to keep eval cost low (~$0.000001 per call).
    """
    eval_prompt = f"""Score how well the RESPONSE answers the QUESTION on a scale of 0 to 10.
Only respond with a single integer (0-10). No explanation.

QUESTION: {prompt[:500]}

RESPONSE: {response[:500]}

Score:"""

    try:
        eval_resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4,
            messages=[{"role": "user", "content": eval_prompt}],
        )
        raw = eval_resp.content[0].text.strip()
        score = int(re.search(r"\d+", raw).group())
        return min(max(score / 10.0, 0.0), 1.0)
    except Exception:
        return -1.0   # eval failed — don't penalise the main call


# ── Pipeline steps (each is a timed, named unit) ─────────────────────────────

def _step_classify(prompt: str) -> tuple[str, str, str, float]:
    """
    Step 1 — Task classification + complexity estimation.
    Returns (task_type_value, model_id, complexity, latency_s).
    Pure regex — no API call, typically < 1 ms.
    """
    # Inline the classifier to avoid a circular import when routing_engine
    # is imported as a sibling module. Mirror the same patterns.
    p = prompt.lower()
    t0 = time.perf_counter()

    # Default: classification (label assignment, yes/no, categorization)
    task_type = "classification"

    # 1. Code generation — strongest signal, check first
    code_patterns = [
        r"\b(write|create|generate|implement|fix|debug|refactor)\b.{0,30}\b(code|function|class|method|script|program)\b",
        r"\b(python|javascript|typescript|java|go|rust|sql)\b",
        r"```",
        r"\bdef \w+\(",
        r"\b(unit test|test case|ci/cd|api endpoint)\b",
    ]
    if any(re.search(pat, p) for pat in code_patterns):
        task_type = "code_generation"
    else:
        # 2. Complex reasoning — multi-step analysis markers
        reasoning_patterns = [
            r"\b(analyze|analyse|evaluate|assess|critique|compare)\b",
            r"\b(why|how).{0,20}\b(work|happen|cause|affect|impact)\b",
            r"\b(pros and cons|trade-?offs?|advantages and disadvantages)\b",
            r"\b(explain.{0,20}(detail|depth|thorough))\b",
            r"\b(what (would|should|could) happen if)\b",
            r"\b(root cause|risk assessment|strategic|recommendation)\b",
            r"\b(step[- ]by[- ]step|chain of thought|reasoning)\b",
        ]
        if any(re.search(pat, p) for pat in reasoning_patterns):
            task_type = "complex_reasoning"
        else:
            # 3. Simple extraction — structured output
            extraction_patterns = [
                r"\b(extract|parse|pull out|identify)\b.{0,30}\b(field|value|entity|name|date|number)\b",
                r"\b(return|output).{0,20}\b(json|csv|table|schema|structured)\b",
                r"\b(fill in|populate).{0,20}\b(form|template|field)\b",
            ]
            if any(re.search(pat, p) for pat in extraction_patterns):
                task_type = "simple_extraction"
            else:
                # 4. Summary
                summary_patterns = [
                    r"\b(summarize|summarise|summary|tldr|tl;dr)\b",
                    r"\b(key (points|takeaways|findings))\b",
                    r"\b(in (brief|short|a nutshell))\b",
                    r"\b(condense|shorten|compress)\b.{0,20}\b(text|article|document|content)\b",
                ]
                if any(re.search(pat, p) for pat in summary_patterns):
                    task_type = "summary"

    # Two-dimensional routing: task_type × complexity → model
    # Complexity is estimated from prompt length (< 30 words = simple, > 400 = high)
    words = len(p.split())
    HIGH_SIGNALS = [
        r"\b(legal|contract|compliance|regulation)\b",
        r"\b(refactor|redesign|overhaul|rewrite)\b",
        r"\b(production|enterprise|large[- ]?scale)\b",
    ]
    complexity = (
        "high"   if (words > 400 or any(re.search(pat, p) for pat in HIGH_SIGNALS))
        else "simple"   if words < 30
        else "standard"
    )

    # summary: Haiku for standard, Sonnet for high-complexity (legal/technical docs)
    # code_generation: Haiku for simple scripts, Sonnet for complex refactoring
    # classification / simple_extraction: always Haiku
    # complex_reasoning: always Sonnet
    if task_type in ("classification", "simple_extraction"):
        model = "claude-haiku-4-5-20251001"
    elif task_type == "summary":
        model = "claude-sonnet-4-6" if complexity == "high" else "claude-haiku-4-5-20251001"
    elif task_type == "code_generation":
        model = "claude-haiku-4-5-20251001" if complexity == "simple" else "claude-sonnet-4-6"
    elif task_type == "complex_reasoning":
        model = "claude-sonnet-4-6"
    else:
        model = "claude-haiku-4-5-20251001"  # default
    elapsed = time.perf_counter() - t0
    return task_type, model, complexity, elapsed


def _step_api_call(
    prompt: str,
    model: str,
    client: anthropic.Anthropic,
) -> tuple[str, int, int, float, Optional[ErrorType], str]:
    """
    Step 2 (or 3 after cache) — Model API call.
    Returns (response_text, input_tokens, output_tokens, latency_s, error_type, error_detail).
    """
    t0 = time.perf_counter()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed = time.perf_counter() - t0
        return (
            resp.content[0].text,
            resp.usage.input_tokens,
            resp.usage.output_tokens,
            elapsed,
            None,
            "",
        )
    except anthropic.BadRequestError as e:
        elapsed = time.perf_counter() - t0
        detail  = str(e)
        err     = ErrorType.CONTEXT_LENGTH if "context" in detail.lower() else ErrorType.API_ERROR
        return ("", 0, 0, elapsed, err, detail[:200])
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return ("", 0, 0, elapsed, ErrorType.API_ERROR, str(e)[:200])


def _log_to_langfuse(record: ObservationRecord) -> None:
    """
    Write all 5 observability dimensions to the current Langfuse span.
    This makes every dimension filterable/groupable in the Langfuse UI:
      - Cost by feature:   filter metadata.feature
      - Cost by user:      filter metadata.user_id
      - Error breakdown:   filter metadata.error_type
      - Quality trends:    plot metadata.relevance_score over time
    """
    try:
        from langfuse import get_client as _lf_client
        _lf_client().update_current_observation(metadata={
            # Identity
            "request_id":       record.request_id,
            "user_id":          record.user_id,
            "feature":          record.feature,

            # 1. Token usage
            "input_tokens":     record.input_tokens,
            "output_tokens":    record.output_tokens,
            "token_ratio":      round(record.token_ratio, 3),

            # 2. Latency breakdown (seconds)
            "latency_classify": round(record.latency_classify, 4),
            "latency_cache":    round(record.latency_cache, 4),
            "latency_api":      round(record.latency_api, 3),
            "latency_evaluate": round(record.latency_evaluate, 3),
            "latency_total":    round(record.latency_total, 3),

            # 3. Cost
            "cost_usd":         round(record.cost_usd, 8),
            "model":            record.model,
            "task_type":        record.task_type,
            "complexity":       record.complexity,

            # 4. Quality
            "relevance_score":  round(record.relevance_score, 3),
            "hallucination":    record.hallucination,

            # 5. Error
            "error_type":       record.error_type.value,
            "error_detail":     record.error_detail,
        })
    except Exception:
        pass   # Langfuse not configured — observability still runs locally


# ── Public entry point ────────────────────────────────────────────────────────

def observe_llm_call(
    prompt:           str,
    user_id:          str  = "anonymous",
    feature:          str  = "unset",
    evaluate_quality: bool = False,
    override_model:   Optional[str] = None,
) -> ObservationRecord:
    """
    Route a prompt through the full 5-dimension observability pipeline.

    Args:
        prompt:           The user prompt.
        user_id:          Caller identity — used for per-user cost rollup.
        feature:          Product feature name — used for per-feature cost rollup.
        evaluate_quality: If True, runs LLM-as-judge relevance scoring (adds ~0.1s, ~$0.000001).
        override_model:   Bypass routing and use a specific model (e.g. for A/B tests).

    Returns:
        ObservationRecord with all 5 dimensions populated.
    """
    wall_start = time.perf_counter()
    client     = anthropic.Anthropic()
    record     = ObservationRecord(user_id=user_id, feature=feature)

    # ── Step 1: Classify ──────────────────────────────────────────────────────
    task_type, model, complexity, lat_classify = _step_classify(prompt)
    record.task_type         = task_type
    record.complexity        = complexity
    record.model             = override_model or model
    record.latency_classify  = lat_classify

    # ── Step 2: API call ──────────────────────────────────────────────────────
    (
        response_text,
        input_tokens,
        output_tokens,
        lat_api,
        api_error,
        api_error_detail,
    ) = _step_api_call(prompt, record.model, client)

    record.response_text  = response_text
    record.input_tokens   = input_tokens
    record.output_tokens  = output_tokens
    record.latency_api    = lat_api
    record.token_ratio    = (output_tokens / input_tokens) if input_tokens else 0.0
    record.cost_usd       = _calculate_cost(record.model, input_tokens, output_tokens)

    if api_error:
        record.error_type   = api_error
        record.error_detail = api_error_detail

    # ── Step 3: Quality evaluation ────────────────────────────────────────────
    if response_text:
        # 3a. Hallucination heuristic (free — no API call)
        t0 = time.perf_counter()
        record.hallucination = _detect_hallucination(response_text)
        if record.hallucination and record.error_type == ErrorType.NONE:
            record.error_type   = ErrorType.HALLUCINATION
            record.error_detail = "High uncertainty-marker density in response"

        # 3b. LLM-as-judge relevance (optional — one cheap Haiku call)
        if evaluate_quality:
            record.relevance_score = _evaluate_relevance(prompt, response_text, client)
            if (
                record.relevance_score >= 0                        # eval succeeded
                and record.relevance_score < QUALITY_PASS_SCORE
                and record.error_type == ErrorType.NONE
            ):
                record.error_type   = ErrorType.QUALITY_FAIL
                record.error_detail = f"Relevance score {record.relevance_score:.2f} < threshold {QUALITY_PASS_SCORE}"

        record.latency_evaluate = time.perf_counter() - t0

    # ── Step 4: Timeout check ─────────────────────────────────────────────────
    record.latency_total = time.perf_counter() - wall_start
    if record.latency_total > LATENCY_TIMEOUT_S and record.error_type == ErrorType.NONE:
        record.error_type   = ErrorType.TIMEOUT
        record.error_detail = f"Total latency {record.latency_total:.1f}s > {LATENCY_TIMEOUT_S}s threshold"

    # ── Log to Langfuse ───────────────────────────────────────────────────────
    _log_to_langfuse(record)

    return record


# ── CLI demo ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    DEMO_CALLS = [
        {
            "label": "classification — expect Haiku, low cost",
            "prompt": "Is this customer message positive, negative, or neutral? 'Your support team was incredibly helpful!'",
            "user_id": "user_01",
            "feature": "intent_classifier",
            "evaluate_quality": True,
        },
        {
            "label": "simple extraction — expect Haiku",
            "prompt": "Extract the invoice number, date, and total amount as JSON: 'Invoice #INV-2025-0042, dated January 15 2025, total $4,320.00'",
            "user_id": "user_02",
            "feature": "data_extractor",
            "evaluate_quality": True,
        },
        {
            "label": "summary — expect Haiku",
            "prompt": "Summarize the key points of this text: Large language models (LLMs) are deep learning models trained on massive text corpora. They learn to predict the next token, which gives rise to emergent abilities like in-context learning, chain-of-thought reasoning, and instruction following.",
            "user_id": "user_02",
            "feature": "report_summarizer",
            "evaluate_quality": True,
        },
        {
            "label": "code generation — expect Sonnet, higher cost",
            "prompt": "Write a Python class that implements a thread-safe LRU cache with TTL expiry.",
            "user_id": "user_01",
            "feature": "code_assistant",
            "evaluate_quality": False,
        },
        {
            "label": "complex reasoning — expect Sonnet",
            "prompt": "Analyze the trade-offs between using a monolithic vs microservices architecture for an early-stage startup with 3 engineers.",
            "user_id": "user_03",
            "feature": "decision_advisor",
            "evaluate_quality": True,
        },
    ]

    print("=" * 70)
    print("LLM Observer — 5-Dimension Observability Demo  (80% Haiku / 20% Sonnet)")
    print("=" * 70)

    total_cost   = 0.0
    error_counts = {}

    for call in DEMO_CALLS:
        print(f"\n{'─' * 70}")
        print(f"  {call['label']}")
        print(f"  Prompt: {call['prompt'][:80]}...")

        r = observe_llm_call(
            prompt=call["prompt"],
            user_id=call["user_id"],
            feature=call["feature"],
            evaluate_quality=call["evaluate_quality"],
        )
        total_cost += r.cost_usd

        # 1. Token usage
        print(f"\n  ── 1. Tokens")
        print(f"     in={r.input_tokens:,}  out={r.output_tokens:,}  ratio={r.token_ratio:.2f}x")

        # 2. Latency per step
        print(f"\n  ── 2. Latency (s)")
        print(f"     classify={r.latency_classify:.4f}  api={r.latency_api:.3f}  "
              f"evaluate={r.latency_evaluate:.3f}  total={r.latency_total:.3f}")

        # 3. Cost
        print(f"\n  ── 3. Cost")
        print(f"     model={r.model}  task={r.task_type}  user={r.user_id}")
        print(f"     cost=${r.cost_usd:.8f}  (cumulative=${total_cost:.6f})")

        # 4. Quality
        rel = f"{r.relevance_score:.2f}" if r.relevance_score >= 0 else "not evaluated"
        print(f"\n  ── 4. Quality")
        print(f"     relevance={rel}  hallucination={r.hallucination}")

        # 5. Error
        print(f"\n  ── 5. Error")
        print(f"     type={r.error_type.value}  detail={r.error_detail or '—'}")

        error_counts[r.error_type.value] = error_counts.get(r.error_type.value, 0) + 1

    # Summary table
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total calls   : {len(DEMO_CALLS)}")
    print(f"  Total cost    : ${total_cost:.6f}")
    print(f"  Error counts  : {json.dumps(error_counts, indent=4)}")
    print(f"\n  Cost by feature / user → run in Langfuse:")
    print("    GET /api/public/metrics/usage?groupBy=metadata.feature")
    print("    GET /api/public/metrics/usage?groupBy=metadata.user_id")

    # Flush Langfuse
    try:
        from langfuse import get_client as _lf
        _lf().flush()
        print("\n  Langfuse: traces flushed.")
    except Exception:
        print("\n  Langfuse: not configured (set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY).")
