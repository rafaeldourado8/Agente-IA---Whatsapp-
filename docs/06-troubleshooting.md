# 🔧 Troubleshooting (Solução de Problemas)

Guia de problemas comuns e como resolvê-los.

---

## 🔴 O agente não responde às mensagens

### Causa 1: WAHA não tem webhook configurado

**Sintoma:** Mensagens chegam no WhatsApp mas o agente não responde.

**Solução:** Verifique se `docker-compose.yml` tem as variáveis de webhook:

```yaml
# No serviço waha:
environment:
  - WHATSAPP_HOOK_URL=http://app:8000/api/v1/webhook/waha
  - WHATSAPP_HOOK_EVENTS=message
```

Se faltou, adicione e reinicie:
```bash
docker compose down
docker compose up -d
```

### Causa 2: URL do WAHA usando localhost

**Sintoma:** O app não consegue enviar respostas de volta.

**Solução:** No `.env`, a URL do WAHA **deve** usar o nome do serviço Docker:

```env
# ❌ ERRADO (dentro do Docker, localhost = próprio container)
WAHA_API_URL=http://localhost:3000/

# ✅ CORRETO
WAHA_API_URL=http://waha:3000/
```

### Causa 3: Sessão WAHA desconectada

**Sintoma:** Status da sessão é `SCAN_QR_CODE` ou `FAILED`.

**Solução:**
1. Acesse `http://localhost:3000/dashboard`
2. Verifique o status da sessão
3. Se `SCAN_QR_CODE` → escaneie novamente
4. Se `FAILED` → reinicie a sessão

### Causa 4: Nome do tenant não corresponde à sessão

**Sintoma:** Erro 404 "Tenant not found" nos logs do app.

**Solução:** O nome da sessão WAHA deve ser **igual** ao nome da pasta em `tenants/`:
- Sessão WAHA: `default` → Pasta: `tenants/default/`
- Sessão WAHA: `clinica_abc` → Pasta: `tenants/clinica_abc/`

---

## 🔴 Health check mostra serviço "down"

### Redis down

```bash
# Verificar logs do Redis
docker compose logs redis

# Reiniciar Redis
docker compose restart redis
```

**Causa comum:** senha incorreta no `.env`. Verifique se `REDIS_PASSWORD` está correto.

### Qdrant down

```bash
# Verificar logs do Qdrant
docker compose logs qdrant

# Reiniciar Qdrant
docker compose restart qdrant
```

**Causa comum:** falta de memória ou disco. Verifique com `docker stats`.

### WAHA down

```bash
# Verificar logs do WAHA
docker compose logs waha

# Reiniciar WAHA
docker compose restart waha
```

**Causa comum:** `WAHA_API_KEY` diferente no `.env` e no `WHATSAPP_API_KEY` do docker-compose.

---

## 🔴 Erro ao subir o Docker

### "port is already allocated"

Algum programa já está usando a porta.

```bash
# Verificar o que usa a porta 8000
# Linux/macOS:
sudo lsof -i :8000

# Windows PowerShell:
netstat -anb | Select-String "8000"
```

**Solução:** Mude a porta no `.env`: `APP_PORT=8001`

### "permission denied" no Docker

**Linux:** Adicione seu usuário ao grupo docker:
```bash
sudo usermod -aG docker $USER
# Faça logout e login novamente
```

**Windows:** Abra o Docker Desktop e verifique se está rodando.

---

## 🔴 Erro "Tenant not found" (404)

**Causa:** A pasta do tenant não existe ou o `settings.yaml` está com erro de sintaxe.

```bash
# Verificar se o tenant existe
ls tenants/

# Verificar sintaxe do YAML (deve mostrar o conteúdo sem erros)
docker compose exec app python -c "
import yaml
with open('tenants/default/settings.yaml') as f:
    print(yaml.safe_load(f))
"
```

**Solução:** Corrija erros de indentação no YAML. Use espaços, nunca tabs.

---

## 🔴 Erro "GEMINI_API_KEY" / respostas da IA não funcionam

```bash
# Testar a chave diretamente
docker compose exec app python -c "
from google import genai
import os
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents='Diga apenas: OK'
)
print(response.text)
"
```

**Causas comuns:**
- Chave expirada ou inválida → gere uma nova em [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- Cota excedida → aguarde o reset (o plano gratuito tem limites por minuto e por dia)

---

## 🔴 Container reinicia em loop

```bash
# Ver motivo do restart
docker compose logs app --tail=50
```

**Causas comuns:**
- Variável obrigatória faltando no `.env` (ex: `GEMINI_API_KEY` vazio)
- Erro de sintaxe no código Python (após editar)
- Memória insuficiente (veja com `docker stats`)

---

## 🟡 Respostas lentas

**Causa:** A primeira resposta para cada tipo de pergunta é mais lenta (precisa consultar a IA). Respostas subsequentes são rápidas (cache).

**Soluções:**
1. Verifique se o Redis está rodando (cache semântico)
2. Ajuste o `semantic_threshold` no `settings.yaml` (mais baixo = mais cache hits)
3. Mude LOG_LEVEL para DEBUG para ver tempos de resposta detalhados

---

## 🟡 WhatsApp desconecta frequentemente

**Causas:**
- Celular sem internet por muito tempo
- WhatsApp atualizado no celular (pode derrubar sessões web)
- Muitas sessões conectadas ao mesmo número

**Soluções:**
1. Mantenha o celular conectado ao Wi-Fi
2. Não use o mesmo número em outro WhatsApp Web
3. Use um chip dedicado para o agente

---

## 📋 Comandos Úteis para Diagnóstico

```bash
# Status de todos os containers
docker compose ps

# Logs em tempo real (todos os serviços)
docker compose logs -f

# Logs de um serviço específico
docker compose logs app --tail=100
docker compose logs waha --tail=100
docker compose logs redis --tail=50
docker compose logs qdrant --tail=50

# Uso de recursos (CPU, memória)
docker stats

# Reiniciar tudo
docker compose restart

# Reiniciar do zero (apaga containers, mantém dados)
docker compose down
docker compose up -d

# Reiniciar do zero E reconstruir
docker compose down
docker compose up -d --build

# Verificar saúde da API
# Windows PowerShell:
Invoke-RestMethod http://localhost:8000/health
# Linux/macOS:
curl http://localhost:8000/health

# Ver tenants disponíveis
# Windows PowerShell:
Invoke-RestMethod http://localhost:8000/api/v1/admin/tenants
# Linux/macOS:
curl http://localhost:8000/api/v1/admin/tenants

# Recarregar config dos tenants (sem reiniciar)
# Windows PowerShell:
Invoke-RestMethod -Method POST http://localhost:8000/api/v1/admin/tenants/reload-all
# Linux/macOS:
curl -X POST http://localhost:8000/api/v1/admin/tenants/reload-all
```

---

## Ainda com problemas?

1. Verifique os logs: `docker compose logs -f`
2. Coloque `LOG_LEVEL=DEBUG` no `.env` e reinicie para ver mais detalhes
3. Consulte a documentação do WAHA: [waha.devlike.pro/docs](https://waha.devlike.pro/docs/)
4. Consulte a documentação do Gemini: [ai.google.dev/docs](https://ai.google.dev/docs)
