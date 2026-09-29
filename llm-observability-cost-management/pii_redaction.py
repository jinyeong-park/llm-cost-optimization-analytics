# pii_redaction.py
"""
PII Redaction for Observability
Required for GDPR, HIPAA, SOC2 compliance
"""

import re
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


class PIIRedactor:
    """Redact PII before logging to observability platform."""

    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    def redact(self, text: str) -> str:
        """Redact all PII patterns from text."""
        result = text
        for pii_type, pattern in self.PATTERNS.items():
            result = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", result)
        return result

    def redact_dict(self, data: Dict) -> Dict:
        """Recursively redact PII from a dictionary."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.redact(v) if isinstance(v, str) else v for v in value
                ]
            else:
                result[key] = value
        return result


def call_claude(prompt: str):
    """Call Claude API and return response."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0]


# Integrate with your observability
from langfuse import observe, Langfuse

langfuse = Langfuse()
redactor = PIIRedactor()


@observe(capture_input=False, capture_output=False)
def secure_llm_call(prompt: str) -> str:
    """LLM call with PII redaction for logs.

    Note: We disable automatic capture and manually log redacted versions.
    """

    response = call_claude(prompt)

    # Manually log redacted versions using v3 API
    langfuse.update_current_span(
        input=redactor.redact(prompt),
        output=redactor.redact(response.text),
    )

    return response.text


if __name__ == "__main__":
    # Test with a prompt containing PII
    test_prompt = """
    Please help me with my account. My email is john.doe@example.com
    and my phone number is 555-123-4567. My SSN is 123-45-6789.
    """

    print("Testing PII redaction with LLM call...")
    result = secure_llm_call(test_prompt)
    print(f"Response: {result}")
