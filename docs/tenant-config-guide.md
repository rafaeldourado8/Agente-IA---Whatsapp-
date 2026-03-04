# Guia de Configuração de Tenant

## Visão Geral

Cada cliente (tenant) do sistema possui sua própria pasta de configuração em `tenants/`. A configuração é feita inteiramente via arquivos YAML — sem código, sem interface gráfica.

## Estrutura de Diretórios

```
tenants/
├── acme_corp/
│   ├── settings.yaml    # Configuração obrigatória
│   └── faq.yaml         # FAQ customizado (opcional, futuro)
├── tech_startup/
│   └── settings.yaml
└── example_tenant/
    └── settings.yaml    # Modelo comentado para referência
```

## Como Adicionar um Novo Tenant

1. **Copie o template**:
   ```bash
   cp -r tenants/example_tenant tenants/nome_do_cliente
   ```

2. **Edite `settings.yaml`**: customize nome, personalidade, prompt, horários, etc.

3. **Reinicie ou recarregue**: o agente carrega configs no startup. Para recarregar sem restart, use o endpoint admin:
   ```
   POST /api/v1/admin/tenants/{tenant_id}/reload
   ```

## Schema Completo do settings.yaml

### `agent` (obrigatório)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|:-----------:|-----------|
| `name` | string | ✅ | Nome exibido do agente |
| `personality` | string | — | Estilo de comunicação |
| `language` | string | — | Código do idioma (padrão: `pt-BR`) |
| `system_prompt` | string | ✅ | Instruções de sistema para a IA |

### `topics`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `allowed` | lista de strings | Tópicos permitidos |
| `blocked` | lista de strings | Tópicos bloqueados |

### `business_hours`

| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `timezone` | string | `America/Sao_Paulo` | Timezone IANA |
| `schedule.monday_friday` | string/null | null | Horário seg–sex (`HH:MM-HH:MM`) |
| `schedule.saturday` | string/null | null | Horário sábado |
| `schedule.sunday` | string/null | null | Horário domingo |
| `out_of_hours_message` | string | (mensagem padrão) | Resposta fora do horário |

### `escalation`

| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `trigger_keywords` | lista | `[]` | Frases que acionam escalação |
| `action` | string | `webhook` | `webhook` ou `message` |
| `webhook_url` | string/null | null | URL para evento de escalação |
| `message` | string | (mensagem padrão) | Texto exibido ao usuário |

### `cache`

| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `semantic_threshold` | float | `0.92` | Similaridade mínima (0.0–1.0) |
| `ttl_hours` | int | `24` | Tempo de vida do cache (horas) |

### `webhooks`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `events` | lista | Eventos a despachar |
| `endpoint` | string/null | URL destino |
| `secret` | string | Secret para assinatura HMAC |

## Eventos Disponíveis

| Evento | Quando é disparado |
|--------|--------------------|
| `message_received` | Nova mensagem do usuário |
| `escalation_triggered` | Escalação para humano acionada |
| `session_started` | Primeira mensagem de uma conversa |
| `session_ended` | Conversa encerrada por inatividade |

## Validação

O sistema valida a configuração no startup. Erros comuns:

- **Campo `agent` ausente**: `agent.name` e `agent.system_prompt` são obrigatórios
- **Threshold inválido**: `cache.semantic_threshold` deve estar entre 0.0 e 1.0
- **YAML mal-formado**: verifique indentação e aspas
