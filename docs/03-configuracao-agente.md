# 🤖 Configuração do Agente de IA

O agente é configurado através de um arquivo **YAML** para cada cliente (tenant).  
Você pode personalizar o nome, personalidade, prompt, horário de atendimento, escalação e mais — **sem alterar nenhum código**.

---

## Estrutura de Pastas

```
tenants/
├── default/              ← Tenant padrão
│   └── settings.yaml     ← Arquivo de configuração
├── clinica_abc/          ← Outro tenant
│   └── settings.yaml
└── loja_xyz/             ← Mais um tenant
    └── settings.yaml
```

Cada pasta é um **tenant** (cliente). O nome da pasta é o **identificador do tenant** e deve ser **igual** ao nome da sessão WAHA.

---

## Criar um Novo Tenant

### 1. Copie a pasta padrão

**Windows (PowerShell):**
```powershell
Copy-Item -Recurse tenants\default tenants\meu_cliente
```

**Linux/macOS:**
```bash
cp -r tenants/default tenants/meu_cliente
```

### 2. Edite o `settings.yaml`

Abra `tenants/meu_cliente/settings.yaml` e personalize.

### 3. Crie uma sessão WAHA com o mesmo nome

No dashboard WAHA (`http://localhost:3000/dashboard`), crie uma sessão chamada `meu_cliente`.

### 4. Recarregue as configurações

Não precisa reiniciar o sistema! Use a API:

**Windows (PowerShell):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/tenants/reload-all" -Method POST
```

**Linux/macOS:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/tenants/reload-all
```

---

## Referência Completa do `settings.yaml`

### 🎭 Identidade do Agente

```yaml
agent:
  # Nome do agente (aparece nas referências do prompt)
  name: "Assistente Virtual da Clínica ABC"

  # Estilo de comunicação
  personality: "Simpático, profissional e acolhedor"

  # Idioma das respostas
  language: "pt-BR"

  # Prompt de sistema — define o comportamento da IA
  system_prompt: |
    Você é o Assistente Virtual da Clínica ABC, especializado em
    atendimento ao paciente.

    Regras:
    - Responda em português, de forma acolhedora e profissional
    - Nunca dê diagnósticos médicos
    - Para agendamentos, peça nome, telefone e convênio
    - Seja conciso: máximo 3 parágrafos por resposta
    - Use emojis com moderação (máximo 1 por mensagem)
    - Se não souber, diga que vai verificar com a equipe
```

> [!TIP]
> **O `system_prompt` é a parte mais importante.** Ele define como a IA responde.
> Quanto mais específico e detalhado, melhor será a qualidade das respostas.

#### Dicas para escrever um bom prompt:

| Dica | Exemplo |
|------|---------|
| Defina **quem** o agente é | "Você é o Assistente Virtual da Empresa X" |
| Defina **como** deve responder | "Responda de forma profissional e simpática" |
| Defina **regras claras** | "Nunca mencione concorrentes" |
| Defina **limites** | "Máximo 3 parágrafos por resposta" |
| Defina o que fazer quando **não souber** | "Peça o contato e diga que vai verificar" |

---

### 📋 Filtro de Tópicos

```yaml
topics:
  # Tópicos que o agente PODE discutir
  allowed:
    - agendamento de consultas
    - dúvidas sobre convênios
    - localização e horários
    - preparação para exames

  # Tópicos que o agente NÃO PODE discutir
  blocked:
    - política
    - religião
    - concorrentes
    - diagnósticos médicos
```

---

### ⏰ Horário de Atendimento

```yaml
business_hours:
  # Fuso horário (lista: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
  timezone: "America/Sao_Paulo"

  # Horários de funcionamento
  # Formato: "HH:MM-HH:MM" ou null (sem atendimento)
  schedule:
    monday_friday: "08:00-18:00"    # Segunda a sexta
    saturday: "09:00-13:00"         # Sábado
    sunday: null                     # Domingo = sem atendimento

  # Mensagem enviada fora do horário
  out_of_hours_message: >
    Nosso horário de atendimento é de segunda a sexta, das 8h às 18h,
    e aos sábados, das 9h às 13h. Deixe sua mensagem que retornaremos
    assim que possível! 😊
```

**Como funciona:**
- Se alguém mandar mensagem **dentro** do horário → IA responde normalmente
- Se alguém mandar mensagem **fora** do horário → envia a `out_of_hours_message`
- Se `schedule` não estiver configurado → IA sempre responde (24/7)

> [!TIP]
> Para atendimento 24 horas, basta remover ou comentar a seção `business_hours`.

---

### 🚨 Escalação para Humano

```yaml
escalation:
  # Palavras/frases que acionam a transferência
  trigger_keywords:
    - "falar com humano"
    - "atendente"
    - "gerente"
    - "reclamação"
    - "cancelar"

  # Ação: "webhook" (chama URL) ou "message" (envia mensagem)
  action: "webhook"

  # URL que recebe o aviso de escalação (se action = webhook)
  webhook_url: "https://seu-sistema.com/api/escalation"

  # Mensagem enviada ao usuário durante a escalação
  message: "Entendi! Vou te conectar com nossa equipe. Aguarde um momento! 🙏"
```

**Como funciona:**
1. Usuário digita "quero falar com um atendente"
2. O sistema detecta a palavra-chave "atendente"
3. Envia a `message` ao usuário
4. Se `action: webhook`, chama a `webhook_url` para notificar sua equipe

---

### 🧠 Cache Semântico

```yaml
cache:
  # Similaridade mínima para cache hit (0.0 a 1.0)
  semantic_threshold: 0.92

  # Validade do cache em horas
  ttl_hours: 24
```

**O que é?**  
Se dois clientes fazem perguntas **parecidas**, o sistema reutiliza a resposta do cache em vez de consultar a IA novamente. Isso é mais rápido e mais barato.

| Threshold | Comportamento | Quando usar |
|-----------|--------------|-------------|
| `0.95+` | Muito conservador — só usa cache se a pergunta for quase idêntica | Quando precisão é crítica |
| `0.90-0.94` | Equilibrado — cache para perguntas semelhantes | Recomendado para a maioria |
| `0.80-0.89` | Agressivo — mais cache hits, risco de resposta errada | Quando volume é muito alto |

---

### 🔗 Webhooks de Eventos

```yaml
webhooks:
  # Eventos que geram notificações
  events:
    - message_received         # Mensagem recebida
    - escalation_triggered     # Escalação acionada
    - session_started          # Nova conversa
    - session_ended            # Conversa encerrada

  # URL que receberá as notificações via POST
  endpoint: "https://seu-sistema.com/webhooks/agent"

  # Secret para assinatura HMAC-SHA256
  secret: "mude-este-secret-em-producao"
```

**O que é?**  
Webhooks permitem que seu sistema externo receba notificações quando algo acontece. Útil para:
- Integrar com CRM
- Dashboard de analytics
- Alertas de escalação

---

## Exemplos Prontos

### Clínica Médica

```yaml
agent:
  name: "Assistente da Clínica Saúde Plena"
  personality: "Acolhedor, profissional e cuidadoso"
  language: "pt-BR"
  system_prompt: |
    Você é o assistente virtual da Clínica Saúde Plena.
    
    Serviços oferecidos:
    - Consultas médicas (clínico geral, cardiologia, dermatologia)
    - Exames laboratoriais
    - Vacinação
    
    Regras:
    - NUNCA dê diagnósticos médicos
    - Para agendamentos, peça: nome completo, convênio, especialidade desejada
    - Horário de atendimento: seg-sex 7h-19h, sáb 7h-12h
    - Endereço: Rua Exemplo, 123 - Centro
    
topics:
  allowed: [agendamentos, exames, convênios, localização, horários, vacinação]
  blocked: [diagnósticos, prescrição de medicamentos, política, religião]

business_hours:
  timezone: "America/Sao_Paulo"
  schedule:
    monday_friday: "07:00-19:00"
    saturday: "07:00-12:00"
    sunday: null
  out_of_hours_message: >
    A Clínica Saúde Plena atende de segunda a sexta das 7h às 19h
    e sábados das 7h às 12h. Deixe sua mensagem! 😊
```

### Loja Virtual

```yaml
agent:
  name: "Assistente da Loja TechShop"
  personality: "Jovem, descontraído e experiente em tecnologia"
  language: "pt-BR"
  system_prompt: |
    Você é o assistente da TechShop, especialista em produtos de tecnologia.
    
    Catálogo:
    - Smartphones (Samsung, Apple, Xiaomi)
    - Notebooks (Dell, Lenovo, MacBook)
    - Acessórios (capas, fones, carregadores)
    
    Regras:
    - Informe preços quando souber
    - Para compras, direcione ao site: www.techshop.com.br
    - Para trocas/devoluções, peça o número do pedido
    - Prazo de entrega: 3 a 7 dias úteis

topics:
  allowed: [produtos, preços, pedidos, trocas, garantia, promoções]
  blocked: [política, religião, concorrentes]

business_hours:
  timezone: "America/Sao_Paulo"
  schedule:
    monday_friday: "09:00-21:00"
    saturday: "09:00-18:00"
    sunday: "10:00-16:00"
  out_of_hours_message: >
    Estamos fora do horário, mas você pode comprar pelo site
    www.techshop.com.br 24h! 🛒

escalation:
  trigger_keywords: [reclamação, defeito, reembolso, cancelar, gerente]
  action: "message"
  message: "Vou encaminhar sua solicitação para nossa equipe de atendimento. Em breve um especialista entrará em contato! 🙏"
```

---

## Próximos Passos

- [🖥️ Deploy em VPS](04-deploy-vps.md) — Colocar em produção
- [☁️ Deploy na AWS EC2](05-deploy-aws-ec2.md) — Deploy na Amazon
