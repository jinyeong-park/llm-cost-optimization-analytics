from langfuse.openai import openai
from dotenv import load_dotenv


load_dotenv()

completion = openai.chat.completions.create(
    name="first_trace_llm",
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": "You are a very accurate calculator. You output only the result of the calculation.",
        },
        {"role": "user", "content": "123 + 456 * 2 = "},
    ],
    metadata={"project": "first_trace_llm_project"},
)
print(completion.choices[0].message.content)
