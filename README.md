# WhatsApp B2B AI Agent

Multi-tenant WhatsApp AI agent for B2B customer support. Powered by Google Gemini, with semantic caching, conversation memory, and per-client configuration via YAML.

## Quick Start

```bash
# 1. Clone
git clone <repository-url>
cd whatsapp-agent

# 2. Configure
cp .env.example .env
# Edit .env with your API keys and passwords

# 3. Setup first tenant
cp -r tenants/example_tenant tenants/my_client
# Edit tenants/my_client/settings.yaml

# 4. Start
docker compose up -d

# 5. Verify
curl http://localhost:8000/health
```

## Architecture

```
WhatsApp User → Evolution API → FastAPI → Cache/AI/Qdrant → Response
```

- **AI:** Google Gemini for response generation
- **Cache:** Redis semantic cache (reduces cost by 40–70%)
- **Memory:** Qdrant vector database for conversation history
- **Config:** YAML per tenant — no code changes to onboard clients

## Key Features

- 🧠 **Semantic cache** — similar questions get instant cached responses
- 🏢 **Multi-tenant** — each client has isolated config, cache, and history
- ⏰ **Business hours** — automatic out-of-hours messages
- 🚨 **Escalation** — keyword triggers for human handoff via webhook
- 🔗 **Webhooks** — event notifications with HMAC signing and retry
- 📊 **Health checks** — monitors Redis, Qdrant, and Evolution API
- 🐳 **Docker-native** — single command deployment

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System design and component overview |
| [Tenant Config Guide](docs/tenant-config-guide.md) | How to configure a new client |
| [API Reference](docs/api-reference.md) | All endpoints with request/response schemas |
| [Webhook Schema](docs/webhook-schema.md) | Webhook events and HMAC verification |
| [Deployment Guide](docs/deployment.md) | Step-by-step VPS deployment |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check with dependency status |
| `POST` | `/api/v1/webhook/message` | Receive WhatsApp message |
| `GET` | `/api/v1/admin/tenants` | List all tenants |
| `GET` | `/api/v1/admin/tenants/{id}` | Get tenant config |
| `POST` | `/api/v1/admin/tenants/{id}/reload` | Reload tenant config |
| `POST` | `/api/v1/admin/tenants/reload-all` | Clear config cache |

## Development

```bash
# Start with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run tests
pip install -e ".[dev]"
pytest tests/ -v

# Lint
ruff check app/
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python 3.10+) |
| AI | Google Gemini |
| Cache | Redis 7 |
| Vector DB | Qdrant |
| WhatsApp | Evolution API |
| Deploy | Docker + Docker Compose |

## License

Proprietary — all rights reserved.
