# model_router.py
"""
Smart Model Router
Automatically routes requests to the most cost-effective model
"""

from enum import Enum
from typing import Optional
import re
from dotenv import load_dotenv

load_dotenv()


class TaskType(Enum):
    SIMPLE = "simple"  # Yes/no, classification
    MODERATE = "moderate"  # Summarization, extraction
    COMPLEX = "complex"  # Analysis, reasoning
    CODE = "code"  # Code generation
    CREATIVE = "creative"  # Creative writing


class ModelRouter:
    """Route requests to optimal models based on task analysis."""

    # Model tiers (cheapest first)
    MODELS = {
        TaskType.SIMPLE: "claude-3-5-haiku-20241022",  # $0.25/1M
        TaskType.MODERATE: "gpt-4o-mini",  # $0.15/1M
        TaskType.CODE: "claude-sonnet-4-20250514",  # Best for code
        TaskType.COMPLEX: "claude-sonnet-4-20250514",  # $3/1M
        TaskType.CREATIVE: "gpt-4o",  # $2.50/1M
    }

    def classify_task(self, prompt: str) -> TaskType:
        """Analyze prompt to determine task type."""

        prompt_lower = prompt.lower()

        # Simple patterns - yes/no, classification
        simple_patterns = [
            r"\b(yes or no)\b",
            r"\b(true or false)\b",
            r"\b(classify|categorize)\b",
            r"^is (this|it|the)",
            r"\b(which one|choose|select)\b",
        ]
        for pattern in simple_patterns:
            if re.search(pattern, prompt_lower):
                return TaskType.SIMPLE

        # Code patterns
        code_patterns = [
            r"\b(write|create|generate|fix|debug).*(code|function|class|script)\b",
            r"\b(python|javascript|typescript|java|rust)\b",
            r"```",  # Code blocks in prompt
        ]
        for pattern in code_patterns:
            if re.search(pattern, prompt_lower):
                return TaskType.CODE

        # Complex reasoning patterns
        complex_patterns = [
            r"\b(analyze|evaluate|compare|critique)\b",
            r"\b(why|how).*(work|happen|cause)\b",
            r"\b(pros and cons|trade-?offs)\b",
            r"\b(explain.*(detail|depth))\b",
        ]
        for pattern in complex_patterns:
            if re.search(pattern, prompt_lower):
                return TaskType.COMPLEX

        # Creative patterns
        creative_patterns = [
            r"\b(write|create|compose).*(story|poem|essay|blog)\b",
            r"\b(creative|imaginative|original)\b",
        ]
        for pattern in creative_patterns:
            if re.search(pattern, prompt_lower):
                return TaskType.CREATIVE

        # Default to moderate
        return TaskType.MODERATE

    def route(self, prompt: str, override_model: Optional[str] = None) -> str:
        """Get the optimal model for a prompt."""

        if override_model:
            return override_model

        task_type = self.classify_task(prompt)
        return self.MODELS[task_type]


# Integration with observability
from langfuse import observe, Langfuse
from anthropic import Anthropic
from openai import OpenAI

langfuse = Langfuse()
router = ModelRouter()

# Initialize clients
anthropic_client = Anthropic()
openai_client = OpenAI()


def call_claude(prompt: str, model: str):
    """Call Claude API."""
    response = anthropic_client.messages.create(
        model=model, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0]


def call_openai(prompt: str, model: str):
    """Call OpenAI API."""
    response = openai_client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message


@observe()
def routed_llm_call(prompt: str, override_model: str = None) -> str:
    """LLM call with automatic model routing."""

    selected_model = router.route(prompt, override_model)
    task_type = router.classify_task(prompt)

    langfuse.update_current_span(
        metadata={
            "task_type": task_type.value,
            "routed_model": selected_model,
        }
    )

    # Use the provider-appropriate function
    if "claude" in selected_model:
        return call_claude(prompt, model=selected_model).text
    else:
        return call_openai(prompt, model=selected_model).content


if __name__ == "__main__":
    # Test different prompts to see routing in action
    print(routed_llm_call("Is 2 + 2 = 4? Yes or no"))  # Routes to SIMPLE
    print(routed_llm_call("Write a Python function to sort a list"))  # Routes to CODE

    langfuse.flush()
