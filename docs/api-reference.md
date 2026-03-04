# API Reference

## Base URL

```
http://<host>:<port>
```

Default port: `8000` (configurable via `APP_PORT` env var).

---

## Health Check

### `GET /health`

Returns the health status of all dependencies.

**Response 200:**
```json
{
  "status": "healthy",
  "services": {
    "redis": "up",
    "qdrant": "up",
    "evolution_api": "up"
  }
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `status` | `healthy` / `degraded` | Overall system status |
| `services.*` | `up` / `down` | Individual service status |

---

## Webhook — Receive Message

### `POST /api/v1/webhook/message`

Receives an incoming WhatsApp message from Evolution API and processes it through the agent pipeline.

**Request Body:**
```json
{
  "instance": "example_tenant",
  "phone": "5511999999999",
  "message": "Qual o horário de funcionamento?",
  "session_id": "optional-session-id"
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `instance` | string | ✅ | Evolution API instance name (maps to tenant_id) |
| `phone` | string | ✅ | Sender phone number (international format) |
| `message` | string | ✅ | Message text content |
| `session_id` | string | — | Session ID (auto-generated if empty) |

**Response 200:**
```json
{
  "status": "ok",
  "response": "Nosso horário é de 8h às 18h, de segunda a sexta.",
  "source": "cache",
  "cached": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Agent's reply text |
| `source` | string | `cache`, `ai`, or `system` |
| `cached` | boolean | Whether the response came from semantic cache |

**Error Responses:**

| Code | Condition |
|------|-----------|
| 404 | Tenant not found |
| 500 | Internal processing error |

---

## Admin — Tenant Management

### `GET /api/v1/admin/tenants`

List all configured tenants.

**Response 200:**
```json
{
  "count": 2,
  "tenants": ["acme_corp", "tech_startup"]
}
```

---

### `GET /api/v1/admin/tenants/{tenant_id}`

Get the current configuration summary for a tenant.

**Response 200:**
```json
{
  "tenant_id": "acme_corp",
  "agent_name": "Atendente Virtual",
  "language": "pt-BR",
  "cache_threshold": 0.92,
  "cache_ttl_hours": 24,
  "business_hours": {
    "timezone": "America/Sao_Paulo",
    "monday_friday": "08:00-18:00",
    "saturday": "09:00-13:00",
    "sunday": null
  },
  "escalation_keywords": ["falar com humano", "gerente"],
  "webhook_endpoint": "https://example.com/webhooks"
}
```

---

### `POST /api/v1/admin/tenants/{tenant_id}/reload`

Force-reload a tenant's settings.yaml from disk without restarting the app.

**Response 200:**
```json
{
  "status": "reloaded",
  "tenant_id": "acme_corp",
  "agent_name": "Atendente Virtual"
}
```

| Code | Condition |
|------|-----------|
| 404 | Tenant not found |
| 422 | Invalid settings.yaml |

---

### `POST /api/v1/admin/tenants/reload-all`

Clear the tenant configuration cache. All tenants will be re-loaded from disk on next access.

**Response 200:**
```json
{
  "status": "cache_cleared",
  "tenants_available": 3
}
```

---

## Admin — Webhook Audit

### `GET /api/v1/admin/webhooks/received`

View received webhook events (audit log).

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `tenant_id` | string | — | Filter by tenant |
| `limit` | int | 50 | Max results |

---

### `GET /api/v1/admin/webhooks/deliveries`

View outbound webhook delivery records.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `tenant_id` | string | — | Filter by tenant |
| `limit` | int | 50 | Max results |

**Response 200:**
```json
{
  "count": 1,
  "deliveries": [
    {
      "event": "message_received",
      "tenant_id": "acme_corp",
      "endpoint": "https://example.com/webhook",
      "status": "delivered",
      "attempts": 1,
      "last_attempt": "2026-01-01T12:00:00",
      "response_code": 200
    }
  ]
}
```

---

## Interactive Documentation

- **Swagger UI:** `http://<host>:8000/docs`
- **ReDoc:** `http://<host>:8000/redoc`
