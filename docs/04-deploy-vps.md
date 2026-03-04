# 🖥️ Deploy em VPS (Servidor Virtual)

Guia completo para colocar o agente em produção em qualquer VPS.  
Funciona em **DigitalOcean**, **Hostinger**, **Contabo**, **Hetzner**, **Vultr**, etc.

---

## Requisitos do Servidor

| Requisito | Mínimo | Recomendado |
|-----------|--------|-------------|
| **CPU** | 1 vCPU | 2 vCPUs |
| **RAM** | 2 GB | 4 GB |
| **Disco** | 20 GB SSD | 40 GB SSD |
| **Sistema** | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| **Rede** | IP público | IP público + domínio |

> [!TIP]
> Para começar, um VPS de **R$ 25–50/mês** é suficiente para até ~500 conversas/dia.

---

## Passo 1: Acessar o Servidor

### Windows
Use o **PowerShell** ou baixe o [PuTTY](https://www.putty.org/):

```powershell
ssh root@SEU_IP_DO_SERVIDOR
```

### Linux / macOS
```bash
ssh root@SEU_IP_DO_SERVIDOR
```

> [!TIP]
> Substitua `SEU_IP_DO_SERVIDOR` pelo IP que o provedor te deu (ex: `143.198.50.100`).

---

## Passo 2: Preparar o Servidor

Execute todos os comandos abaixo no terminal do servidor:

```bash
# Atualizar o sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar dependências essenciais
sudo apt-get install -y ca-certificates curl gnupg git

# Instalar Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verificar instalação
docker --version
docker compose version
```

---

## Passo 3: Criar Usuário de Aplicação

> [!IMPORTANT]
> **Nunca rode aplicações como `root` em produção.**  
> Crie um usuário dedicado para segurança.

```bash
# Criar usuário
sudo adduser agent
# (defina uma senha quando solicitado)

# Adicionar ao grupo docker
sudo usermod -aG docker agent

# Trocar para o novo usuário
su - agent
```

---

## Passo 4: Baixar o Projeto

```bash
# Como usuário 'agent'
cd ~
git clone <url-do-repositorio> whatsapp-agent
cd whatsapp-agent
```

---

## Passo 5: Configurar o Ambiente

```bash
# Criar o arquivo .env a partir do modelo
cp .env.example .env

# Editar com nano (ou vim)
nano .env
```

### Configurações importantes para produção:

```env
# --- Aplicação ---
APP_PORT=8000
LOG_LEVEL=INFO

# --- Google Gemini AI ---
GEMINI_API_KEY=AIzaSy...SUA_CHAVE_REAL_AQUI

# --- Redis ---
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=GERE_UMA_SENHA_FORTE_AQUI_123!@#

# --- Qdrant ---
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_NAME=conversations

# --- WAHA ---
WAHA_API_URL=http://waha:3000/
WAHA_API_KEY=GERE_UMA_SENHA_FORTE_AQUI_456!@#
WAHA_DASHBOARD_USERNAME=admin
WAHA_DASHBOARD_PASSWORD=GERE_UMA_SENHA_FORTE_AQUI_789!@#
WAHA_SWAGGER_USERNAME=admin
WAHA_SWAGGER_PASSWORD=GERE_UMA_SENHA_FORTE_AQUI_789!@#

# --- Webhook ---
WEBHOOK_SECRET=GERE_UMA_CHAVE_HMAC_FORTE_AQUI
```

> [!CAUTION]
> **Use senhas fortes e únicas!** Nunca use as senhas de exemplo.  
> Para gerar senhas fortes: `openssl rand -base64 24`

Salve com `Ctrl+O`, depois `Enter`, depois `Ctrl+X`.

---

## Passo 6: Configurar o Tenant

```bash
# Editar a configuração do agente
nano tenants/default/settings.yaml
```

Personalize o `system_prompt`, horários, etc. Veja [🤖 Configuração do Agente](03-configuracao-agente.md).

---

## Passo 7: Subir os Serviços

```bash
docker compose up -d
```

Verifique se tudo subiu:
```bash
docker compose ps
```

Teste a saúde:
```bash
curl http://localhost:8000/health
```

---

## Passo 8: Configurar Firewall

Abra apenas as portas necessárias:

```bash
# Permitir SSH (ESSENCIAL — não execute sem isso!)
sudo ufw allow 22/tcp

# Permitir o app (para webhooks externos)
sudo ufw allow 8000/tcp

# Permitir WAHA dashboard (opcional — pode fechar depois de conectar)
sudo ufw allow 3000/tcp

# Ativar firewall
sudo ufw enable
```

> [!WARNING]
> **Nunca ative o UFW sem antes liberar a porta 22 (SSH)!**  
> Você ficaria trancado fora do servidor.

---

## Passo 9: Conectar o WhatsApp

1. Acesse `http://SEU_IP:3000/dashboard` no navegador
2. Faça login com suas credenciais
3. Crie a sessão `default` e escaneie o QR Code
4. Veja detalhes em [📱 Configuração do WAHA](02-configuracao-waha.md)

---

## Passo 10: Configurar HTTPS com Nginx (Opcional mas Recomendado)

Se você tem um domínio (ex: `agente.suaempresa.com`):

```bash
# Instalar Nginx
sudo apt-get install -y nginx

# Instalar Certbot (certificado SSL gratuito)
sudo apt-get install -y certbot python3-certbot-nginx
```

Crie a configuração do Nginx:
```bash
sudo nano /etc/nginx/sites-available/whatsapp-agent
```

Cole o seguinte conteúdo:
```nginx
server {
    server_name agente.suaempresa.com;

    # App (API principal)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WAHA Dashboard
    location /waha/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Ative e obtenha o certificado SSL:
```bash
# Ativar o site
sudo ln -s /etc/nginx/sites-available/whatsapp-agent /etc/nginx/sites-enabled/

# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx

# Obter certificado SSL (gratuito)
sudo certbot --nginx -d agente.suaempresa.com
```

---

## Configurar Reinício Automático

O Docker Compose já está configurado com `restart: unless-stopped`, então os containers reiniciam automaticamente. Mas caso o servidor reinicie:

```bash
# Garantir que o Docker inicia com o sistema
sudo systemctl enable docker
```

---

## Monitoramento

### Ver logs em tempo real
```bash
docker compose logs -f
```

### Ver logs de um serviço específico
```bash
docker compose logs app --tail=100      # Últimas 100 linhas do app
docker compose logs waha --tail=50      # Últimas 50 linhas do WAHA
```

### Ver uso de recursos
```bash
docker stats
```

### Atualizar o sistema
```bash
# Puxar novas alterações
cd ~/whatsapp-agent
git pull

# Reconstruir e reiniciar
docker compose up -d --build
```

---

## Próximos Passos

- [☁️ Deploy na AWS EC2](05-deploy-aws-ec2.md) — Se preferir Amazon
- [🔧 Troubleshooting](06-troubleshooting.md) — Problemas comuns
