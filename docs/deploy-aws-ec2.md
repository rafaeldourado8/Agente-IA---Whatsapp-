# ☁️ Deploy na AWS EC2 — Free Tier

> Guia para subir o agente em uma instância EC2 gratuita da Amazon.

---

## ⚠️ Aviso sobre o Free Tier

| Recurso | Free Tier | O que precisamos | Funciona? |
|---------|-----------|-----------------|:---------:|
| **Instância** | t2.micro (1 vCPU, 1GB RAM) | ~1.2GB no pico | ⚡ Apertado |
| **Disco** | 30GB EBS gp2 | ~5GB | ✅ Sobra |
| **Rede** | 15GB/mês outbound | Pouco tráfego | ✅ OK |
| **Duração** | 12 meses grátis | - | ✅ |

> 💡 **1GB de RAM é apertado** para rodar App + Redis + Qdrant + Evolution API. Vamos adicionar **2GB de swap** para funcionar. Para produção real com volume, recomendamos **t3.small** (2GB RAM, ~$15/mês).

---

## Parte 1 — Criar a Instância EC2

### 1.1 Acessar o Console da AWS

1. Acesse [console.aws.amazon.com](https://console.aws.amazon.com)
2. Vá em **EC2 → Launch Instance**

### 1.2 Configurar a Instância

| Campo | Valor |
|-------|-------|
| **Name** | `whatsapp-agent` |
| **AMI** | Ubuntu Server 24.04 LTS (Free tier eligible) |
| **Instance type** | `t2.micro` (Free tier eligible) |
| **Key pair** | Criar nova → nome: `whatsapp-agent-key` → Download `.pem` |
| **Security Group** | Criar novo (veja regras abaixo) |
| **Storage** | 30 GB gp2 (máximo do free tier) |

### 1.3 Configurar Security Group (Firewall)

Clique em **Edit** nas regras de entrada e adicione:

| Tipo | Porta | Origem | Motivo |
|------|:-----:|--------|--------|
| SSH | 22 | Meu IP | Acesso remoto |
| HTTP | 80 | 0.0.0.0/0 | (futuro reverse proxy) |
| HTTPS | 443 | 0.0.0.0/0 | (futuro reverse proxy) |
| Custom TCP | 8000 | 0.0.0.0/0 | API do agente |
| Custom TCP | 8080 | Meu IP | Evolution API (admin) |

> 🔒 **Segurança:** a porta 8080 (Evolution API) deve ficar aberta **só para o seu IP**. Nunca exponha para o mundo.

### 1.4 Lançar e Conectar

```bash
# Dar permissão à chave (no seu computador)
chmod 400 whatsapp-agent-key.pem

# Conectar via SSH (substitua pelo IP público da instância)
ssh -i whatsapp-agent-key.pem ubuntu@SEU_IP_PUBLICO
```

> 💡 No Windows, use o PuTTY ou o terminal do VS Code com a extensão Remote SSH.

---

## Parte 2 — Preparar o Servidor

### 2.1 Atualizar e Instalar Docker

```bash
# Atualizar pacotes
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# Verificar
docker --version
docker compose version
```

### 2.2 Criar Swap (ESSENCIAL para t2.micro)

Como temos apenas 1GB de RAM, o swap evita travamentos:

```bash
# Criar arquivo de swap de 2GB
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Tornar permanente
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verificar
free -h
# Deve mostrar 2GB de swap
```

### 2.3 Otimizar Memória

```bash
# Reduzir tendência de usar swap (usar só quando necessário)
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## Parte 3 — Instalar e Configurar

### 3.1 Clonar o Projeto

```bash
git clone <URL_DO_REPOSITORIO> /opt/whatsapp-agent
cd /opt/whatsapp-agent
```

### 3.2 Instalar Evolution API

```bash
mkdir -p /opt/evolution-api
cat <<'EOF' > /opt/evolution-api/docker-compose.yml
services:
  evolution-api:
    image: atendai/evolution-api:v2.2.3
    ports:
      - "8080:8080"
    environment:
      - AUTHENTICATION_API_KEY=MINHA_CHAVE_EVOLUTION_123
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://postgres:evo_pg_pass@postgres:5432/evolution
      - WEBHOOK_GLOBAL_URL=http://172.17.0.1:8000/api/v1/webhook/message
      - WEBHOOK_GLOBAL_ENABLED=true
      - WEBHOOK_EVENTS=MESSAGES_UPSERT
    volumes:
      - evolution_data:/evolution/instances
    depends_on:
      - postgres
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=evo_pg_pass
      - POSTGRES_DB=evolution
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M

volumes:
  evolution_data:
  postgres_data:
EOF
```

> ⚠️ Na AWS EC2, **não existe `host.docker.internal`**. Usamos `172.17.0.1` (gateway padrão do Docker bridge) para o app se comunicar com a Evolution API.

```bash
cd /opt/evolution-api
docker compose up -d
```

### 3.3 Criar Instância e Conectar WhatsApp

```bash
# Criar instância
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: MINHA_CHAVE_EVOLUTION_123" \
  -H "Content-Type: application/json" \
  -d '{"instanceName": "minha_empresa", "integration": "WHATSAPP-BAILEYS", "qrcode": true}'

# Pegar QR Code para escanear
curl http://localhost:8080/instance/connect/minha_empresa \
  -H "apikey: MINHA_CHAVE_EVOLUTION_123"
```

Escaneie o QR Code com o WhatsApp do número desejado.

### 3.4 Configurar o Agente

```bash
cd /opt/whatsapp-agent

# Criar .env
cp .env.example .env
nano .env
```

Preencha o `.env`:

```ini
APP_PORT=8000
LOG_LEVEL=INFO
TENANT_CONFIG_DIR=./tenants

GEMINI_API_KEY=AIzaSy_SUA_CHAVE_GEMINI
GEMINI_MODEL=gemini-2.0-flash

REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=redis_pass_forte_456

QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_NAME=conversations

EVOLUTION_API_URL=http://172.17.0.1:8080
EVOLUTION_API_KEY=MINHA_CHAVE_EVOLUTION_123

WEBHOOK_SECRET=webhook_secret_789
```

### 3.5 Configurar Tenant

```bash
cp -r tenants/example_tenant tenants/minha_empresa
nano tenants/minha_empresa/settings.yaml
# Configure conforme o guia-de-ativacao.md
```

### 3.6 Otimizar Docker Compose para EC2

Vamos limitar a memória dos containers para caber no t2.micro:

```bash
cat <<'EOF' >> docker-compose.override.yml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 256M
  redis:
    deploy:
      resources:
        limits:
          memory: 128M
  qdrant:
    deploy:
      resources:
        limits:
          memory: 384M
EOF
```

### 3.7 Iniciar

```bash
docker compose up -d

# Aguardar ~60 segundos no t2.micro (mais lento que VPS maiores)
sleep 60

# Verificar
docker compose ps
curl http://localhost:8000/health
```

---

## Parte 4 — Configurar IP Elástico (Fixo)

Por padrão, o IP da EC2 muda a cada reinício. Para ter um IP fixo:

1. No Console AWS → **EC2 → Elastic IPs**
2. Clique **Allocate Elastic IP address**
3. Clique **Associate Elastic IP**
4. Selecione a instância `whatsapp-agent`

> 💡 IP Elástico é **gratuito** enquanto estiver associado a uma instância em execução.

---

## Parte 5 — Verificação Final

```bash
# De dentro do servidor
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/admin/tenants

# Do seu computador (substitua pelo IP público/elástico)
curl http://SEU_IP_PUBLICO:8000/health
```

Agora envie uma mensagem WhatsApp para o número conectado e veja a magia acontecer! 🎉

---

## 📊 Monitoramento de Recursos

```bash
# Ver uso de memória dos containers
docker stats --no-stream

# Ver uso do sistema
free -h
df -h
```

**Uso esperado no t2.micro:**

| Container | RAM |
|-----------|-----|
| App (FastAPI) | ~150MB |
| Redis | ~50MB |
| Qdrant | ~200–350MB |
| Evolution API | ~200MB |
| Postgres (Evolution) | ~80MB |
| **Total** | **~700MB–900MB** |
| Swap disponível | 2GB |

---

## ⚡ Dicas de Performance no Free Tier

1. **Não rode outros serviços** no mesmo servidor
2. **Monitore a memória** com `docker stats` regularmente
3. **Configure alertas na AWS** → CloudWatch → CPUUtilization > 80%
4. **Reinicie semanalmente** para limpar memória fragmentada:
   ```bash
   docker compose -f /opt/evolution-api/docker-compose.yml restart
   docker compose -f /opt/whatsapp-agent/docker-compose.yml restart
   ```
5. **Considere upgrade** para t3.small ($15/mês) se o agente atender muitas mensagens

---

## 🔒 Segurança Extra na AWS

- [ ] Usar **Elastic IP** para IP fixo
- [ ] Security Group com portas mínimas abertas
- [ ] Porta 8080 liberada **apenas para o seu IP**
- [ ] Habilitar **backup automático** do EBS (snapshots)
- [ ] Configurar **MFA** na conta AWS
- [ ] Nunca commitar chaves no repositório

---

## 🆘 Se o Servidor Ficar Lento

```bash
# Ver o que está consumindo mais
docker stats

# Se Qdrant estiver usando demais, reiniciar
docker compose restart qdrant

# Se tudo estiver engasgado, reiniciar tudo
docker compose down
docker compose -f /opt/evolution-api/docker-compose.yml down
# Esperar 10 segundos
docker compose -f /opt/evolution-api/docker-compose.yml up -d
sleep 15
docker compose up -d
```
