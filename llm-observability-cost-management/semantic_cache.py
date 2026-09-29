# semantic_cache.py
"""
Semantic Cache for LLM Responses
Reduces costs by 30-50% for applications with repeated query patterns
"""

import chromadb
from sentence_transformers import SentenceTransformer
import hashlib
import json
from typing import Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
import anthropic

load_dotenv()

# Initialize Anthropic client
client = anthropic.Anthropic()


def call_claude(query: str) -> anthropic.types.Message:
    """Call Claude API with the given query."""
    return client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": query}],
    )


class SemanticCache:
    def __init__(
        self,
        similarity_threshold: float = 0.92,  # How similar queries must be
        ttl_hours: int = 24,  # Cache expiration
        persist_directory: str = "./chroma_cache_db",  # Persist for cross-run caching
    ):
        # Use PersistentClient for cache to survive across runs
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="llm_cache", metadata={"hnsw:space": "cosine"}
        )
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self.threshold = similarity_threshold
        self.ttl = timedelta(hours=ttl_hours)

    def _get_embedding(self, text: str) -> list:
        return self.encoder.encode(text).tolist()

    def _is_expired(self, timestamp: str) -> bool:
        cached_time = datetime.fromisoformat(timestamp)
        return datetime.now() - cached_time > self.ttl

    def get(self, query: str) -> Optional[Tuple[str, float]]:
        """
        Look for a cached response.

        Returns: (cached_response, similarity_score) or None
        """
        query_embedding = self._get_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"][0]:
            return None

        # Check similarity (distance to similarity)
        distance = results["distances"][0][0]
        similarity = 1 - distance  # Cosine distance to similarity

        if similarity < self.threshold:
            return None

        # Check expiration
        metadata = results["metadatas"][0][0]
        if self._is_expired(metadata["timestamp"]):
            return None

        cached_response = json.loads(metadata["response"])
        return (cached_response, similarity)

    def set(self, query: str, response: str, metadata: dict = None):
        """Cache a response for a query."""

        query_embedding = self._get_embedding(query)
        doc_id = hashlib.md5(query.encode()).hexdigest()

        self.collection.upsert(
            ids=[doc_id],
            embeddings=[query_embedding],
            documents=[query],
            metadatas=[
                {
                    "response": json.dumps(response),
                    "timestamp": datetime.now().isoformat(),
                    **(metadata or {}),
                }
            ],
        )


# Usage
from langfuse import observe, Langfuse

langfuse = Langfuse()
cache = SemanticCache(similarity_threshold=0.85)  # Lowered for better semantic matching


@observe()
def cached_llm_call(query: str) -> str:
    """LLM call with semantic caching."""

    # Check cache first
    cached = cache.get(query)
    if cached:
        response, similarity = cached
        langfuse.update_current_span(
            metadata={
                "cache_hit": True,
                "similarity": similarity,
            }
        )
        print(f"  ✅ CACHE HIT! Similarity: {similarity:.2%}")
        return response

    # Cache miss - call LLM
    print(f"  ❌ CACHE MISS - Calling Claude API...")
    response = call_claude(query)

    # Extract text from response (content is a list of TextBlock objects)
    response_text = response.content[0].text

    # Store in cache
    cache.set(query, response_text)

    langfuse.update_current_span(metadata={"cache_hit": False})

    return response_text


def simulate_semantic_cache():
    """
    Simulation demonstrating semantic cache hits with similar questions.

    The key insight: Questions don't need to be IDENTICAL - they need to be
    SEMANTICALLY SIMILAR (meaning the same thing in different words).
    """
    print("=" * 70)
    print("🧠 SEMANTIC CACHE SIMULATION")
    print("=" * 70)

    # Track stats
    total_queries = 0
    cache_hits = 0
    cache_misses = 0
    api_calls_saved = 0

    # These question groups are semantically similar to each other
    # Using factual questions that LLMs can actually answer!
    question_groups = [
        {
            "topic": "Python Programming",
            "questions": [
                "What is a Python list comprehension?",
                "Explain list comprehensions in Python",
                "How do list comprehensions work in Python?",
                "What are Python list comprehensions and how to use them?",
            ],
        },
        {
            "topic": "Machine Learning",
            "questions": [
                "What is the difference between supervised and unsupervised learning?",
                "Explain supervised vs unsupervised machine learning",
                "How does supervised learning differ from unsupervised learning?",
                "Compare supervised and unsupervised learning in ML",
            ],
        },
        {
            "topic": "API Concepts",
            "questions": [
                "What is a REST API?",
                "Explain what REST APIs are",
                "What does REST API mean?",
                "Can you describe what a RESTful API is?",
            ],
        },
    ]

    for group in question_groups:
        print(f"\n{'─' * 70}")
        print(f"📁 TOPIC: {group['topic']}")
        print(f"{'─' * 70}")

        for i, question in enumerate(group["questions"]):
            total_queries += 1
            print(f'\n🔍 Query {i+1}: "{question}"')

            # Check cache BEFORE calling - show what's happening
            cached_result = cache.get(question)
            if cached_result:
                cache_hits += 1
                api_calls_saved += 1
                response, similarity = cached_result
                print(f"   ┌{'─' * 50}┐")
                print(f"   │ ✅ CACHE HIT TRIGGERED!                          │")
                print(f"   │ 💾 Retrieved from semantic cache                 │")
                print(
                    f"   │ 📊 Similarity Score: {similarity:.2%}                     │"
                )
                print(f"   │ 💰 API call SAVED! (Cost: $0.00)                 │")
                print(f"   └{'─' * 50}┘")
                result = response
                langfuse.update_current_span(
                    metadata={"cache_hit": True, "similarity": similarity}
                )
            else:
                cache_misses += 1
                print(f"   ┌{'─' * 50}┐")
                print(f"   │ ❌ CACHE MISS - No similar query found           │")
                print(f"   │ 🌐 Calling Claude API...                         │")
                print(f"   │ 💸 API cost incurred                             │")
                print(f"   └{'─' * 50}┘")
                response = call_claude(question)
                result = response.content[0].text
                cache.set(question, result)
                print(f"   │ 💾 Response cached for future similar queries    │")
                langfuse.update_current_span(metadata={"cache_hit": False})

            # Show truncated response
            display_response = result[:80] + "..." if len(result) > 80 else result
            print(f"   📝 Response: {display_response}")

    # Summary stats
    print(f"\n{'=' * 70}")
    print("📊 CACHE PERFORMANCE SUMMARY")
    print(f"{'=' * 70}")
    print(
        f"""
    ┌─────────────────────────────────────────────────────────────────┐
    │  Total Queries:        {total_queries:3d}                                      │
    │  Cache Hits:           {cache_hits:3d}  ✅                                    │
    │  Cache Misses:         {cache_misses:3d}  ❌                                    │
    │  Hit Rate:             {(cache_hits/total_queries*100) if total_queries > 0 else 0:5.1f}%                                   │
    │  API Calls Saved:      {api_calls_saved:3d}  💰                                    │
    └─────────────────────────────────────────────────────────────────┘
    """
    )

    if cache_hits > 0:
        print("🎉 SEMANTIC CACHING IS WORKING!")
        print("   Similar questions are returning cached responses.")

    print("\n💡 TIP: Run this script again to see even MORE cache hits!")
    print("   The cache persists to disk, so previous queries are remembered.")


if __name__ == "__main__":
    simulate_semantic_cache()
    langfuse.flush()
