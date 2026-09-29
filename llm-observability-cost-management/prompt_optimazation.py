def optimize_prompt(prompt: str) -> str:
    """
    Apply common prompt optimizations.

    NOT a replacement for manual review - just catches obvious bloat.
    """

    # Remove common filler phrases
    fillers = [
        "I want you to",
        "You are a highly intelligent",
        "Please note that",
        "It's important to remember that",
        "In your response, make sure to",
        "As an AI assistant,",
    ]

    result = prompt
    for filler in fillers:
        result = result.replace(filler, "")

    # Remove excessive whitespace
    result = " ".join(result.split())

    # Remove repeated instructions
    lines = result.split(".")
    seen = set()
    unique_lines = []
    for line in lines:
        normalized = line.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_lines.append(line)

    return ". ".join(unique_lines)