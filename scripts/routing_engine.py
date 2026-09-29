"""
routing_engine.py — Production-ready LLM routing engine
Two-dimensional routing: task_type × complexity → model selection.

How this connects to the dashboard:
  1. Every API call gets tagged: langfuse.update_current_span(metadata={"task_type": ..., "complexity": ...})
  2. Langfuse aggregates call counts by metadata.task_type
  3. Cost Projection page reads that aggregation → pre-fills call volumes automatically

Routing philosophy:
  - Two dimensions: task_type (what) × complexity (how hard) → model
  - Classification / extraction: always Haiku — complexity doesn't change the answer
  - Summary: Haiku for standard docs; Sonnet only when complexity == "high" (legal, technical, multi-doc)
  - Code: Haiku for simple scripts; Sonnet for complex refactoring / API design / debugging
  - Complex reasoning: always Sonnet — hallucination risk too high on Haiku regardless of complexity
  - Default when uncertain: Haiku (start cheap, promote on evidence)

Based on: llm-observability-cost-management/smart_routing.py
Adapted for: Claude Haiku 4.5 vs Claude Sonnet 4.6, 5 task types,
             benchmark-derived routing thresholds, and complexity dimension.
"""

import re
from enum import Enum
from typing import Optional
from dotenv import load_dotenv
import anthropic

load_dotenv()

# ── Task types ────────────────────────────────────────────────────────────────
class TaskType(Enum):
    CLASSIFICATION    = "classification"
    SIMPLE_EXTRACTION = "simple_extraction"
    SUMMARY           = "summary"
    CODE_GENERATION   = "code_generation"
    COMPLEX_REASONING = "complex_reasoning"


# ── Complexity levels ─────────────────────────────────────────────────────────
class Complexity(Enum):
    SIMPLE   = "simple"    # short prompt, single-step, clear answer
    STANDARD = "standard"  # moderate length, multi-field, typical production call
    HIGH     = "high"      # long context, multi-doc, legal/technical, ambiguous


# ── Smart routing: task_type × complexity → model ─────────────────────────────
#
# Key insight from the image: complexity is the second dimension that unlocks
# finer-grained cost control — especially for summary and code_generation,
# where a "simple" version routes cheap but a "high" version needs Sonnet.
#
QUALITY_THRESHOLD = 0.10

def select_model(task_type: TaskType, complexity: Complexity) -> str:
    """Select the most cost-effective model for the task.

    Mirrors the smart_routing.py pattern from the reference implementation,
    adapted for Haiku 4.5 / Sonnet 4.6 and our 5 task types.

    Pricing reference (per 1M tokens):
        Haiku  4.5:   $0.80 input / $4.00 output
        Sonnet 4.6:   $3.00 input / $15.00 output
    """
    # Classification, extraction — Haiku always (pattern recognition, no reasoning chain)
    if task_type in (TaskType.CLASSIFICATION, TaskType.SIMPLE_EXTRACTION):
        return "claude-haiku-4-5-20251001"   # $0.80/1M input

    # Summarization — Haiku for standard docs; Sonnet only when complexity is high
    if task_type == TaskType.SUMMARY:
        if complexity != Complexity.HIGH:
            return "claude-haiku-4-5-20251001"   # meeting notes, product reviews, news
        return "claude-sonnet-4-6"               # legal/technical/multi-doc — accuracy critical

    # Code generation — start cheap, upgrade on complexity
    if task_type == TaskType.CODE_GENERATION:
        if complexity == Complexity.SIMPLE:
            return "claude-haiku-4-5-20251001"   # one-liners, simple scripts, boilerplate
        return "claude-sonnet-4-6"               # complex refactoring, API design, debugging

    # Complex reasoning — always Sonnet (Haiku hallucination rate too high)
    if task_type == TaskType.COMPLEX_REASONING:
        return "claude-sonnet-4-6"

    # Default: Haiku (start cheap, promote on evidence)
    return "claude-haiku-4-5-20251001"


ROUTING_REASON = {
    (TaskType.CLASSIFICATION,    Complexity.SIMPLE):   "label/yes-no — Haiku, quality tie",
    (TaskType.CLASSIFICATION,    Complexity.STANDARD): "label/yes-no — Haiku, quality tie",
    (TaskType.CLASSIFICATION,    Complexity.HIGH):     "label/yes-no — Haiku, quality tie",
    (TaskType.SIMPLE_EXTRACTION, Complexity.SIMPLE):   "structured output — Haiku, quality tie",
    (TaskType.SIMPLE_EXTRACTION, Complexity.STANDARD): "structured output — Haiku, quality tie",
    (TaskType.SIMPLE_EXTRACTION, Complexity.HIGH):     "structured output — Haiku, quality tie",
    (TaskType.SUMMARY,           Complexity.SIMPLE):   "standard summary — Haiku, gap ≤ threshold",
    (TaskType.SUMMARY,           Complexity.STANDARD): "standard summary — Haiku, gap ≤ threshold",
    (TaskType.SUMMARY,           Complexity.HIGH):     "legal/technical doc — Sonnet, accuracy critical",
    (TaskType.CODE_GENERATION,   Complexity.SIMPLE):   "simple script — Haiku, boilerplate/one-liners",
    (TaskType.CODE_GENERATION,   Complexity.STANDARD): "complex code — Sonnet, capability gap > threshold",
    (TaskType.CODE_GENERATION,   Complexity.HIGH):     "complex code — Sonnet, capability gap > threshold",
    (TaskType.COMPLEX_REASONING, Complexity.SIMPLE):   "reasoning — Sonnet, Haiku hallucination risk",
    (TaskType.COMPLEX_REASONING, Complexity.STANDARD): "reasoning — Sonnet, Haiku hallucination risk",
    (TaskType.COMPLEX_REASONING, Complexity.HIGH):     "reasoning — Sonnet, Haiku hallucination risk",
}


# ── Task classifier — regex-based, < 1 ms ─────────────────────────────────────
class TaskClassifier:
    """
    Classify a prompt into one of 5 task types using regex patterns.
    Priority order (most specific → most general):
      1. code_generation   — language names, code blocks
      2. complex_reasoning — analytical verbs, multi-step markers
      3. simple_extraction — field/schema extraction signals
      4. summary           — summarization keywords
      5. classification    — default (label, yes/no, categorization)
    """

    def classify(self, prompt: str) -> TaskType:
        p = prompt.lower()

        code_patterns = [
            r"\b(write|create|generate|implement|fix|debug|refactor)\b.{0,30}\b(code|function|class|method|script|program)\b",
            r"\b(python|javascript|typescript|java|go|rust|sql)\b",
            r"```",
            r"\bdef \w+\(",
            r"\b(unit test|test case|ci/cd|api endpoint)\b",
        ]
        if any(re.search(pat, p) for pat in code_patterns):
            return TaskType.CODE_GENERATION

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
            return TaskType.COMPLEX_REASONING

        extraction_patterns = [
            r"\b(extract|parse|pull out|identify)\b.{0,30}\b(field|value|entity|name|date|number)\b",
            r"\b(return|output).{0,20}\b(json|csv|table|schema|structured)\b",
            r"\b(fill in|populate).{0,20}\b(form|template|field)\b",
        ]
        if any(re.search(pat, p) for pat in extraction_patterns):
            return TaskType.SIMPLE_EXTRACTION

        summary_patterns = [
            r"\b(summarize|summarise|summary|tldr|tl;dr)\b",
            r"\b(key (points|takeaways|findings))\b",
            r"\b(in (brief|short|a nutshell))\b",
            r"\b(condense|shorten|compress)\b.{0,20}\b(text|article|document|content)\b",
        ]
        if any(re.search(pat, p) for pat in summary_patterns):
            return TaskType.SUMMARY

        return TaskType.CLASSIFICATION


# ── Complexity classifier — heuristic, < 1 ms ─────────────────────────────────
class ComplexityClassifier:
    """
    Estimate prompt complexity from lexical signals and length.
    Returns Complexity.SIMPLE / STANDARD / HIGH.

    In production: replace with a lightweight meta-classifier or pass
    complexity explicitly from the calling service (e.g. via metadata
    set when the user selects "advanced mode" or uploads a document).
    """

    # Keywords that signal high-complexity work
    HIGH_SIGNALS = [
        r"\b(legal|contract|compliance|regulation|liability)\b",
        r"\b(technical spec|architecture|system design|migration)\b",
        r"\b(multi[- ]?doc|multiple (documents?|files?|sources?))\b",
        r"\b(production|enterprise|large[- ]?scale|high[- ]?stakes)\b",
        r"\b(refactor|redesign|overhaul|rewrite)\b",
        r"\b(security|audit|penetration|vulnerability)\b",
    ]

    # Keywords that signal simple / boilerplate work
    SIMPLE_SIGNALS = [
        r"\b(one[- ]?liner|simple|basic|quick|short|small)\b",
        r"\b(hello world|example|demo|template|boilerplate)\b",
        r"\byes or no\b",
        r"\b(single|just one|only one)\b.{0,20}\b(field|step|sentence|word|label)\b",
    ]

    def classify(self, prompt: str) -> Complexity:
        p = prompt.lower()
        words = len(p.split())

        if any(re.search(pat, p) for pat in self.HIGH_SIGNALS) or words > 400:
            return Complexity.HIGH

        if any(re.search(pat, p) for pat in self.SIMPLE_SIGNALS) or words < 30:
            return Complexity.SIMPLE

        return Complexity.STANDARD


# ── Router ─────────────────────────────────────────────────────────────────────
class ModelRouter:
    """
    Two-dimensional routing: task_type × complexity → model.

    Design tip: wrap every feature call in observe_llm_call() from llm_observer.py
    so Langfuse quality scores flow back into your threshold review cycle.
    After 30 days, query:
        SELECT task_type, complexity, AVG(relevance_score)
        FROM observations GROUP BY 1, 2
    and promote any cell where Haiku's avg score < QUALITY_THRESHOLD to Sonnet.
    """

    def __init__(self, quality_threshold: float = QUALITY_THRESHOLD):
        self.task_classifier       = TaskClassifier()
        self.complexity_classifier = ComplexityClassifier()
        self.threshold             = quality_threshold
        self.client                = anthropic.Anthropic()

    def route(
        self,
        prompt: str,
        override_model:      Optional[str]        = None,
        override_complexity: Optional[Complexity]  = None,
    ) -> tuple[str, TaskType, Complexity]:
        """
        Returns (model_id, task_type, complexity).
        Pass override_model to bypass routing (A/B tests, feature flags).
        Pass override_complexity to inject complexity from caller metadata
        (e.g. the UI knows the user uploaded a 50-page PDF → HIGH).
        """
        task_type  = self.task_classifier.classify(prompt)
        complexity = override_complexity or self.complexity_classifier.classify(prompt)

        if override_model:
            return override_model, task_type, complexity

        model = select_model(task_type, complexity)
        return model, task_type, complexity

    def call(
        self,
        prompt: str,
        override_model:      Optional[str]       = None,
        override_complexity: Optional[Complexity] = None,
    ) -> dict:
        """Route and call the API. Returns response dict with routing metadata."""
        model, task_type, complexity = self.route(
            prompt, override_model, override_complexity
        )

        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        key    = (task_type, complexity)
        reason = ROUTING_REASON.get(key, f"{task_type.value}/{complexity.value}")

        result = {
            "text":           response.content[0].text,
            "model":          model,
            "task_type":      task_type.value,
            "complexity":     complexity.value,
            "routing_reason": reason,
            "input_tokens":   response.usage.input_tokens,
            "output_tokens":  response.usage.output_tokens,
        }

        _log_to_langfuse(result)
        return result


# ── Langfuse integration ───────────────────────────────────────────────────────
def _log_to_langfuse(result: dict):
    """
    Tag the current Langfuse span with task_type, complexity, and routing decision.
    Both dimensions become filterable in Langfuse:
      groupby metadata.task_type  → cost by task
      groupby metadata.complexity → cost by complexity tier
    """
    try:
        from langfuse import get_client
        langfuse = get_client()
        langfuse.update_current_observation(
            metadata={
                "task_type":      result["task_type"],
                "complexity":     result["complexity"],
                "routed_model":   result["model"],
                "routing_reason": result["routing_reason"],
            }
        )
    except Exception:
        pass  # Langfuse not configured — routing still works without it


# ── CLI demo ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    router = ModelRouter()

    test_cases = [
        # (prompt, expected_task, expected_complexity, expected_model)
        (
            "Is this customer message positive, negative, or neutral?",
            "classification / standard → Haiku",
        ),
        (
            "Extract the invoice number, date, and total amount as JSON.",
            "simple_extraction / standard → Haiku",
        ),
        (
            "Summarize the key findings from this Q3 earnings report.",
            "summary / standard → Haiku",
        ),
        (
            "Summarize this 80-page legal contract and flag compliance risks.",
            "summary / HIGH → Sonnet  (legal doc upgrade)",
        ),
        (
            "Write a quick Python one-liner to flatten a nested list.",
            "code_generation / SIMPLE → Haiku",
        ),
        (
            "Refactor this production authentication service to use dependency injection and add retry logic.",
            "code_generation / HIGH → Sonnet  (complex refactor)",
        ),
        (
            "Analyze the root cause of the churn spike in our enterprise segment last quarter.",
            "complex_reasoning / standard → Sonnet",
        ),
    ]

    print("=" * 70)
    print("Smart Routing Demo  (task_type × complexity → model)")
    print(f"Quality threshold: {QUALITY_THRESHOLD}")
    print("=" * 70)

    for prompt, expected in test_cases:
        model, task_type, complexity = router.route(prompt)
        key    = (task_type, complexity)
        reason = ROUTING_REASON.get(key, "—")
        print(f"\nPrompt     : {prompt[:68]}...")
        print(f"Task       : {task_type.value}")
        print(f"Complexity : {complexity.value}")
        print(f"Model      : {model}")
        print(f"Reason     : {reason}")
        print(f"Expected   : {expected}")
