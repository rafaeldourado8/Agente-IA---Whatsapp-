# ADR-002: Semantic Cache with Redis

## Status
Accepted

## Context
Every user message sent to the AI provider (Google Gemini) incurs:
- **Latency**: 1–5 seconds per API call
- **Cost**: charged per token (input + output)

In support/FAQ scenarios, many users ask semantically identical questions (e.g., "what are your business hours?" vs "when do you open?"). Without caching, each of these generates a separate AI call with the same response.

## Decision
Implement a **semantic cache** layer using Redis to store and retrieve AI responses based on query similarity.

### How it works
1. When a user message arrives, compute its embedding vector
2. Compare the embedding against cached query embeddings in Redis using cosine similarity
3. If similarity ≥ configurable threshold (default 0.92), return the cached response (**cache hit**)
4. Otherwise, call the AI provider, cache the query embedding + response, and return (**cache miss**)

### Cache key design
```
cache:{tenant_id}:{embedding_hash} → {response_text, original_query, timestamp}
```

Each tenant has isolated cache entries. The TTL is configurable per tenant (`cache.ttl_hours` in settings.yaml).

### Similarity threshold
The threshold (0.0–1.0) balances:
- **Too high** (e.g., 0.99): almost no cache hits, defeats the purpose
- **Too low** (e.g., 0.80): returns incorrect responses for different questions

Default of 0.92 is a conservative starting point. Each tenant can tune this in their `settings.yaml`.

## Consequences

### Positive
- **Cost reduction**: 40–70% fewer AI calls for FAQ-heavy tenants
- **Latency reduction**: cached responses return in <50ms vs 1–5s for AI calls
- **Configurable per tenant**: each client can tune threshold and TTL
- **Key differentiator**: most competitors call the AI for every message

### Negative
- Requires embedding computation for every incoming message (lightweight vs full AI call)
- Cache invalidation when a tenant updates their FAQ or system prompt requires clearing the cache
- Subtle semantic differences may cause incorrect cache hits if threshold is too low
- Additional memory usage in Redis for embeddings and cached responses

## Alternatives Considered

### Exact-match cache (hash of query text)
Only matches identical strings — "business hours?" ≠ "what are your hours?" — very low hit rate. Rejected.

### LLM-based cache (e.g., GPTCache)
Third-party library with additional dependencies and complexity. Rejected in favor of a simpler, custom implementation using standard Redis + embedding comparison.

### No cache
Simpler architecture but 100% of messages hit the AI provider. Rejected because it increases cost and latency significantly for FAQ-heavy workloads, which is the primary use case.
