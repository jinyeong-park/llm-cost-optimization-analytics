# token_calculator-2.py
"""
Token Cost Calculator for LLM Applications
Demonstrates real-world cost estimation
"""

import tiktoken
from dataclasses import dataclass
from typing import Dict

@dataclass
class ModelPricing:
    name: str
    input_cost_per_million: float
    output_cost_per_million: float

# Current pricing (January 2026)
MODELS = {
    "gpt-4o": ModelPricing("gpt-4o", 2.50, 10.00),
    "gpt-4o-mini": ModelPricing("gpt-4o-mini", 0.15, 0.60),
    "claude-3.5-sonnet": ModelPricing("claude-3.5-sonnet", 3.00, 15.00),
    "claude-3.5-haiku": ModelPricing("claude-3.5-haiku", 0.25, 1.25),
}

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens for a given text."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def calculate_cost(
    input_text: str,
    output_text: str,
    model: str = "gpt-4o"
) -> Dict[str, float]:
    """Calculate the cost of an LLM interaction."""

    pricing = MODELS.get(model)
    if not pricing:
        raise ValueError(f"Unknown model: {model}")

    input_tokens = count_tokens(input_text, model)
    output_tokens = count_tokens(output_text, model)

    input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_million
    output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_million

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
        "model": model,
    }

# Example: Compare costs across models
if __name__ == "__main__":
    system_prompt = """You are a helpful customer service agent.
    Be concise and professional. Only answer questions about our products."""

    user_message = "What's your return policy?"

    response = """Our return policy allows returns within 30 days of purchase.
    Items must be unused and in original packaging.
    Refunds are processed within 5-7 business days."""

    full_input = system_prompt + "\n\n" + user_message

    print("Cost Comparison Across Models")
    print("=" * 50)

    for model_name in MODELS:
        result = calculate_cost(full_input, response, model_name)
        print(f"\n{model_name}:")
        print(f"  Input tokens: {result['input_tokens']}")
        print(f"  Output tokens: {result['output_tokens']}")
        print(f"  Total cost: ${result['total_cost']:.6f}")

        # Project to 1M requests
        monthly_cost = result['total_cost'] * 1_000_000
        print(f"  Cost at 1M requests/month: ${monthly_cost:,.2f}")