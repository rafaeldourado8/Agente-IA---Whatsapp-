# 📱 Configuração do WAHA (WhatsApp)

O **WAHA** (WhatsApp HTTP API) é o serviço que conecta seu sistema ao WhatsApp.  
Ele funciona como uma "ponte" entre o WhatsApp e o agente de IA.

---

## Como funciona

```
Usuário manda mensagem → WhatsApp → WAHA → Seu Agente IA → Resposta
```

O WAHA roda em um container Docker e se conecta ao WhatsApp através de um **QR Code** — assim como o WhatsApp Web.

> [!IMPORTANT]
> O WAHA usa a API não-oficial do WhatsApp (semelhante ao WhatsApp Web).  
> Use um **número dedicado** para o agente, **não** seu número pessoal.

---

## Passo 1: Acessar o Painel do WAHA

Após subir os containers com `docker compose up -d`, acesse:

```
http://localhost:3000/dashboard
```

**Login:**
- **Usuário:** o valor de `WAHA_DASHBOARD_USERNAME` no seu `.env` (padrão: `admin`)
- **Senha:** o valor de `WAHA_DASHBOARD_PASSWORD` no seu `.env`

---

## Passo 2: Criar uma Sessão WhatsApp

A sessão é a "conexão" entre o WAHA e o WhatsApp. O nome da sessão **deve ser igual** ao nome do tenant (pasta em `tenants/`).

### Via Dashboard (mais fácil)

1. No painel, clique em **"Sessions"** no menu lateral
2. Clique em **"Start new session"**
3. Em **"Session Name"**, digite: `default` (ou o nome do seu tenant)
4. Clique em **"Start"**
5. Aparecerá um **QR Code**
6. No seu celular:
   - Abra o WhatsApp
   - Vá em **Dispositivos Conectados** (Menu → Aparelhos Conectados)
   - Clique em **Conectar Dispositivo**
   - Escaneie o QR Code

### Via API (alternativa)

**Windows (PowerShell):**
```powershell
$headers = @{ "X-Api-Key" = "sua-waha-api-key" }
$body = @{ name = "default" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:3000/api/sessions/start" -Method POST -Headers $headers -Body $body -ContentType "application/json"
```

**Linux/macOS:**
```bash
curl -X POST http://localhost:3000/api/sessions/start \
  -H "X-Api-Key: sua-waha-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "default"}'
```

Depois, pegue o QR Code:
```bash
# Abre o QR Code como imagem no navegador
http://localhost:3000/api/sessions/default/auth/qr?format=image
```

---

## Passo 3: Verificar Conexão

Após escanear o QR Code, verifique se a sessão está ativa:

**Windows (PowerShell):**
```powershell
$headers = @{ "X-Api-Key" = "sua-waha-api-key" }
Invoke-RestMethod -Uri "http://localhost:3000/api/sessions/" -Headers $headers
```

**Linux/macOS:**
```bash
curl -H "X-Api-Key: sua-waha-api-key" http://localhost:3000/api/sessions/
```

Resultado esperado:
```json
[
  {
    "name": "default",
    "status": "WORKING",
    ...
  }
]
```

O status deve ser `"WORKING"`. Se mostrar `"SCAN_QR_CODE"`, escaneie o QR novamente.

---

## Passo 4 (Opcional): Conexão Remota (Sem QR Code)

Se você precisa conectar o WhatsApp de um cliente que está longe (não pode escanear o QR Code da sua tela), você pode gerar um **Código de Pareamento** de 8 dígitos.

**Como funciona:**
1. Você solicita um código para o número do cliente
2. Você envia o código para ele (ex: pelo seu próprio WhatsApp)
3. Ele digita o código no celular dele

**Gerando o código via API:**

Altere `SEU_NUMERO_AQUI` para o celular do seu cliente (ex: `5511999999999`).

**Windows (PowerShell):**
```powershell
$headers = @{ "X-Api-Key" = "sua-waha-api-key" }
$body = @{ phoneNumber = "SEU_NUMERO_AQUI" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:3000/api/sessions/default/auth/request-code" -Method POST -Headers $headers -Body $body -ContentType "application/json"
```

**Linux/macOS:**
```bash
curl -X POST http://localhost:3000/api/sessions/default/auth/request-code \
  -H "X-Api-Key: sua-waha-api-key" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "SEU_NUMERO_AQUI"}'
```

**O que o cliente deve fazer:**
1. Abrir o WhatsApp
2. **Aparelhos Conectados** > **Conectar um Aparelho**
3. Clicar em **"Conectar com número de telefone em vez disso"** (na tela da câmera)
4. Digitar o código de 8 dígitos que você mandou.

---

## Como o Webhook Funciona

O sistema é configurado automaticamente para que:

1. WAHA recebe uma mensagem no WhatsApp
2. WAHA envia a mensagem para `http://app:8000/api/v1/webhook/waha`
3. O agente processa e responde
4. O agente envia a resposta de volta pelo WAHA

Essa configuração está no `docker-compose.yml`:

```yaml
# Dentro do serviço waha:
environment:
  - WHATSAPP_HOOK_URL=http://app:8000/api/v1/webhook/waha
  - WHATSAPP_HOOK_EVENTS=message
```

> [!TIP]
> Você **não precisa** configurar o webhook manualmente.  
> O `docker-compose.yml` já faz isso automaticamente via variáveis de ambiente.

---

## Sessões e Tenants

O sistema usa o **nome da sessão WAHA** como **identificador do tenant**.  
Isso significa:

| Sessão WAHA | Pasta do Tenant | Resultado |
|-------------|-----------------|-----------|
| `default` | `tenants/default/` | ✅ Funciona |
| `clinica_abc` | `tenants/clinica_abc/` | ✅ Funciona |
| `loja_xyz` | `tenants/loja_xyz/` | ✅ Funciona |
| `minha_sessao` | *(sem pasta)* | ❌ Erro 404 |

### Arquitetura de Múltiplos Números (Multi-tenant)

**Sim, esta arquitetura suporta dezenas de números conectados simultaneamente!**  
O próprio design `Multi-tenant` foi feito especificamente para que uma única instância (1 Docker) atenda vários clientes diferentes ao mesmo tempo, mantendo tudo isolado.

Para adicionar um novo cliente com um **número novo**:

1. Crie uma pasta para cada cliente em `tenants/`:
   ```
   tenants/
   ├── clinica_abc/
   │   └── settings.yaml    ← Configurações e IA da Clínica
   ├── loja_xyz/
   │   └── settings.yaml    ← Configurações e IA da Loja
   └── escritorio_def/
       └── settings.yaml    ← Configurações e IA do Escritório
   ```

2. Crie **novas sessões WAHA** (uma para cada cliente):
   - Inicie a sessão `clinica_abc` → Leia o QR Code com o número da clínica
   - Inicie a sessão `loja_xyz` → Leia o QR Code com o número da loja
   - Inicie a sessão `escritorio_def` → Leia o QR Code com o número do escritório

3. **Como o isolamento funciona:**
   - Quando chega mensagem no número da loja, o webhook envia `session="loja_xyz"`.
   - A Aplicação (FastAPI) carrega *apenas* o arquivo `tenants/loja_xyz/settings.yaml`.
   - A memória da conversa e o cache daquela IA ficam isolados em coleções separadas (usando o tenant-id).
   - A IA responde via API WAHA enviando de volta para a sessão `loja_xyz`.

> [!TIP]
> Você roda a aplicação apenas 1 vez (não precisa de 1 docker para cada cliente). Com **1 servidor de 2GB ou 4GB RAM** (`t3.medium` na AWS), você pode rodar **10, 20 ou 50 números** simultaneamente, bastando criar mais pastas e sessões.

---

## Dicas Importantes

### O WhatsApp desconectou?

Se o celular ficar muito tempo sem internet, a conexão pode cair. Para reconectar:

```bash
# Reiniciar a sessão
docker compose restart waha
```

Ou acesse o dashboard e clique em **"Restart"** na sessão.

### Mensagens não estão chegando?

1. Verifique se a sessão está `WORKING` no dashboard
2. Verifique os logs: `docker compose logs waha --tail=50`
3. Verifique os logs do app: `docker compose logs app --tail=50`
4. Veja o guia de [🔧 Troubleshooting](06-troubleshooting.md)

### Documentação Swagger do WAHA

O WAHA tem sua própria documentação de API em:
```
http://localhost:3000/swagger
```

Use as mesmas credenciais de `WAHA_SWAGGER_USERNAME` e `WAHA_SWAGGER_PASSWORD`.

---

## Próximos Passos

- [🤖 Configurar o Agente de IA](03-configuracao-agente.md)
