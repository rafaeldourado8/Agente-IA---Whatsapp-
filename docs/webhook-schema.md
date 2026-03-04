# Webhook Schema Reference

## Overview

The agent dispatches webhook events to tenant-configured endpoints via `POST` with HMAC-SHA256 signed payloads. All events share a common envelope and each has event-specific `data`.

## Common Headers

| Header | Description |
|--------|-------------|
| `Content-Type` | `application/json` |
| `X-Webhook-Event` | Event type name |
| `X-Webhook-Signature` | HMAC-SHA256 hex digest of the body, signed with the tenant's `webhooks.secret` |

### Verifying Signatures

```python
import hmac, hashlib

def verify(body: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(
        key=secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Delivery Behavior

- **Timeout:** 10 seconds per attempt
- **Retries:** up to 3 attempts on failure
- **Audit:** all deliveries (success and failure) are persisted and viewable via `GET /api/v1/admin/webhooks/deliveries`

---

## Events

### `message_received`

Dispatched after a user message is processed and a response is generated.

```json
{
  "tenant_id": "acme_corp",
  "session_id": "5511999999999_acme_corp",
  "phone": "5511999999999",
  "user_message": "Qual o horário de funcionamento?",
  "agent_response": "Nosso horário é de 8h às 18h.",
  "source": "cache",
  "cached": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tenant_id` | string | Tenant identifier |
| `session_id` | string | Conversation session ID |
| `phone` | string | User phone number |
| `user_message` | string | Original user message |
| `agent_response` | string | Agent's reply |
| `source` | string | `cache`, `ai`, or `system` |
| `cached` | boolean | Whether response was served from cache |

---

### `escalation_triggered`

Dispatched when the user's message contains an escalation keyword.

```json
{
  "tenant_id": "acme_corp",
  "session_id": "5511999999999_acme_corp",
  "phone": "5511999999999",
  "message": "quero falar com humano"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tenant_id` | string | Tenant identifier |
| `session_id` | string | Conversation session ID |
| `phone` | string | User phone number |
| `message` | string | Message that triggered escalation |

---

### `session_started`

Dispatched when a new conversation session begins (first message from a user).

```json
{
  "tenant_id": "acme_corp",
  "session_id": "5511999999999_acme_corp",
  "phone": "5511999999999",
  "started_at": "2026-01-15T10:30:00-03:00"
}
```

---

### `session_ended`

Dispatched when a session is ended due to inactivity timeout.

```json
{
  "tenant_id": "acme_corp",
  "session_id": "5511999999999_acme_corp",
  "phone": "5511999999999",
  "ended_at": "2026-01-15T11:00:00-03:00",
  "message_count": 12
}
```

---

## Configuration

In `tenants/<tenant_id>/settings.yaml`:

```yaml
webhooks:
  events:
    - message_received
    - escalation_triggered
    - session_started
    - session_ended
  endpoint: "https://your-server.com/webhooks/agent"
  secret: "your-hmac-secret"
```
