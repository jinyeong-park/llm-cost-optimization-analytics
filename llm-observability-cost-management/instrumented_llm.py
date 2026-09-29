# instrumented_llm.py
"""
Production-Ready LLM Wrapper with Observability
Use this as a starting point for your applications

Updated for Langfuse Python SDK v3 (Decorator-based API)
"""

from anthropic import Anthropic
from openai import OpenAI
from langfuse import observe, Langfuse
from dotenv import load_dotenv
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

load_dotenv()

# Initialize clients
anthropic_client = Anthropic()
openai_client = OpenAI()
langfuse = Langfuse()


@dataclass
class LLMResponse:
    """Structured response from LLM calls."""

    content: str
    input_tokens: int
    output_tokens: int
    model: str
    duration_ms: float
    cost: float


# Token pricing (per 1M tokens) - Update as needed
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on token usage."""
    pricing = PRICING.get(model, {"input": 0, "output": 0})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


@observe()
def call_claude(
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    system: Optional[str] = None,
    max_tokens: int = 1024,
    metadata: Optional[Dict[str, Any]] = None,
) -> LLMResponse:
    """
    Call Claude with full observability.

    The @observe decorator automatically:
    - Creates a span in the trace
    - Captures timing
    - Nests properly when called from other @observe functions
    """

    start = time.time()

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = anthropic_client.messages.create(**kwargs)

    duration_ms = (time.time() - start) * 1000
    cost = calculate_cost(
        model, response.usage.input_tokens, response.usage.output_tokens
    )

    # Update current span with model-specific info using v3 API
    langfuse.update_current_span(
        metadata={
            **(metadata or {}),
            "model": model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "duration_ms": duration_ms,
            "stop_reason": response.stop_reason,
            "cost": cost,
        },
    )

    return LLMResponse(
        content=response.content[0].text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=model,
        duration_ms=duration_ms,
        cost=cost,
    )


@observe()
def call_openai(
    prompt: str,
    model: str = "gpt-4o-mini",
    system: Optional[str] = None,
    max_tokens: int = 1024,
    metadata: Optional[Dict[str, Any]] = None,
) -> LLMResponse:
    """Call OpenAI with full observability."""

    start = time.time()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = openai_client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )

    duration_ms = (time.time() - start) * 1000

    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost = calculate_cost(model, input_tokens, output_tokens)

    # Update current span with model-specific info using v3 API
    langfuse.update_current_span(
        metadata={
            **(metadata or {}),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "cost": cost,
        },
    )

    return LLMResponse(
        content=response.choices[0].message.content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
        duration_ms=duration_ms,
        cost=cost,
    )


@observe()
def compare_models(prompt: str) -> dict:
    """
    Compare responses from Claude and OpenAI for the same prompt.
    Each call becomes a child span in the trace.
    """
    claude_response = call_claude(prompt)
    openai_response = call_openai(prompt)

    langfuse.update_current_span(
        metadata={"comparison": True},
    )

    return {
        "claude": claude_response,
        "openai": openai_response,
    }


# Example usage
if __name__ == "__main__":
    # Simple call - creates a trace with one span
    # response = call_claude("What is observability in 2 sentences?")

    response = compare_models("Explain the theory of relativity in simple terms.")

    # print(f"Response: {response.content}")
    print(f"Response: {response}")
    print(
        f"Tokens: {response.claude.input_tokens} in, {response.claude.output_tokens} out"
    )
    print(f"Cost: ${response.claude.cost:.6f}")
    print(f"Duration: {response.claude.duration_ms:.0f}ms")

    # IMPORTANT: Always flush in short-lived scripts to ensure data is sent
    langfuse.flush()
