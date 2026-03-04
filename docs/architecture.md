# Architecture Overview

## System Description

WhatsApp B2B AI Agent is a multi-tenant, headless customer-support platform that connects WhatsApp users to AI-powered agents via the Evolution API. Each tenant (B2B client) gets its own configuration — personality, rules, FAQ, business hours, and webhook endpoints — defined entirely in a YAML file. No code changes are required to onboard a new client.

## High-Level Flow

```
WhatsApp User
    │
    ▼
Evolution API  ──(webhook)──►  FastAPI Gateway
                                    │
                                    ├── 1. Identify tenant by WhatsApp instance
                                    │
                                    ├── 2. Load tenant settings (YAML)
                                    │
                                    ├── 3. Check business hours
                                    │     └── Outside hours → return out_of_hours_message
                                    │
                                    ├── 4. Check escalation keywords
                                    │     └── Match → dispatch escalation webhook
                                    │
                                    ├── 5. Query semantic cache (Redis + embeddings)
                                    │     ├── Cache HIT  → return cached response
                                    │     └── Cache MISS → continue to step 6
                                    │
                                    ├── 6. Retrieve conversation history (Qdrant)
                                    │
                                    ├── 7. Call Google Gemini API
                                    │     └── Include: system_prompt + history + user message
                                    │
                                    ├── 8. Store response in semantic cache
                                    │
                                    ├── 9. Store messages in Qdrant (history)
                                    │
                                    ├── 10. Dispatch event webhooks
                                    │
                                    └── 11. Send response back via Evolution API
                                              │
                                              ▼
                                        WhatsApp User
```

## Component Architecture

### Layers

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **API** | `app/api/` | HTTP endpoints, request validation, dependency injection |
| **Core** | `app/core/` | Business logic, orchestration, ABC interfaces |
| **Services** | `app/services/` | Concrete implementations of external integrations |
| **Tenant** | `app/tenant/` | Multi-tenant config loading and validation |
| **Models** | `app/models/` | Pydantic data schemas (no logic) |

### External Dependencies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| AI Provider | Google Gemini | Natural language response generation |
| Semantic Cache | Redis + Embeddings | Avoid redundant AI calls for similar questions |
| Vector Store | Qdrant | Conversation history with semantic search |
| WhatsApp Gateway | Evolution API | Send/receive WhatsApp messages |

### Dependency Flow

```
API Layer  ──►  Core Layer  ──►  Interfaces (ABCs)
                                      ▲
                                      │
                              Services Layer (implementations)
```

The Core layer depends **only** on abstractions (`interfaces.py`). Concrete implementations in `services/` are injected at runtime via FastAPI's dependency injection system. This ensures testability (swap real services with mocks) and extensibility (add new AI providers without touching core logic).

## Multi-Tenant Design

Each tenant is identified by a unique directory name under `tenants/`:

```
tenants/
├── acme_corp/
│   ├── settings.yaml    # Agent personality, rules, business hours
│   └── faq.yaml         # Optional FAQ entries
├── tech_startup/
│   ├── settings.yaml
│   └── faq.yaml
```

Tenant isolation is enforced at every layer:
- **Config**: each tenant loads its own settings file
- **Cache**: cache keys are namespaced by tenant_id
- **History**: Qdrant queries filter by tenant_id
- **Webhooks**: each tenant can have its own webhook endpoint

## Security Model

- All secrets are loaded from environment variables, never hardcoded
- Webhook payloads are signed with HMAC-SHA256
- The application container runs as a non-root user
- Redis and Qdrant ports are not exposed in production Docker Compose
- Tenant config files are mounted read-only in production
