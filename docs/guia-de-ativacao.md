# 🚀 Guia de Ativação — WhatsApp B2B AI Agent

> Guia passo a passo para instalar, configurar e ativar o agente de IA no WhatsApp do seu negócio.

---

## 📋 O que você vai precisar

| Item | Onde conseguir |
|------|---------------|
| **Servidor VPS** | DigitalOcean, Contabo, Hetzner (mínimo 2GB RAM, Ubuntu 22.04) |
| **Domínio** (opcional) | Para HTTPS — qualquer registrador (Namecheap, Cloudflare) |
| **Chave da API do Google Gemini** | [Google AI Studio](https://aistudio.google.com/apikey) |
| **Número de WhatsApp** | Um chip com WhatsApp ativo (pode ser número novo) |
| **Acesso SSH ao servidor** | Terminal ou PuTTY |

---

## Parte 1 — Preparar o Servidor

### 1.1 Instalar Docker

Conecte no servidor via SSH e execute:

```bash
# Atualizar pacotes
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com | sudo sh

# Adicionar seu usuário ao grupo docker (para não usar sudo)
sudo usermod -aG docker $USER

# Aplicar a mudança (ou saia e entre novamente via SSH)
newgrp docker

# Verificar instalação
docker --version
docker compose version
```

> ⚠️ **Importante:** o Docker Compose v2 já vem junto com o Docker Engine. O comando é `docker compose` (com espaço, não hífen).

### 1.2 Baixar o Projeto

```bash
# Clonar o repositório
git clone <URL_DO_REPOSITORIO> /opt/whatsapp-agent
cd /opt/whatsapp-agent
```

---

## Parte 2 — Configurar a Evolution API

A Evolution API é o serviço que conecta o agente ao WhatsApp. Ela precisa rodar como um container separado.

### 2.1 Criar o Docker Compose da Evolution API

Crie um arquivo para a Evolution API (fora do projeto do agente):

```bash
mkdir -p /opt/evolution-api
nano /opt/evolution-api/docker-compose.yml
```

Cole o conteúdo abaixo:

```yaml
services:
  evolution-api:
    image: atendai/evolution-api:v2.2.3
    ports:
      - "8080:8080"
    environment:
      # Autenticação
      - AUTHENTICATION_API_KEY=SUA_CHAVE_SECRETA_AQUI
      
      # Banco de dados (SQLite para simplicidade)
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://postgres:senha_postgres@postgres:5432/evolution
      
      # Webhook — apontar para o agente
      - WEBHOOK_GLOBAL_URL=http://host.docker.internal:8000/api/v1/webhook/message
      - WEBHOOK_GLOBAL_ENABLED=true
      - WEBHOOK_EVENTS=MESSAGES_UPSERT
      
    volumes:
      - evolution_data:/evolution/instances
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=senha_postgres
      - POSTGRES_DB=evolution
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  evolution_data:
  postgres_data:
```

> 🔑 **Atenção:** troque `SUA_CHAVE_SECRETA_AQUI` por uma chave forte. Anote-a — você vai usar no `.env` do agente.

### 2.2 Iniciar a Evolution API

```bash
cd /opt/evolution-api
docker compose up -d
```

Verifique se está rodando:

```bash
curl http://localhost:8080/
# Deve retornar uma resposta JSON
```

### 2.3 Criar uma Instância e Conectar o WhatsApp

A Evolution API gerencia "instâncias" — cada instância é uma conexão com um número de WhatsApp.

```bash
# Criar instância chamada "minha_empresa"
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: SUA_CHAVE_SECRETA_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "minha_empresa",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true
  }'
```

A resposta conterá um **QR Code** (em base64). Para visualizar:

```bash
# Gerar QR Code para conectar
curl -X GET http://localhost:8080/instance/connect/minha_empresa \
  -H "apikey: SUA_CHAVE_SECRETA_AQUI"
```

> 📱 **Escaneie o QR Code com o WhatsApp do número que será usado pelo agente:**
> 1. Abra o WhatsApp no celular
> 2. Vá em **Configurações → Dispositivos Conectados → Conectar Dispositivo**
> 3. Escaneie o QR Code retornado pela API

### 2.4 Verificar Conexão

```bash
curl http://localhost:8080/instance/connectionState/minha_empresa \
  -H "apikey: SUA_CHAVE_SECRETA_AQUI"
```

Deve retornar `"state": "open"`.

---

## Parte 3 — Obter a Chave do Google Gemini

### 3.1 Criar Chave de API

1. Acesse [Google AI Studio](https://aistudio.google.com/apikey)
2. Faça login com sua conta Google
3. Clique em **"Create API Key"**
4. Copie a chave gerada (começa com `AIza...`)

> 💡 A API do Gemini tem um **plano gratuito** generoso para começar. Para uso em produção com volume alto, considere o plano pago.

---

## Parte 4 — Configurar o Agente

### 4.1 Criar o Arquivo de Ambiente

```bash
cd /opt/whatsapp-agent
cp .env.example .env
nano .env
```

Preencha com seus dados reais:

```ini
# Porta do agente (padrão 8000)
APP_PORT=8000
LOG_LEVEL=INFO
TENANT_CONFIG_DIR=./tenants

# Chave do Google Gemini (obtida no Passo 3)
GEMINI_API_KEY=AIzaSy_SUA_CHAVE_AQUI
GEMINI_MODEL=gemini-2.0-flash

# Redis (senha forte — invente uma)
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=minha_senha_redis_forte_123

# Qdrant (manter padrão)
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_NAME=conversations

# Evolution API (mesma chave do Passo 2)
EVOLUTION_API_URL=http://host.docker.internal:8080
EVOLUTION_API_KEY=SUA_CHAVE_SECRETA_AQUI

# Secret para webhooks (invente uma)
WEBHOOK_SECRET=meu_webhook_secret_seguro
```

### 4.2 Criar a Configuração do Seu Tenant

O "tenant" é a configuração do agente para o seu negócio. O nome da pasta é o **mesmo nome da instância** criada na Evolution API.

```bash
# Copiar o template
cp -r tenants/example_tenant tenants/minha_empresa
nano tenants/minha_empresa/settings.yaml
```

Edite o arquivo de configuração:

```yaml
agent:
  name: "Assistente da Minha Empresa"
  personality: "Simpático, objetivo e profissional"
  language: "pt-BR"
  system_prompt: |
    Você é o Assistente da Minha Empresa.
    Responda sempre em português, de forma simpática e profissional.
    
    Sobre a empresa:
    - Nome: Minha Empresa Ltda
    - Produtos: [descreva seus produtos aqui]
    - Endereço: [seu endereço]
    - Telefone: [seu telefone]
    
    Regras:
    - Nunca invente informações que você não sabe
    - Se não souber responder, peça o contato do cliente
    - Seja conciso (máximo 3 parágrafos)

topics:
  allowed:
    - suporte técnico
    - dúvidas sobre produtos
    - preços
    - horário de funcionamento
    - agendamentos
  blocked:
    - política
    - religião
    - concorrentes

business_hours:
  timezone: "America/Sao_Paulo"
  schedule:
    monday_friday: "08:00-18:00"
    saturday: "09:00-13:00"
    sunday: null
  out_of_hours_message: >
    Olá! Nosso horário de atendimento é de segunda a sexta,
    das 8h às 18h, e sábados das 9h às 13h.
    Deixe sua mensagem que responderemos assim que possível! 😊

escalation:
  trigger_keywords:
    - "falar com humano"
    - "atendente"
    - "gerente"
    - "reclamação"
  action: "message"
  message: "Vou te conectar com nossa equipe. Aguarde um momento! 🙋"

cache:
  semantic_threshold: 0.92
  ttl_hours: 24

webhooks:
  events: []
  endpoint: null
  secret: ""
```

> 💡 **Dica:** o `system_prompt` é onde você define o comportamento do agente. Quanto mais detalhado, melhor. Inclua informações sobre seus produtos, políticas de troca, preços, etc.

---

## Parte 5 — Iniciar o Agente

### 5.1 Subir os Serviços

```bash
cd /opt/whatsapp-agent
docker compose up -d
```

Aguarde uns 30 segundos e verifique:

```bash
# Ver status dos containers
docker compose ps

# Verificar saúde do sistema
curl http://localhost:8000/health
```

Resposta esperada:

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

### 5.2 Verificar se o Tenant Está Carregado

```bash
curl http://localhost:8000/api/v1/admin/tenants
```

Deve mostrar:

```json
{
  "count": 1,
  "tenants": ["minha_empresa"]
}
```

---

## Parte 6 — Testar

### 6.1 Teste Manual via WhatsApp

1. Pegue **outro celular** (ou peça para alguém)
2. Envie uma mensagem para o **número conectado à Evolution API**
3. O agente deve responder automaticamente! 🎉

### 6.2 Teste via API (sem WhatsApp)

```bash
curl -X POST http://localhost:8000/api/v1/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "instance": "minha_empresa",
    "phone": "5511999999999",
    "message": "Qual o horário de funcionamento?"
  }'
```

---

## Parte 7 — Monitoramento

### Ver Logs em Tempo Real

```bash
# Logs do agente
docker compose logs -f app

# Logs de todos os serviços
docker compose logs -f
```

### Ver Webhooks Recebidos

```bash
curl http://localhost:8000/api/v1/admin/webhooks/received
```

---

## ❓ Problemas Comuns

### "Tenant not found" (404)

O nome da pasta em `tenants/` deve ser **exatamente igual** ao nome da instância na Evolution API. Se a instância se chama `minha_empresa`, a pasta deve ser `tenants/minha_empresa/`.

### QR Code expirou

Execute novamente o comando de conexão:
```bash
curl http://localhost:8080/instance/connect/minha_empresa \
  -H "apikey: SUA_CHAVE_SECRETA_AQUI"
```

### Agente não responde

1. Verifique os logs: `docker compose logs -f app`
2. Verifique se a Evolution API está conectada: `curl http://localhost:8080/instance/connectionState/minha_empresa -H "apikey: SUA_CHAVE"`
3. Verifique o health check: `curl http://localhost:8000/health`

### Redis ou Qdrant "down" no health check

```bash
# Reiniciar serviço com problema
docker compose restart redis
# ou
docker compose restart qdrant
```

### Atualizar configuração do agente sem reiniciar

```bash
# Edite o arquivo
nano tenants/minha_empresa/settings.yaml

# Recarregue
curl -X POST http://localhost:8000/api/v1/admin/tenants/minha_empresa/reload
```

---

## 📞 Próximos Passos

1. **Personalize o system_prompt** com FAQ, informações de produtos, políticas
2. **Configure webhooks** se quiser receber notificações no seu sistema
3. **Ajuste o horário de atendimento** para o seu negócio
4. **Configure HTTPS** com Nginx ou Caddy para segurança em produção
5. **Monitore os logs** nas primeiras semanas para ajustar o comportamento

---

> 📌 **Suporte técnico:** entre em contato com a equipe de suporte para dúvidas sobre configuração avançada.
