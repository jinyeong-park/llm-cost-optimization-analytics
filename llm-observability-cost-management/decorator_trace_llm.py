"""
Langfuse API Level 2: Decorator-based (@observe())

This approach uses decorators to automatically create traces and spans.
Nested function calls automatically create nested spans.
"""

from langfuse import observe, Langfuse
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
langfuse = Langfuse()


@observe()  # Creates a trace automatically
def calculator(expression: str) -> str:
    """Single calculation - becomes a span when called from another @observe function."""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a very accurate calculator. You output only the result of the calculation.",
            },
            {"role": "user", "content": expression},
        ],
    )

    # Update current trace/span with additional context
    langfuse.update_current_span(
        metadata={"project": "decorator_example", "tags": ["calculator", "math"]},
    )

    return completion.choices[0].message.content


@observe()  # Nested function = nested span
def process_calculations(expressions: list[str]) -> list[str]:
    """Process multiple calculations - each calculator() call becomes a child span."""
    results = []
    for expr in expressions:
        result = calculator(expr)  # Each call becomes a child span
        results.append(f"{expr} = {result}")
    return results


if __name__ == "__main__":
    # Run it - this creates a trace with nested spans
    expressions = ["123 + 456", "789 * 2", "100 / 4"]
    results = process_calculations(expressions)

    print("Results:")
    for r in results:
        print(f"  {r}")

    # Ensure data is sent to Langfuse
    langfuse.flush()
