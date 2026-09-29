# Token Cost Calculator - Analysis & Documentation

## Script Results

When running `token_calculator-2.py`, here are the actual results for a simple customer service interaction:

### Cost Comparison Table

| Model | Input Tokens | Output Tokens | Cost per Request | Monthly Cost @ 1M Requests |
|-------|-------------|---------------|------------------|---------------------------|
| gpt-4o | 26 | 35 | $0.000415 | $415.00 |
| gpt-4o-mini | 26 | 35 | $0.000025 | $24.90 |
| claude-3.5-sonnet | 27 | 35 | $0.000606 | $606.00 |
| claude-3.5-haiku | 27 | 35 | $0.000050 | $50.50 |

### What These Results Mean

1. **Model choice dramatically impacts costs** - The difference between the cheapest (GPT-4o-mini at $24.90/month) and most expensive (Claude 3.5 Sonnet at $606/month) is **24x** for the exact same task.

2. **"Mini" and "Haiku" models are significantly cheaper** - These smaller, faster models cost 17-24x less than their larger counterparts while often providing sufficient quality for simple tasks like customer service responses.

3. **Output tokens are more expensive than input tokens** - Across all models, output pricing is 4-5x higher than input pricing. This means verbose responses cost more than long prompts.

4. **Token counts vary slightly by model** - Claude models show 27 input tokens vs 26 for GPT models because the script falls back to a generic tokenizer for Claude (since tiktoken is OpenAI's tokenizer).

---

## Script Breakdown

### 1. Imports and Data Classes (Lines 1-15)

```python
import tiktoken
from dataclasses import dataclass
from typing import Dict

@dataclass
class ModelPricing:
    name: str
    input_cost_per_million: float
    output_cost_per_million: float
```

**What it does:**
- `tiktoken` - OpenAI's fast tokenizer library for counting tokens
- `@dataclass` - Python's built-in decorator for creating simple data containers
- `ModelPricing` - A data structure holding model name and pricing (input/output costs per million tokens)

---

### 2. Model Pricing Configuration (Lines 17-23)

```python
MODELS = {
    "gpt-4o": ModelPricing("gpt-4o", 2.50, 10.00),
    "gpt-4o-mini": ModelPricing("gpt-4o-mini", 0.15, 0.60),
    "claude-3.5-sonnet": ModelPricing("claude-3.5-sonnet", 3.00, 15.00),
    "claude-3.5-haiku": ModelPricing("claude-3.5-haiku", 0.25, 1.25),
}
```

**What it does:**
- Defines a dictionary of supported models with their current pricing
- Prices are in USD per million tokens
- Example: GPT-4o costs $2.50 per million input tokens and $10.00 per million output tokens

**Pricing Breakdown:**

| Model | Input ($/M tokens) | Output ($/M tokens) | Output/Input Ratio |
|-------|-------------------|--------------------|--------------------|
| gpt-4o | $2.50 | $10.00 | 4x |
| gpt-4o-mini | $0.15 | $0.60 | 4x |
| claude-3.5-sonnet | $3.00 | $15.00 | 5x |
| claude-3.5-haiku | $0.25 | $1.25 | 5x |

---

### 3. Token Counting Function (Lines 25-31)

```python
def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens for a given text."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))
```

**What it does:**
- Takes a text string and model name as input
- Tries to get the specific tokenizer for that model
- Falls back to `cl100k_base` encoding if the model isn't recognized (this is why Claude models show slightly different token counts)
- Returns the number of tokens in the text

**Why tokens matter:**
- LLMs don't process text character-by-character; they use tokens
- A token is roughly 4 characters or 0.75 words on average
- "Hello, world!" = 4 tokens
- Longer/rarer words may be split into multiple tokens

---

### 4. Cost Calculation Function (Lines 33-58)

```python
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
```

**What it does:**
1. Looks up the pricing for the specified model
2. Counts tokens in both input (prompt) and output (response)
3. Calculates cost using the formula: `(tokens / 1,000,000) × price_per_million`
4. Returns a dictionary with all the metrics

**Cost Formula Example (GPT-4o):**
- Input: 26 tokens × ($2.50 / 1,000,000) = $0.000065
- Output: 35 tokens × ($10.00 / 1,000,000) = $0.000350
- Total: $0.000415

---

### 5. Main Execution Block (Lines 60-85)

```python
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
```

**What it does:**
1. Sets up a sample customer service scenario with:
   - A system prompt (instructions for the AI)
   - A user message (the customer's question)
   - A simulated response (what the AI would reply)

2. Loops through all defined models and:
   - Calculates the cost for this interaction
   - Displays token counts and per-request cost
   - Projects the cost to 1 million requests per month

---

## Key Insights for LLM Cost Optimization

### 1. Choose the Right Model for the Task
- **Simple tasks** (classification, extraction, simple Q&A): Use mini/haiku models
- **Complex tasks** (reasoning, coding, nuanced writing): Use full models
- **Savings potential**: 17-24x cost reduction for appropriate tasks

### 2. Optimize Your Prompts
- Shorter system prompts = fewer input tokens = lower costs
- Avoid repetitive instructions
- Use concise language

### 3. Control Output Length
- Output tokens cost 4-5x more than input tokens
- Set max_tokens limits where appropriate
- Ask for concise responses in your prompts

### 4. Monitor and Project Costs
- Track token usage in production
- Project costs before scaling
- A $0.0004 request becomes $400/month at 1M requests

### 5. Consider Caching
- Cache responses for common queries
- Use semantic caching for similar questions
- Significant savings for repetitive use cases

---

## Running the Script

```bash
# Install dependencies
pip install tiktoken

# Run the calculator
python token_calculator-2.py
```

---

*Generated from token_calculator-2.py analysis*
