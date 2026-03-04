# ☁️ Deploy na AWS EC2

Guia passo a passo para colocar o agente de IA rodando na **Amazon EC2**.  
Ideal para quem quer a infraestrutura da AWS com controle total do servidor.

---

## O que é a AWS EC2?

A **EC2** (Elastic Compute Cloud) é um serviço da Amazon que cria **servidores virtuais** na nuvem. Funciona como alugar um computador que fica ligado 24 horas, acessível pela internet — perfeito para rodar o agente WhatsApp.

> [!TIP]
> A AWS oferece **12 meses grátis** para novas contas (tier `t2.micro` ou `t3.micro`).  
> Para produção, recomendamos `t3.small` ou maior.

---

## Custos Estimados

| Instância | CPU | RAM | Custo/mês (estimado) | Para quem |
|-----------|-----|-----|---------------------|-----------|
| `t3.micro` | 2 vCPU | 1 GB | ~US$ 8 (grátis 12 meses) | Teste |
| `t3.small` | 2 vCPU | 2 GB | ~US$ 17 | Até 200 conversas/dia |
| `t3.medium` | 2 vCPU | 4 GB | ~US$ 34 | Até 1000 conversas/dia |

Adicione ~US$ 5/mês para armazenamento (20 GB SSD).

---

## Pré-requisitos

1. **Conta AWS** — [Criar conta](https://aws.amazon.com/free/)
2. **Chave Gemini** — [Obter grátis](https://aistudio.google.com/apikey)

---

## Passo 1: Criar a Instância EC2

### 1.1 Acessar o Console AWS

1. Acesse [console.aws.amazon.com](https://console.aws.amazon.com/)
2. Faça login na sua conta
3. No menu de busca, digite **"EC2"** e clique no serviço

### 1.2 Criar a Instância

1. Clique em **"Launch Instance"** (Executar Instância)
2. Preencha:

| Campo | Valor |
|-------|-------|
| **Name** | `whatsapp-agent` |
| **Application and OS** | Ubuntu Server 24.04 LTS (Free tier eligible) |
| **Instance type** | `t3.small` (ou `t3.micro` para teste) |
| **Key pair** | Clique em **"Create new key pair"** |

### 1.3 Criar Key Pair (Chave de Acesso)

1. **Nome:** `whatsapp-agent-key`
2. **Tipo:** RSA
3. **Formato:**
   - Windows: `.ppk` (para PuTTY)
   - Linux/macOS: `.pem`
4. Clique em **"Create key pair"** — o arquivo será baixado automaticamente

> [!CAUTION]
> **Guarde este arquivo em local seguro!** Se você perder a chave, não conseguirá acessar o servidor.  
> Ele é sua "senha" para entrar no servidor.

### 1.4 Configurar Rede e Segurança

Na seção **"Network settings"**, clique em **"Edit"** e configure:

**Segurity Group Rules (Regras de Firewall):**

| Tipo | Porta | Origem | Descrição |
|------|-------|--------|-----------|
| SSH | 22 | My IP | Acesso SSH (somente seu IP) |
| Custom TCP | 8000 | Anywhere (0.0.0.0/0) | API do Agente |
| Custom TCP | 3000 | My IP | Dashboard WAHA (somente seu IP) |

> [!IMPORTANT]
> Restrinja a porta 3000 apenas ao seu IP para segurança.  
> A porta 8000 precisa ser aberta para o WAHA enviar webhooks internos, mas em produção recomenda-se colocar atrás de um proxy reverso.

### 1.5 Configurar Armazenamento

- **Tamanho:** 20 GB (mínimo) ou 30 GB (recomendado)
- **Tipo:** gp3 (SSD)

### 1.6 Lançar

Clique em **"Launch Instance"**. Aguarde ~1 minuto até o status ficar **"Running"**.

---

## Passo 2: Acessar o Servidor

### Encontrar o IP Público

1. No painel EC2, clique na sua instância
2. Copie o **"Public IPv4 address"** (algo como `54.123.45.67`)

### Conectar via SSH

**Windows (PowerShell):**
```powershell
# Navegar até onde salvou a chave
cd C:\Users\SeuUsuario\Downloads

# Conectar
ssh -i whatsapp-agent-key.pem ubuntu@54.123.45.67
```

Se aparecer um erro de permissões no Windows:
```powershell
icacls whatsapp-agent-key.pem /inheritance:r /grant:r "$($env:USERNAME):(R)"
ssh -i whatsapp-agent-key.pem ubuntu@54.123.45.67
```

**Linux/macOS:**
```bash
# Ajustar permissões da chave
chmod 400 ~/Downloads/whatsapp-agent-key.pem

# Conectar
ssh -i ~/Downloads/whatsapp-agent-key.pem ubuntu@54.123.45.67
```

> [!TIP]
> Na primeira conexão, digite `yes` quando perguntado sobre a fingerprint.

---

## Passo 3: Instalar Docker no Servidor

Já conectado via SSH:

```bash
# Atualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar Docker (script oficial)
curl -fsSL https://get.docker.com | sudo sh

# Adicionar usuário ao grupo docker (para não precisar de sudo)
sudo usermod -aG docker $USER

# Sair e entrar novamente para aplicar permissões
exit
```

Reconecte via SSH e verifique:
```bash
docker --version
docker compose version
```

---

## Passo 4: Configurar e Iniciar o Projeto

```bash
# Clonar o projeto
git clone <url-do-repositorio> ~/whatsapp-agent
cd ~/whatsapp-agent

# Criar arquivo de configuração
cp .env.example .env
nano .env
```

Edite o `.env` com senhas fortes (veja [passo 5 do guia VPS](04-deploy-vps.md#passo-5-configurar-o-ambiente) para detalhes).

```bash
# Subir todos os serviços
docker compose up -d

# Verificar
docker compose ps
curl http://localhost:8000/health
```

---

## Passo 5: Conectar o WhatsApp

1. No seu computador, acesse `http://SEU_IP_EC2:3000/dashboard`
2. Faça login com `WAHA_DASHBOARD_USERNAME` / `WAHA_DASHBOARD_PASSWORD`
3. Crie a sessão `default` e escaneie o QR Code
4. Detalhes em [📱 Configuração do WAHA](02-configuracao-waha.md)

---

## Passo 6: Configurar IP Elástico (Recomendado)

Por padrão, o IP da EC2 muda se você parar e iniciar a instância.  
Um **Elastic IP** é um IP fixo, gratuito enquanto sua instância estiver rodando.

1. No painel EC2, vá em **"Elastic IPs"** (menu lateral)
2. Clique em **"Allocate Elastic IP address"**
3. Clique em **"Allocate"**
4. Selecione o IP recém-criado
5. Clique em **"Actions" → "Associate Elastic IP address"**
6. Selecione sua instância `whatsapp-agent`
7. Clique em **"Associate"**

Agora seu servidor tem um IP fixo que nunca muda.

> [!WARNING]
> Se você alocar um Elastic IP e **não** associar a uma instância rodando, a AWS cobra ~US$ 3,65/mês. Sempre associe ou libere IPs não utilizados.

---

## Passo 7: Configurar Domínio (Opcional)

Se você tem um domínio (ex: `agente.empresa.com`):

1. No seu provedor DNS, crie um registro **A** apontando para o Elastic IP
2. Instale Nginx + Certbot no servidor:

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Criar config do Nginx
sudo nano /etc/nginx/sites-available/whatsapp-agent
```

Cole:
```nginx
server {
    server_name agente.empresa.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Ativar
sudo ln -s /etc/nginx/sites-available/whatsapp-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL gratuito
sudo certbot --nginx -d agente.empresa.com
```

---

## Dicas de Segurança AWS

### Restringir Security Group

Depois de conectar o WhatsApp, restrinja a porta 3000 apenas ao seu IP:

1. Vá em **"Security Groups"** no painel EC2
2. Edite as regras de entrada (Inbound Rules)
3. Mude a porta 3000 de "Anywhere" para **"My IP"**

### Backups Automáticos

1. No painel EC2, selecione sua instância
2. **Actions → Image and templates → Create image**
3. Para automatizar, use **AWS Backup** ou **Amazon Data Lifecycle Manager**

### Monitoramento com CloudWatch

1. No painel EC2, aba **"Monitoring"**
2. Veja gráficos de CPU, rede e disco
3. Configure alarmes em **CloudWatch → Alarms → Create alarm**

---

## Comandos Úteis no EC2

```bash
# Ver status dos containers
docker compose ps

# Ver logs em tempo real
docker compose logs -f

# Uso de recursos
docker stats

# Espaço em disco
df -h

# Atualizar o projeto
cd ~/whatsapp-agent
git pull
docker compose up -d --build
```

---

## Próximos Passos

- [🤖 Configurar o Agente](03-configuracao-agente.md)
- [🔧 Troubleshooting](06-troubleshooting.md)
