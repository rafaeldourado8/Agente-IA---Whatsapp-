# ADR-001: Qdrant for Conversation History

## Status
Accepted

## Context
The agent needs to maintain conversation history per session and per tenant. This history serves two purposes:

1. **Contextual responses**: include recent messages when calling the AI provider so it can maintain coherent conversations.
2. **Semantic retrieval**: find semantically relevant past interactions to enrich context (beyond the immediate session).

Traditional relational databases (PostgreSQL, MySQL) store messages well but lack native semantic search. A full-text search engine (Elasticsearch) supports keyword search but not vector similarity.

## Decision
Use **Qdrant** as the primary conversation history store.

Qdrant is a purpose-built vector database that supports:
- Storing messages with vector embeddings alongside structured metadata (tenant_id, session_id, timestamp)
- Filtering by metadata fields (e.g., retrieve only messages for a specific tenant and session)
- Nearest-neighbor similarity search on embeddings
- Payload storage alongside vectors (the message text itself)

Each message is stored as a Qdrant point with:
- **Vector**: embedding of the message content
- **Payload**: `{tenant_id, session_id, role, content, timestamp}`

## Consequences

### Positive
- Native semantic search enables "memory" across sessions — the agent can recall relevant past interactions
- Metadata filtering provides efficient retrieval scoped to tenant + session
- Horizontal scalability for growing message volumes
- No additional database needed for conversation storage

### Negative
- Qdrant is not a relational database — complex queries (e.g., aggregate analytics) are harder
- Requires embedding generation for every stored message (additional compute cost)
- Vector databases are less mature than relational databases in terms of ecosystem and tooling

## Alternatives Considered

### PostgreSQL + pgvector
Considered combining a relational database with the pgvector extension. Rejected because it adds operational complexity (managing a PostgreSQL instance) and pgvector's query performance for large-scale similarity search is inferior to purpose-built vector databases.

### Redis with vector search (RediSearch)
Considered using Redis for both cache and history. Rejected because Redis is optimized for ephemeral data — using it for persistent conversation history conflicts with its primary role as a cache and increases memory requirements.

### SQLite with local embeddings
Considered for simplicity in single-tenant deployments. Rejected because it does not scale to multi-tenant environments and lacks built-in vector search.
