"""
Langfuse API Level 3: Context Manager (Langfuse v3)

This approach uses context managers to explicitly define trace hierarchy.
You have fine-grained control over spans and generations.
"""

from langfuse import Langfuse
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
langfuse = Langfuse()

expression = "123 + 456 * 2"

# Create a trace and use context managers for spans/generations
with langfuse.start_as_current_span(name="calculator_context_manager") as trace:

    # Add a span for preprocessing
    with langfuse.start_as_current_span(name="input_validation") as validation_span:
        langfuse.update_current_span(
            input={"expression": expression},
            output={"status": "valid"},
        )

    # Add a generation for the LLM call
    with langfuse.start_as_current_generation(
        name="llm_calculation",
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": "You are a very accurate calculator. You output only the result of the calculation.",
            },
            {"role": "user", "content": expression},
        ],
    ) as generation:
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
        result = completion.choices[0].message.content

        langfuse.update_current_generation(
            output=result,
            usage_details={
                "input": completion.usage.prompt_tokens,
                "output": completion.usage.completion_tokens,
            },
            metadata={"project": "context_manager_example"},
        )

    # Update trace with final output
    langfuse.update_current_trace(
        output={"result": result},
        tags=["calculator", "context_manager"],
    )

print(f"{expression} = {result}")

# Ensure data is sent to Langfuse before script exits
langfuse.flush()
