import tiktoken

# Initialize the tokenizer for GPT-4
enc = tiktoken.encoding_for_model("gpt-4")

# Let's count some tokens
examples = [
    "Hello, world!",  # Simple
    "The quick brown fox jumps over the lazy dog.",  # Standard sentence
    "def calculate_total(items): return sum(item.price for item in items)",  # Code
    "supercalifragilisticexpialidocious",  # Long word
]

for text in examples:
    tokens = enc.encode(text)
    print(f"'{text}'")
    print(f"  Characters: {len(text)}")
    print(f"  Tokens: {len(tokens)}")
    print(f"  Tokens: {tokens}")
    print()