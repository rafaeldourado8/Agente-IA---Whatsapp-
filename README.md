# 🤖 WhatsApp B2B AI Agent

Agente de IA para atendimento ao cliente via WhatsApp.  
Multi-tenant, com cache semântico, memória de conversa e configuração por cliente via YAML.

---

## ⚡ Início Rápido (5 minutos)

### Pré-requisitos

- **Docker Desktop** instalado ([Download](https://www.docker.com/products/docker-desktop/))
- **Chave da API Google Gemini** ([Obter grátis](https://aistudio.google.com/apikey))

### Passo a passo

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd whatsapp-agent

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env e coloque sua GEMINI_API_KEY

# 3. Suba todos os serviços
docker compose up -d

# 4. Verifique se está tudo rodando
# Windows PowerShell:
Invoke-RestMethod http://localhost:8000/health
# Linux/macOS:
curl http://localhost:8000/health
```

Você deve ver:
```json
{
  "status": "healthy",
  "services": {
    "redis": "up",
    "qdrant": "up",
    "waha": "up"
  }
}
```

### 5. Conecte seu WhatsApp

Acesse o painel do WAHA em `http://localhost:3000/dashboard` e escaneie o QR Code.  
Veja detalhes em [📱 Configuração do WAHA](docs/02-configuracao-waha.md).

---

## 🏗️ Arquitetura

```
Usuário WhatsApp → WAHA → FastAPI App → Cache/AI/Qdrant → Resposta
```

| Componente | Tecnologia | Função |
|-----------|-----------|--------|
| **Backend** | FastAPI (Python 3.12) | API REST, webhooks, orquestração |
| **IA** | Google Gemini 2.0 Flash | Geração de respostas inteligentes |
| **Cache** | Redis 7 | Cache semântico (reduz custo 40–70%) |
| **Memória** | Qdrant | Histórico vetorial de conversas |
| **WhatsApp** | WAHA | Gateway HTTP para WhatsApp |
| **Deploy** | Docker Compose | Infraestrutura containerizada |

---

## ✨ Funcionalidades

| Feature | Descrição |
|---------|-----------|
| 🧠 **Cache Semântico** | Perguntas similares recebem respostas instantâneas do cache |
| 🎨 **Multimodal** | Processa imagens e áudio além de texto |
| 🏢 **Multi-tenant** | Cada cliente tem config, cache e histórico isolados |
| ⏰ **Horário Comercial** | Mensagem automática fora do expediente |
| 🚨 **Escalação** | Palavras-chave transferem para humano via webhook |
| 🔗 **Webhooks** | Notificações de eventos com assinatura HMAC |
| 📊 **Health Checks** | Monitora Redis, Qdrant e WAHA |
| 🐳 **Docker-native** | Deploy com um único comando |

---

## 📚 Documentação Completa

| Guia | Descrição |
|------|-----------|
| [📦 Instalação Local](docs/01-instalacao-local.md) | Setup completo para Windows, Linux e macOS |
| [📱 Configuração do WAHA](docs/02-configuracao-waha.md) | Conectar WhatsApp, QR Code, sessões |
| [🤖 Configuração do Agente](docs/03-configuracao-agente.md) | Prompts, horários, escalação, cache |
| [🖥️ Deploy em VPS](docs/04-deploy-vps.md) | Deploy em qualquer VPS (DigitalOcean, Hostinger, etc.) |
| [☁️ Deploy na AWS EC2](docs/05-deploy-aws-ec2.md) | Deploy passo a passo na Amazon EC2 |
| [🔧 Troubleshooting](docs/06-troubleshooting.md) | Problemas comuns e soluções |
| [🎨 Suporte Multimodal](docs/07-multimodal-support.md) | Processamento de imagens e áudio |

---

## 🔌 Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Status dos serviços |
| `POST` | `/api/v1/webhook/waha` | Recebe mensagens do WAHA (produção) |
| `POST` | `/api/v1/webhook/message` | Recebe mensagens (teste manual) |
| `GET` | `/api/v1/admin/tenants` | Lista todos os tenants |
| `GET` | `/api/v1/admin/tenants/{id}` | Config de um tenant |
| `POST` | `/api/v1/admin/tenants/{id}/reload` | Recarrega config do tenant |
| `POST` | `/api/v1/admin/tenants/reload-all` | Limpa cache de configs |

Documentação interativa disponível em: `http://localhost:8000/docs`

---

## 🛠️ Desenvolvimento

```bash
# Instalar dependências de desenvolvimento
pip install -e ".[dev]"

# Rodar testes
pytest tests/ -v

# Lint
ruff check app/

# Type check
mypy app/
```

---

## 📄 Licença

Proprietário — todos os direitos reservados.
