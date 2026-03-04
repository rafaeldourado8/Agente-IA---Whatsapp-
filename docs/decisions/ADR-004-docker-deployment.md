# ADR-004: Docker as the Only Deployment Method

## Status
Accepted

## Context
The product is a self-hosted B2B SaaS installed on the client's VPS or on-premises machine. We need a deployment method that is:
- Reproducible across different environments
- Easy for non-developer operators to manage
- Capable of orchestrating multiple services (app, Redis, Qdrant)
- Isolated from the host OS to prevent dependency conflicts

## Decision
Use **Docker and Docker Compose** as the only supported deployment method.

The application is packaged as a Docker image with a multi-stage build (lean runtime image, non-root user). All dependencies (Redis, Qdrant) are defined in `docker-compose.yml` with health checks and named volumes.

## Consequences

### Positive
- **Reproducible**: identical environment on every deployment
- **Simple operations**: `docker compose up -d` starts everything
- **Isolation**: no dependency conflicts with the host system
- **Health checks**: services only start when dependencies are ready
- **Volume management**: persistent data survives container restarts

### Negative
- Requires Docker and Docker Compose installed on the host
- Small performance overhead from containerization
- Image builds require internet access (pulling base images)
- Operators need basic Docker knowledge

## Alternatives Considered

### Direct host installation (pip install + systemd)
Simpler for single-service apps but fragile with multiple dependencies. Rejected because managing Redis + Qdrant + the app natively increases support burden.

### Kubernetes
Optimal for large-scale multi-tenant but overkill for single-tenant VPS deployments. May be supported in the future for enterprise clients.
