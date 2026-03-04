# 📦 Instalação Local

Guia completo para rodar o WhatsApp B2B AI Agent no seu computador.  
Funciona em **Windows**, **Linux** e **macOS**.

---

## O que você vai precisar

| Requisito | O que é | Onde baixar |
|-----------|---------|-------------|
| **Docker Desktop** | Programa que roda containers (pense como "mini-servidores"). Necessário para rodar todos os serviços. | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **Git** | Programa para baixar o código-fonte do projeto. | [git-scm.com](https://git-scm.com/) |
| **Chave Gemini** | Chave de acesso à IA do Google (grátis). | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

> [!IMPORTANT]
> Você **não precisa** instalar Python, Redis, ou qualquer outro serviço manualmente.  
> O Docker faz tudo automaticamente.

---

## Passo 1: Instalar o Docker Desktop

### Windows

1. Acesse [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Clique em **"Download for Windows"**
3. Execute o instalador `.exe`
4. Durante a instalação, marque **"Use WSL 2"** (recomendado)
5. Reinicie o computador quando solicitado
6. Abra o Docker Desktop e aguarde ele iniciar (ícone da baleia na barra de tarefas)

Para verificar se instalou corretamente, abra o **PowerShell** e digite:
```powershell
docker --version
# Deve mostrar algo como: Docker version 27.x.x
```

### Linux (Ubuntu/Debian)

```bash
# Atualizar pacotes
sudo apt-get update

# Instalar dependências
sudo apt-get install -y ca-certificates curl gnupg

# Adicionar chave GPG do Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Adicionar repositório
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine + Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Dar permissão para rodar docker sem sudo
sudo usermod -aG docker $USER
# IMPORTANTE: faça logout e login novamente para a permissão funcionar
```

### macOS

1. Acesse [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Clique em **"Download for Mac"** (escolha Apple Silicon ou Intel, conforme seu Mac)
3. Arraste o Docker para a pasta **Applications**
4. Abra o Docker Desktop e autorize quando solicitado

```bash
docker --version
# Deve mostrar algo como: Docker version 27.x.x
```

---

## Passo 2: Obter a Chave da API Gemini

A IA do Google Gemini é o "cérebro" do agente. Você precisa de uma chave gratuita.

1. Acesse [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Faça login com sua conta Google
3. Clique em **"Create API Key"**
4. Copie a chave (começa com `AIza...`)
5. **Guarde essa chave — você vai usá-la no próximo passo**

> [!TIP]
> O plano gratuito do Gemini permite **15 requisições por minuto** e **1.500 por dia**.  
> Para uso comercial, considere o plano pago com limites maiores.

---

## Passo 3: Baixar o Projeto

### Windows (PowerShell)
```powershell
# Navegue até onde quer salvar o projeto
cd C:\Users\SeuUsuario\Projetos

# Clone o repositório
git clone <url-do-repositorio>
cd whatsapp-agent
```

### Linux / macOS (Terminal)
```bash
cd ~/projetos
git clone <url-do-repositorio>
cd whatsapp-agent
```

---

## Passo 4: Configurar o Arquivo `.env`

O arquivo `.env` contém todas as senhas e configurações sensíveis do sistema.

### 4.1 Criar o arquivo

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux/macOS:**
```bash
cp .env.example .env
```

### 4.2 Editar o arquivo

Abra o `.env` no seu editor de texto (VS Code, Notepad++, nano, etc.) e preencha:

```env
# =============================================================================
# WhatsApp B2B AI Agent — Variáveis de Ambiente
# =============================================================================

# --- Aplicação ---
APP_PORT=8000                              # Porta da API (não precisa mudar)
LOG_LEVEL=INFO                             # Nível de log (DEBUG para mais detalhes)
TENANT_CONFIG_DIR=./tenants                # Pasta com as configurações dos clientes

# --- Google Gemini AI ---
GEMINI_API_KEY=AIzaSy...                   # ← COLE SUA CHAVE AQUI
GEMINI_MODEL=gemini-2.0-flash             # Modelo (não precisa mudar)

# --- Redis (Cache) ---
REDIS_URL=redis://redis:6379/0             # URL interna (não mude)
REDIS_PASSWORD=SuaSenhaRedis123            # ← MUDE para uma senha forte

# --- Qdrant (Memória) ---
QDRANT_URL=http://qdrant:6333              # URL interna (não mude)
QDRANT_COLLECTION_NAME=conversations       # Nome da coleção (não precisa mudar)

# --- WAHA (WhatsApp) ---
WAHA_API_URL=http://waha:3000/             # URL interna (não mude)
WAHA_API_KEY=SuaSenhaWaha123               # ← MUDE para uma senha forte
WAHA_DASHBOARD_USERNAME=admin              # Login do painel WAHA
WAHA_DASHBOARD_PASSWORD=SuaSenhaWaha123    # ← MUDE para uma senha forte
WAHA_SWAGGER_USERNAME=admin                # Login da documentação API WAHA
WAHA_SWAGGER_PASSWORD=SuaSenhaWaha123      # ← MUDE para uma senha forte

# --- Webhook ---
WEBHOOK_SECRET=SeuSecretWebhook123         # ← MUDE para uma chave forte
```

> [!CAUTION]
> **Nunca compartilhe o arquivo `.env`** com ninguém e nunca faça commit dele no Git.  
> Ele contém senhas e chaves de acesso.

> [!TIP]
> As URLs `redis://redis:...`, `http://qdrant:...` e `http://waha:...` são **URLs internas do Docker**.  
> Elas apontam para outros containers, não para o seu computador. **Não mude.**

---

## Passo 5: Subir os Serviços

Com o Docker Desktop aberto, rode no terminal:

```bash
docker compose up -d
```

**O que acontece:**
1. Docker baixa as imagens necessárias (~2 minutos na primeira vez)
2. Constrói o container da aplicação
3. Inicia 4 containers: `app`, `waha`, `redis`, `qdrant`

Para verificar se tudo subiu:
```bash
docker compose ps
```

Todos devem estar com status `Up` ou `running (healthy)`.

### Verificar saúde do sistema

**Windows (PowerShell):**
```powershell
Invoke-RestMethod http://localhost:8000/health
```

**Linux/macOS:**
```bash
curl http://localhost:8000/health
```

Resultado esperado:
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

---

## Passo 6: Conectar o WhatsApp

Veja o guia completo em [📱 Configuração do WAHA](02-configuracao-waha.md).

---

## Comandos Úteis

| Comando | O que faz |
|---------|-----------|
| `docker compose up -d` | Inicia todos os serviços em segundo plano |
| `docker compose down` | Para todos os serviços |
| `docker compose logs app` | Ver logs da aplicação |
| `docker compose logs waha` | Ver logs do WAHA |
| `docker compose logs -f` | Ver logs em tempo real (Ctrl+C para sair) |
| `docker compose restart app` | Reiniciar apenas a aplicação |
| `docker compose up -d --build` | Reconstruir e reiniciar (após editar código) |
| `docker compose ps` | Ver status dos containers |

---

## Próximos Passos

1. [📱 Configurar o WAHA e conectar WhatsApp](02-configuracao-waha.md)
2. [🤖 Configurar o agente de IA](03-configuracao-agente.md)
