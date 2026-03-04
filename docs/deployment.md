# Deployment Guide

## Prerequisites

- Linux VPS or on-premises server (Ubuntu 22.04+ recommended)
- Docker Engine 24.0+
- Docker Compose v2.20+
- At least 2GB RAM, 10GB disk

## Step-by-Step Deployment

### 1. Clone the Repository

```bash
git clone <repository-url> /opt/whatsapp-agent
cd /opt/whatsapp-agent
```

### 2. Create Environment File

```bash
cp .env.example .env
nano .env
```

Fill in all required values:
- `GEMINI_API_KEY` — your Google AI API key
- `REDIS_PASSWORD` — strong password for Redis
- `EVOLUTION_API_KEY` — your Evolution API key
- `WEBHOOK_SECRET` — random string for HMAC signing

### 3. Configure Your First Tenant

```bash
cp -r tenants/example_tenant tenants/my_client
nano tenants/my_client/settings.yaml
```

Edit the settings: agent name, personality, system prompt, business hours, escalation keywords, and webhook endpoints. See `docs/tenant-config-guide.md` for details.

### 4. Build and Start

```bash
docker compose up -d
```

This will:
1. Build the application image
2. Start Redis (waits for healthy)
3. Start Qdrant (waits for healthy)
4. Start the application (waits for Redis + Qdrant)

### 5. Verify

```bash
# Check all containers are running
docker compose ps

# Check application health
curl http://localhost:8000/health

# Check tenant is loaded
curl http://localhost:8000/api/v1/admin/tenants
```

## Operations

### Viewing Logs

```bash
# All services
docker compose logs -f

# Application only
docker compose logs -f app

# Last 100 lines
docker compose logs --tail 100 app
```

### Adding a New Tenant

```bash
# 1. Create tenant directory
cp -r tenants/example_tenant tenants/new_client
nano tenants/new_client/settings.yaml

# 2. Reload without restart
curl -X POST http://localhost:8000/api/v1/admin/tenants/new_client/reload
```

### Updating Tenant Configuration

```bash
# 1. Edit the file
nano tenants/my_client/settings.yaml

# 2. Reload single tenant (no restart needed)
curl -X POST http://localhost:8000/api/v1/admin/tenants/my_client/reload

# Or reload all tenants
curl -X POST http://localhost:8000/api/v1/admin/tenants/reload-all
```

### Updating the Application

```bash
git pull
docker compose build app
docker compose up -d app
```

### Restarting Services

```bash
# Restart app only (data preserved)
docker compose restart app

# Restart everything (data preserved)
docker compose restart

# ⚠️ DANGER: this DELETES all data
# docker compose down -v
```

## Security Checklist

- [ ] All secrets in `.env`, never in code
- [ ] `.env` is in `.gitignore`
- [ ] Redis and Qdrant ports NOT exposed (`docker-compose.yml` has no `ports:` for them)
- [ ] Application container runs as non-root user
- [ ] Tenant volumes mounted read-only (`:ro`) in production
- [ ] HTTPS configured via reverse proxy (nginx/Caddy) in front of the app
- [ ] Webhook secrets are unique per tenant
