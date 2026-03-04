  # 🚀 Guia de Ativação — Seu Agente de IA no WhatsApp

> Este guia vai te levar do zero até o seu agente funcionando no WhatsApp em **7 passos simples**.
> Tempo estimado: **30–45 minutos**.

---

## 📖 O que é este produto?

É um **robô de atendimento** que responde automaticamente as mensagens do WhatsApp da sua empresa. Ele usa inteligência artificial (Google Gemini) para entender o que o cliente pergunta e dar respostas personalizadas com base nos dados que você configura.

**Exemplo prático:**
- 👤 Cliente: *"Qual o horário de funcionamento?"*
- 🤖 Agente: *"Olá! Funcionamos de segunda a sexta, das 8h às 18h, e sábados das 9h às 13h. Posso ajudar com mais alguma coisa?"*

O agente funciona 24 horas — fora do horário comercial, ele avisa que está fechado e pede para o cliente deixar uma mensagem.

---

## 📋 O que você vai precisar

Antes de começar, tenha em mãos:

| Item | O que é | Como conseguir |
|------|---------|---------------|
| 🖥️ **Servidor** | Um computador na nuvem que fica ligado 24h | Contratar na AWS, DigitalOcean ou similar (~R$75–225/mês) |
| 📱 **Chip de celular** | Um número de WhatsApp para o agente usar | Comprar um chip pré-pago normal |
| 🔑 **Chave do Google** | Permissão para usar a inteligência artificial | Gratuito — vamos criar juntos no Passo 3 |

> 💡 **O que é um servidor?** Pense nele como um computador que fica ligado o tempo todo na internet. Ao invés de deixar o seu computador pessoal ligado, você "aluga" um na nuvem. É como alugar um escritório virtual para o robô trabalhar.

---

## Passo 1 — Contratar e Acessar o Servidor

### O que vamos fazer?
Alugar um computador na nuvem e conectar nele remotamente.

### Como fazer (AWS):

1. Acesse [console.aws.amazon.com](https://console.aws.amazon.com) e crie uma conta (se ainda não tem)
2. No menu, vá em **EC2** → **Launch Instance**
3. Configure:
   - **Nome:** `whatsapp-agent`
   - **Sistema operacional:** Ubuntu Server 24.04 LTS
   - **Tipo:** `t3.small` (2GB RAM) ou `c7i-flex.large` (4GB RAM, recomendado)
   - **Key pair:** Crie uma nova (será um arquivo `.pem` — **guarde bem, você vai precisar!**)
   - **Disco:** 30 GB
4. Em **Security Group** (firewall), libere estas portas:

| Porta | Para que serve |
|:-----:|---------------|
| 22 | Você acessar o servidor remotamente |
| 8000 | O agente de IA funcionar |
| 8080 | Configurar a conexão com o WhatsApp (apenas seu IP!) |

5. Clique em **Launch Instance**

### Conectar no servidor:

No terminal do seu computador (ou PuTTY no Windows):

```bash
ssh -i whatsapp-agent-key.pem ubuntu@IP_DO_SEU_SERVIDOR
```

> 💡 **O que é SSH?** É um jeito seguro de "entrar" no servidor pela internet, como se você estivesse sentado na frente dele. Tudo que você digitar será executado lá.

---

## Passo 2 — Instalar o Docker

### O que vamos fazer?
Instalar o programa que vai rodar todos os serviços do agente de forma organizada.

### Por que Docker?
O Docker é como uma "caixinha" que embala o agente e tudo que ele precisa. Ao invés de instalar dezenas de programas, instalamos só o Docker e ele cuida do resto.

### Como fazer:

Cole estes comandos no terminal (um de cada vez):

```bash
# Atualizar o sistema
sudo apt update && sudo apt upgrade -y

# Instalar o Docker
curl -fsSL https://get.docker.com | sudo sh

# Permitir usar Docker sem 'sudo'
sudo usermod -aG docker ubuntu
newgrp docker

# Verificar se instalou corretamente
docker --version
```

Deve aparecer algo como `Docker version 29.x.x` ✅

> ⚠️ **Se der algum erro**, tente sair do servidor (`exit`) e entrar novamente (`ssh ...`).

---

## Passo 3 — Criar Chave do Google Gemini (Gratuito)

### O que vamos fazer?
Pegar a "chave de acesso" para o agente poder usar a inteligência artificial do Google.

### Por que precisa disso?
O Google oferece um serviço de IA chamado Gemini. Para usar, você precisa de uma chave que identifica a sua conta. É gratuito para volumes moderados.

### Como fazer:

1. Acesse [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Faça login com qualquer conta Google (Gmail)
3. Clique em **"Create API Key"**
4. **Copie a chave** que aparece (começa com `AIza...`)
5. **Guarde essa chave** — você vai usar no Passo 5

> ⚠️ **Nunca compartilhe esta chave** com ninguém. Ela é como uma senha.

---

## Passo 4 — Conectar o WhatsApp

### O que vamos fazer?
Instalar o serviço que conecta o agente ao WhatsApp e escanear o QR Code com o celular.

### Como funciona?
Usamos um programa chamado **Evolution API** (gratuito e open-source) que funciona igual ao WhatsApp Web — ele conecta um número de WhatsApp ao servidor. Não precisa criar conta, é só instalar.

### 4.1 — Criar a pasta e o arquivo de configuração:

```bash
sudo mkdir -p /opt/evolution-api
sudo chown -R ubuntu:ubuntu /opt/evolution-api
nano /opt/evolution-api/docker-compose.yml
```

O comando `nano` vai abrir um editor de texto. Cole este conteúdo:

```yaml
services:
  evolution-api:
    image: atendai/evolution-api:v2.2.3
    ports:
      - "8080:8080"
    environment:
      - AUTHENTICATION_API_KEY=MinhaChaveEvolution123
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://postgres:EvoPgSenha2026Forte@postgres:5432/evolution
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://redis-evo:6379
      - CACHE_LOCAL_ENABLED=false
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

**Para salvar:** aperte `Ctrl+O` → `Enter` → `Ctrl+X`

> ⚠️ **Sobre as senhas:**
> - Troque `MinhaChaveEvolution123` por uma chave inventada por você (anote!)
> - Troque `EvoPgSenha2026Forte` por uma senha inventada por você (anote!)  
> - **NÃO use** caracteres especiais como `@`, `#`, `!`, `&` nas senhas — use apenas letras e números

### 4.2 — Iniciar a Evolution API:

```bash
cd /opt/evolution-api
docker compose up -d
```

Aguarde ~1 minuto. Verifique se está rodando:

```bash
docker compose logs --tail 20
```

Deve aparecer `HTTP - ON: 8080` sem erros repetidos ✅

### 4.3 — Criar conexão com o WhatsApp:

```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: MinhaChaveEvolution123" \
  -H "Content-Type: application/json" \
  -d '{"instanceName": "minha_empresa", "integration": "WHATSAPP-BAILEYS", "qrcode": true}'
```

> 📌 **`minha_empresa`** é o identificador do seu negócio. Troque pelo nome da sua empresa (sem espaços, sem acentos). Ex: `padaria_silva`, `clinica_saude`, `loja_roupas`

### 4.4 — Escanear o QR Code:

Abra no navegador do seu computador:

```
http://IP_DO_SEU_SERVIDOR:8080/manager
```

Você verá a instância que acabou de criar. Clique nela para ver o **QR Code**.

No celular com o número que será do agente:
1. Abra o **WhatsApp**
2. Vá em **⋮ → Dispositivos Conectados → Conectar Dispositivo**
3. **Escaneie o QR Code** que aparece no navegador

### 4.5 — Verificar se conectou:

```bash
curl http://localhost:8080/instance/connectionState/minha_empresa \
  -H "apikey: MinhaChaveEvolution123"
```

Se aparecer `"state": "open"` → WhatsApp conectado! ✅

> 💡 **Dica:** o WhatsApp continua funcionando normalmente no celular. A Evolution API funciona como mais um "dispositivo conectado", igual ao WhatsApp Web.

---

## Passo 5 — Configurar o Agente

### O que vamos fazer?
Baixar o código do agente e preencher as configurações com seus dados.

### 5.1 — Baixar o projeto:

```bash
sudo mkdir -p /opt/whatsapp-agent
sudo chown -R ubuntu:ubuntu /opt/whatsapp-agent
git clone <URL_DO_REPOSITORIO> /opt/whatsapp-agent
cd /opt/whatsapp-agent
```

### 5.2 — Criar o arquivo de configuração geral:

```bash
cp .env.example .env
nano .env
```

Preencha com seus dados (troque os valores em MAIÚSCULAS):

```ini
# Configuração geral
APP_PORT=8000
LOG_LEVEL=INFO
TENANT_CONFIG_DIR=./tenants

# Google Gemini (chave do Passo 3)
GEMINI_API_KEY=COLE_SUA_CHAVE_AQUI
GEMINI_MODEL=gemini-2.0-flash

# Banco de cache (pode manter assim)
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=MinhasenhaRedisForte123

# Banco de memória (pode manter assim)
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_NAME=conversations

# Evolution API (mesma chave do Passo 4)
EVOLUTION_API_URL=http://172.17.0.1:8080
EVOLUTION_API_KEY=MinhaChaveEvolution123

# Segurança dos webhooks
WEBHOOK_SECRET=MeuWebhookSecreto456
```

**Salve:** `Ctrl+O` → `Enter` → `Ctrl+X`

> 💡 **O que cada coisa faz:**
> - **GEMINI_API_KEY** → chave para o agente "pensar" (Google Gemini)
> - **REDIS** → memória rápida que evita o agente pensar a mesma coisa duas vezes (cache)
> - **QDRANT** → onde o agente guarda o histórico das conversas
> - **EVOLUTION_API** → conexão com o WhatsApp

### 5.3 — Configurar o perfil do agente:

Esta é a parte mais importante! Aqui você define **quem** o agente é e **o que** ele sabe.

```bash
cp -r tenants/example_tenant tenants/minha_empresa
nano tenants/minha_empresa/settings.yaml
```

> ⚠️ O nome da pasta (`minha_empresa`) deve ser **exatamente igual** ao nome da instância criada no Passo 4.

Edite o arquivo com os dados do seu negócio:

```yaml
# ===================================================
# IDENTIDADE DO AGENTE
# Aqui você define a personalidade e o conhecimento
# ===================================================
agent:
  # Nome que aparece como remetente
  name: "Assistente Virtual da Minha Empresa"
  
  # Como o agente se comporta
  personality: "Simpático, prestativo e profissional"
  
  # Idioma
  language: "pt-BR"
  
  # INSTRUÇÕES DO AGENTE — a parte mais importante!
  # Tudo que está aqui o agente vai "saber" e seguir.
  # Quanto mais detalhado, melhor ele responde.
  system_prompt: |
    Você é o assistente virtual da Minha Empresa.
    Sempre responda em português, de forma simpática e profissional.
    
    SOBRE A EMPRESA:
    - Nome: Minha Empresa Ltda
    - Ramo: [descreva o ramo do negócio]
    - Endereço: [endereço completo]
    - Telefone fixo: [número]
    - E-mail: [email]
    - Site: [url]
    
    PRODUTOS/SERVIÇOS:
    - [Liste cada produto/serviço com preço]
    - [Quanto mais detalhes, melhor]
    
    POLÍTICAS:
    - Trocas: [política de troca]
    - Pagamento: [formas aceitas]
    - Entrega: [prazos e condições]
    
    REGRAS DE COMPORTAMENTO:
    - Nunca invente informações que não estão acima
    - Se não souber responder, diga: "Vou verificar com nossa equipe e retorno em breve!"
    - Seja conciso (máximo 3 parágrafos por resposta)
    - Use emojis com moderação (1-2 por mensagem)
    - Nunca fale mal de concorrentes
    - Não discuta política, religião ou assuntos polêmicos

# ===================================================
# ASSUNTOS PERMITIDOS E BLOQUEADOS
# Define sobre o que o agente pode e não pode falar
# ===================================================
topics:
  allowed:
    - dúvidas sobre produtos
    - preços e promoções
    - horário de funcionamento
    - endereço e localização
    - formas de pagamento
    - status de pedidos
    - agendamentos
  blocked:
    - política
    - religião
    - assuntos pessoais
    - concorrentes

# ===================================================
# HORÁRIO DE ATENDIMENTO
# Fora desse horário, o agente avisa que está fechado
# ===================================================
business_hours:
  timezone: "America/Sao_Paulo"
  schedule:
    # Formato: "HH:MM-HH:MM" (24 horas)
    monday_friday: "08:00-18:00"   # Seg-Sex: 8h às 18h
    saturday: "09:00-13:00"        # Sábado: 9h às 13h
    sunday: null                    # Domingo: fechado (null = fechado)
  
  # Mensagem automática fora do horário
  out_of_hours_message: >
    Olá! 😊 Nosso horário de atendimento é de segunda a sexta,
    das 8h às 18h, e sábados das 9h às 13h.
    Deixe sua mensagem que responderemos no próximo dia útil!

# ===================================================
# ATENDIMENTO HUMANO
# Quando o cliente pedir para falar com uma pessoa
# ===================================================
escalation:
  # Palavras que ativam o encaminhamento para humano
  trigger_keywords:
    - "falar com humano"
    - "falar com atendente"
    - "falar com pessoa"
    - "gerente"
    - "reclamação"
    - "insatisfeito"
  
  action: "message"
  
  # Mensagem que o agente envia quando o cliente quer falar com humano
  message: >
    Entendo! Vou encaminhar você para nossa equipe de atendimento.
    Um atendente humano vai entrar em contato em breve. 
    Obrigado pela paciência! 🙋

# ===================================================
# CACHE (Performance)
# Perguntas parecidas recebem a mesma resposta sem
# gastar com IA — economiza até 70% dos custos!
# ===================================================
cache:
  semantic_threshold: 0.92   # Quão parecida a pergunta precisa ser (0.0–1.0)
  ttl_hours: 24              # Quanto tempo a resposta fica no cache (em horas)

# ===================================================
# WEBHOOKS (Integrações)
# Se você quer receber notificações no seu sistema
# Deixe vazio se não precisar
# ===================================================
webhooks:
  events: []
  endpoint: null
  secret: ""
```

**Salve:** `Ctrl+O` → `Enter` → `Ctrl+X`

> 💡 **Dica importante:** o `system_prompt` é o cérebro do agente. Ele só sabe o que está escrito ali. Se você quer que ele responda sobre preços, coloque os preços. Se quer que ele saiba o endereço, escreva o endereço. Quanto mais informação, melhor!

---

## Passo 6 — Iniciar o Agente

### O que vamos fazer?
Ligar o agente e todos os serviços necessários.

```bash
cd /opt/whatsapp-agent
docker compose up -d
```

Aguarde ~1 minuto e verifique:

```bash
# Ver se todos os serviços estão "running"
docker compose ps

# Verificar a saúde do sistema
curl http://localhost:8000/health
```

Resultado esperado:
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

Se todos aparecem como `"up"` → está tudo funcionando! ✅

```bash
# Ver se o agente reconhece seu tenant
curl http://localhost:8000/api/v1/admin/tenants
```

Deve mostrar o nome da sua empresa na lista.

---

## Passo 7 — Testar!

### Teste 1: Enviar mensagem pelo WhatsApp

1. Pegue **outro celular** (não o que está conectado ao agente)
2. Envie uma mensagem para o **número do agente**
3. Aguarde a resposta automática (pode levar 3–10 segundos na primeira vez)

### Teste 2: Verificar pelo terminal

```bash
# Ver os logs em tempo real (Ctrl+C para sair)
docker compose logs -f app
```

Você verá cada mensagem recebida e a resposta gerada pelo agente.

### Teste 3: Testar direto pela API (sem precisar de WhatsApp)

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

## ✅ Pronto! Seu agente está no ar!

A partir de agora, toda mensagem que chegar no WhatsApp será respondida automaticamente pela IA.

---

## 🔧 Operações do Dia a Dia

### Alterar as informações do agente

Se mudou o preço, horário ou qualquer informação:

```bash
# 1. Editar o arquivo
nano /opt/whatsapp-agent/tenants/minha_empresa/settings.yaml

# 2. Recarregar (sem reiniciar!)
curl -X POST http://localhost:8000/api/v1/admin/tenants/minha_empresa/reload
```

### Ver os logs (o que o agente está fazendo)

```bash
cd /opt/whatsapp-agent
docker compose logs -f app
```

Aperte `Ctrl+C` para sair dos logs.

### Reiniciar o agente (se algo não estiver funcionando)

```bash
cd /opt/whatsapp-agent
docker compose restart
```

### Ver quantos tenants estão configurados

```bash
curl http://localhost:8000/api/v1/admin/tenants
```

---

## ❓ Problemas Comuns

### "O agente não responde nenhuma mensagem"

1. Verifique se o WhatsApp está conectado:
   ```bash
   curl http://localhost:8080/instance/connectionState/minha_empresa \
     -H "apikey: MinhaChaveEvolution123"
   ```
   Se mostrar `"close"`, reconecte escaneando o QR Code novamente.

2. Verifique os logs do agente:
   ```bash
   cd /opt/whatsapp-agent
   docker compose logs --tail 50 app
   ```

### "Tenant not found" (404)

O nome da pasta em `tenants/` está diferente do nome da instância na Evolution API.
- Pasta: `tenants/minha_empresa/`
- Instância: `minha_empresa`
Devem ser **exatamente iguais**.

### "O agente dá respostas erradas"

Melhore o `system_prompt` no `settings.yaml`:
- Adicione mais informações sobre seus produtos
- Seja mais específico nas regras
- Adicione exemplos de perguntas e respostas

### "O servidor está lento"

```bash
# Ver uso de memória
docker stats --no-stream
```

Se a memória estiver no limite, considere um servidor maior.

### "O QR Code expirou"

Gere um novo:
```bash
curl http://localhost:8080/instance/connect/minha_empresa \
  -H "apikey: MinhaChaveEvolution123"
```

---

## 📚 Glossário

| Termo | O que significa |
|-------|----------------|
| **Docker** | Programa que roda aplicações em "caixinhas" isoladas |
| **Container** | Uma "caixinha" rodando um serviço (agente, Redis, etc.) |
| **Terminal** | Tela preta onde digitamos comandos |
| **SSH** | Forma segura de acessar um servidor pela internet |
| **API** | Forma de programas conversarem entre si |
| **Webhook** | Aviso automático que um programa envia para outro |
| **QR Code** | Código 2D que você escaneia com a câmera do celular |
| **Tenant** | Configuração de um cliente (cada empresa = 1 tenant) |
| **Cache** | Memória rápida que guarda respostas para reutilizar |
| **System Prompt** | Instruções que definem o comportamento da IA |
| **Redis** | Banco de dados super-rápido usado para cache |
| **Qdrant** | Banco de dados que guarda o histórico das conversas |
| **Evolution API** | Programa gratuito que conecta ao WhatsApp |

---

> 📞 **Precisa de ajuda?** Entre em contato com o suporte técnico para dúvidas sobre configuração ou comportamento do agente.
