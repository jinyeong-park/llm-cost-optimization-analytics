"""
Langfuse API Level 4: Low-level SDK (Langfuse v3)

This approach gives you maximum control over everything:
- Custom timing
- Scores and evaluations
- Events for debugging
- Manual span/generation management
"""

from langfuse import Langfuse
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()
client = OpenAI()
langfuse = Langfuse()

expression = "123 + 456 * 2"

# Create root span - this creates a new trace automatically
root_span = langfuse.start_span(
    name="calculator_low_level",
    input={"expression": expression},
    metadata={"project": "low_level_example"},
)

# Get the trace_id for later use (scores)
trace_id = root_span.trace_id

# Create a child span for preprocessing
preprocessing_span = langfuse.start_span(
    name="preprocessing",
    input={"raw_expression": expression},
)
preprocessing_span.update(
    output={"validated_expression": expression, "status": "valid"},
)
preprocessing_span.end()

# Create generation manually with custom timing
start_time = time.time()

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

end_time = time.time()
result = completion.choices[0].message.content

# Log generation with full control
generation = langfuse.start_generation(
    name="llm_calculation",
    model="gpt-4o-mini",
    model_parameters={"temperature": 1.0},
    input=[
        {
            "role": "system",
            "content": "You are a very accurate calculator. You output only the result of the calculation.",
        },
        {"role": "user", "content": expression},
    ],
)

# Update with output and usage, then end
generation.update(
    output=result,
    usage_details={
        "input": completion.usage.prompt_tokens,
        "output": completion.usage.completion_tokens,
        "total": completion.usage.total_tokens,
    },
    level="DEFAULT",  # Options: "DEBUG", "DEFAULT", "WARNING", "ERROR"
    status_message="Calculation completed successfully",
)
generation.end()

# End the root span with final output
root_span.update(
    output={"result": result},
    metadata={"duration_ms": (end_time - start_time) * 1000},
)
root_span.end()

# Add a score to evaluate the trace
langfuse.create_score(
    trace_id=trace_id,
    name="accuracy",
    value=1.0,
    comment="Correct calculation verified",
)

# Create an event for debugging/logging (within current context)
event = langfuse.create_event(
    name="calculation_complete",
    input={"expression": expression},
    output={"result": result},
    metadata={"duration_ms": (end_time - start_time) * 1000},
)

print(f"{expression} = {result}")
print(f"Duration: {(end_time - start_time) * 1000:.2f}ms")
print(f"Tokens used: {completion.usage.total_tokens}")
print(f"Trace ID: {trace_id}")

# Ensure data is sent to Langfuse before script exits
langfuse.flush()
