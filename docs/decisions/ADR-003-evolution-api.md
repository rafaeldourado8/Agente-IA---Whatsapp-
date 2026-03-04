# ADR-003: Evolution API for WhatsApp Integration

## Status
Accepted

## Context
The agent needs to send and receive WhatsApp messages. The WhatsApp Business API requires either:
1. An official Meta Business API integration (expensive, complex approval process)
2. A third-party gateway that abstracts the WhatsApp protocol

For a self-hosted B2B SaaS product, we need a solution that:
- Can be installed alongside our application on the client's VPS
- Supports multiple WhatsApp instances (one per tenant or shared)
- Provides a simple REST API for message sending
- Handles QR code pairing and session management
- Is open-source or has a permissive license

## Decision
Use **Evolution API** as the WhatsApp gateway.

Evolution API is an open-source WhatsApp integration layer that provides:
- REST API for sending/receiving messages
- Multi-instance support (multiple WhatsApp numbers)
- Webhook-based message reception
- Session management with QR code pairing
- Docker-native deployment
- Active community and regular updates

## Consequences

### Positive
- **Self-hosted**: runs as a Docker container alongside our application
- **REST API**: simple HTTP integration, no protocol-level complexity
- **Multi-instance**: each tenant can have their own WhatsApp number
- **Open-source**: no licensing costs, full source available
- **Docker-native**: fits our containerized deployment model

### Negative
- **Unofficial**: uses reverse-engineered WhatsApp Web protocol, risk of being blocked
- **Dependency**: relies on external project maintenance
- **Stability**: less battle-tested than Meta's official API

## Alternatives Considered

### Meta Official WhatsApp Business API
Most reliable but requires business verification, costs per conversation, and complex setup. Rejected for initial version because it conflicts with the self-hosted, low-cost SaaS model. May be supported as an optional provider in the future.

### Baileys (direct library)
JavaScript library for direct WhatsApp Web integration. Rejected because it would require building our own REST layer, session management, and reconnection logic — essentially reimplementing what Evolution API already provides.

### Twilio WhatsApp
Managed service with per-message pricing. Rejected because it cannot be self-hosted and increases per-tenant costs.
