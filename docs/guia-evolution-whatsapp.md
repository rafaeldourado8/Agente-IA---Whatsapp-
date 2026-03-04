# 📱 Guia de Configuração — Evolution API + WhatsApp

> Como instalar a Evolution API e conectar seu número de WhatsApp ao agente.

---

## ❓ Preciso Criar Conta?

**NÃO!** A Evolution API é um software **open-source** que roda no **seu próprio servidor**. 

- ❌ Não precisa de conta
- ❌ Não precisa de cadastro
- ❌ Não precisa de licença
- ❌ Não paga nada para a Evolution
- ✅ Só precisa de Docker instalado

A única coisa que você precisa é um **número de WhatsApp** (pode ser chip novo).

---

## Parte 1 — Instalar a Evolution API

### 1.1 Criar Pasta e Docker Compose

No seu servidor (EC2, VPS, ou máquina local):

```bash
sudo mkdir -p /opt/evolution-api
sudo chown -R $USER:$USER /opt/evolution-api
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
      # Chave de acesso — INVENTE uma chave forte
      - AUTHENTICATION_API_KEY=MinhaChaveSuperSecreta123
      
      # Banco de dados
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://postgres:EvoPgSenha2026Forte@postgres:5432/evolution
      
      # Cache Redis (recomendado para performance)
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://redis-evo:6379
      - CACHE_LOCAL_ENABLED=false
      
      # Webhook — envia mensagens recebidas para o agente
      # Na AWS/Linux: usar IP do Docker bridge (172.17.0.1)
      # No Windows/Mac: usar host.docker.internal
      - WEBHOOK_GLOBAL_URL=http://172.17.0.1:8000/api/v1/webhook/message
      - WEBHOOK_GLOBAL_ENABLED=true
      - WEBHOOK_EVENTS=MESSAGES_UPSERT
      
    volumes:
      - evolution_data:/evolution/instances
    depends_on:
      - postgres
      - redis-evo
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=EvoPgSenha2026Forte
      - POSTGRES_DB=evolution
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis-evo:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  evolution_data:
  postgres_data:
```

> [!CAUTION]
> **Senha do Postgres:** NÃO use caracteres especiais como `@`, `#`, `!`, `&` na senha.
> Esses caracteres quebram a URL de conexão do Prisma.
> Use apenas letras, números e underscores (ex: `EvoPgSenha2026Forte`).

> [!IMPORTANT]
> Troque `MinhaChaveSuperSecreta123` por uma chave forte de verdade.
> Você vai usar essa mesma chave no `.env` do agente como `EVOLUTION_API_KEY`.

### 1.2 Sobre o Redis

A Evolution API v2 usa Redis para cache de sessões e instâncias. O docker-compose acima já inclui um container `redis-evo` dedicado para isso.

> [!NOTE]
> Este Redis é **separado** do Redis do agente. Cada um roda em seu próprio docker-compose com volumes independentes.

**Se seu servidor tiver pouca RAM (≤ 1GB)**, você pode desabilitar o Redis trocando as variáveis:
```yaml
      - CACHE_REDIS_ENABLED=false
      - CACHE_REDIS_URI=
      - CACHE_LOCAL_ENABLED=true
```
E remover o serviço `redis-evo` do docker-compose.

### 1.3 Webhook URL — Linux vs Windows/Mac

| Ambiente | URL do Webhook |
|----------|---------------|
| **AWS EC2 / Linux / VPS** | `http://172.17.0.1:8000/api/v1/webhook/message` |
| **Windows / Mac (Docker Desktop)** | `http://host.docker.internal:8000/api/v1/webhook/message` |

> O `172.17.0.1` é o gateway padrão do Docker bridge no Linux. O `host.docker.internal` só existe no Docker Desktop (Windows/Mac).

### 1.4 Iniciar

```bash
cd /opt/evolution-api
docker compose up -d
```

Aguarde ~30 segundos e teste:

```bash
curl http://localhost:8080/
```

Se retornar um JSON, a Evolution API está rodando! ✅

Verifique os logs para confirmar que não há erros:

```bash
docker compose logs -f
```

Deve aparecer `HTTP - ON: 8080` sem erros de Redis.

> [!TIP]
> Se aparecer `Permission denied` ao criar arquivos em `/opt`, use:
> ```bash
> sudo chown -R $USER:$USER /opt/evolution-api
> ```

---

## Parte 2 — Criar Instância do WhatsApp

Uma "instância" é a conexão com um número de WhatsApp. Cada cliente/tenant pode ter sua própria instância.

### 2.1 Criar a Instância

```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: MinhaChaveSuperSecreta123" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "minha_empresa",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true
  }'
```

> 📌 O `instanceName` aqui deve ser o **mesmo nome** da pasta do tenant em `tenants/minha_empresa/`.

Resposta esperada:
```json
{
  "instance": {
    "instanceName": "minha_empresa",
    "status": "created"
  },
  "qrcode": {
    "code": "2@ABC123...",
    "base64": "data:image/png;base64,iVBOR..."
  }
}
```

---

## Parte 3 — Conectar o WhatsApp (Escanear QR Code)

### Opção A: Via Navegador (mais fácil)

Se você está acessando o servidor remotamente, abra no navegador:

```
http://SEU_IP:8080/manager
```

> ⚠️ A porta 8080 precisa estar aberta no Security Group da AWS (apenas para o seu IP por segurança).

Nessa interface web você vai ver a instância criada e pode gerar o QR Code clicando nela.

### Opção B: Via Terminal

```bash
# Gerar QR Code
curl http://localhost:8080/instance/connect/minha_empresa \
  -H "apikey: MinhaChaveSuperSecreta123"
```

A resposta terá o QR Code em base64. Para visualizar, copie o valor do campo `base64` e cole em qualquer conversor online de base64 para imagem (ex: [base64-image.de](https://www.base64-image.de/)).

### Escanear no Celular

1. Abra o **WhatsApp** no celular com o número que será do agente
2. Toque em **⋮ (três pontinhos)** → **Dispositivos Conectados**
3. Toque em **Conectar Dispositivo**
4. Escaneie o QR Code

### Verificar Conexão

```bash
curl http://localhost:8080/instance/connectionState/minha_empresa \
  -H "apikey: MinhaChaveSuperSecreta123"
```

Resposta esperada:
```json
{
  "instance": "minha_empresa",
  "state": "open"
}
```

Se aparecer `"state": "open"`, o WhatsApp está conectado! ✅

---

## Parte 4 — Testar a Conexão

### 4.1 Enviar Mensagem de Teste (via API)

Envie uma mensagem para outro número para confirmar que funciona:

```bash
curl -X POST http://localhost:8080/message/sendText/minha_empresa \
  -H "apikey: MinhaChaveSuperSecreta123" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "text": "Olá! Teste do agente de IA 🤖"
  }'
```

> 📱 Substitua `5511999999999` por um número real (com DDD, sem +).

Se a pessoa receber a mensagem, está tudo funcionando!

### 4.2 Testar Recebimento (Webhook)

Quando alguém enviar uma mensagem para o número conectado, a Evolution API vai enviar um POST para o webhook configurado.

Para testar antes de ter o agente rodando:

```bash
# Subir um receptor temporário na porta 8000
python3 -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(length))
        print(json.dumps(body, indent=2))
        self.send_response(200)
        self.end_headers()

HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
"
```

Agora envie uma mensagem para o número do WhatsApp de outro celular. Você verá o payload do webhook no terminal.

---

## Parte 5 — Conectar com o Agente

Agora que a Evolution API está rodando e o WhatsApp conectado, certifique-se que no `.env` do agente:

```ini
# AWS/Linux: usar IP do Docker bridge
EVOLUTION_API_URL=http://172.17.0.1:8080

# Windows/Mac: usar host.docker.internal
# EVOLUTION_API_URL=http://host.docker.internal:8080

# Mesma chave definida no docker-compose da Evolution
EVOLUTION_API_KEY=MinhaChaveSuperSecreta123
```

E que a pasta do tenant tem o **mesmo nome** da instância:

```
tenants/
└── minha_empresa/        ← mesmo nome da instanceName
    └── settings.yaml
```

Inicie o agente:

```bash
cd /opt/whatsapp-agent
docker compose up -d
```

Envie uma mensagem para o número do WhatsApp → o agente responde automaticamente! 🎉

---

## ❓ Perguntas Frequentes

### O QR Code expirou, o que faço?

Gere um novo:
```bash
curl http://localhost:8080/instance/connect/minha_empresa \
  -H "apikey: MinhaChaveSuperSecreta123"
```

### O WhatsApp desconectou do nada

Isso pode acontecer se o celular ficar sem internet por muito tempo. Reconecte:
```bash
# Ver estado
curl http://localhost:8080/instance/connectionState/minha_empresa \
  -H "apikey: MinhaChaveSuperSecreta123"

# Se estiver "close", reconectar
curl http://localhost:8080/instance/connect/minha_empresa \
  -H "apikey: MinhaChaveSuperSecreta123"
```

### Erro "redis disconnected" nos logs

A Evolution API v2 requer Redis. Certifique-se de que o container `redis-evo` está rodando:
```bash
cd /opt/evolution-api
docker compose ps
docker compose restart redis-evo
```

### Erro "invalid port number in database URL"

A senha do Postgres contém caracteres especiais (`@`, `#`, `!`, `&`) que quebram a URL. Troque por uma senha contendo apenas letras e números:
```bash
docker compose down
# Remover volume antigo
docker volume rm evolution-api_postgres_data
# Editar, trocar senha, e subir de novo
nano docker-compose.yml
docker compose up -d
```

### Erro "Permission denied" no nano

Use `sudo` ou mude o dono da pasta:
```bash
sudo chown -R $USER:$USER /opt/evolution-api
```

### Posso usar mais de um número de WhatsApp?

Sim! Crie uma nova instância para cada número:
```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: MinhaChaveSuperSecreta123" \
  -H "Content-Type: application/json" \
  -d '{"instanceName": "outro_cliente", "integration": "WHATSAPP-BAILEYS", "qrcode": true}'
```

E crie a pasta correspondente `tenants/outro_cliente/settings.yaml`.

### Posso usar o WhatsApp normalmente no celular?

Sim! A Evolution API funciona como um **dispositivo conectado** (igual ao WhatsApp Web). O celular continua funcionando normalmente.

### O agente responde a todas as mensagens?

Sim, a todas que chegam naquele número. Se quiser filtrar (exemplo: não responder a grupos), configure no `settings.yaml` ou nos filtros do webhook.

### Quanto custa a Evolution API?

**R$ 0 (zero)**. É open-source, MIT license. Você só paga pela infraestrutura (servidor, internet).

---

## 📋 Resumo Rápido

```
1. docker compose up -d              ← Sobe a Evolution API + Redis + Postgres
2. curl POST /instance/create        ← Cria instância "minha_empresa"  
3. curl GET /instance/connect/...    ← Pega QR Code
4. 📱 Escaneia no WhatsApp           ← Conecta o número
5. Configura .env do agente          ← Aponta para a Evolution API
6. docker compose up -d (agente)     ← Sobe o agente
7. Envia mensagem → agente responde! ← 🎉 Funcionando
```
