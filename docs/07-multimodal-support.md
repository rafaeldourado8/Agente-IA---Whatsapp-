# 🎨 Suporte Multimodal (Imagens e Áudio)

O agente WhatsApp agora suporta processamento de **imagens** e **áudio**, além de mensagens de texto.

---

## 📋 Modelos Utilizados

| Tipo | Modelo | Função |
|------|--------|--------|
| **Texto** | `gemini-2.0-flash` | Conversação padrão |
| **Imagem** | `gemini-2.0-flash-exp` | Análise e descrição de imagens |
| **Áudio** | `gemini-1.5-flash` | Transcrição de áudio |

---

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Adicione ao seu `.env`:

```bash
# Modelos de IA
GEMINI_MODEL=gemini-2.0-flash
GEMINI_VISION_MODEL=gemini-2.0-flash-exp
GEMINI_AUDIO_MODEL=gemini-1.5-flash
```

### 2. Reinicie os Serviços

```bash
docker compose restart app
```

---

## 🖼️ Processamento de Imagens

### Como Funciona

1. Usuário envia uma **imagem** via WhatsApp (com ou sem legenda)
2. WAHA detecta `type: "image"` e `hasMedia: true`
3. O agente baixa a imagem via `mediaUrl`
4. Gemini 2.0 Flash Exp analisa a imagem
5. Resposta é enviada ao usuário

### Exemplo de Uso

**Usuário envia:** 📷 Foto de um produto  
**Legenda:** "Quanto custa este produto?"

**Agente responde:**  
"Vejo que você enviou uma imagem de [descrição do produto]. O preço é R$ XXX. Posso ajudar com mais informações?"

### Casos de Uso

- ✅ Identificação de produtos
- ✅ Análise de documentos (RG, CNH, comprovantes)
- ✅ Diagnóstico visual (fotos de problemas técnicos)
- ✅ Catálogo de produtos

---

## 🎤 Processamento de Áudio

### Como Funciona

1. Usuário envia um **áudio** via WhatsApp
2. WAHA detecta `type: "audio"` ou `type: "ptt"` (push-to-talk)
3. O agente baixa o áudio via `mediaUrl`
4. Gemini 1.5 Flash transcreve o áudio
5. Transcrição é processada como mensagem de texto
6. Resposta é gerada com base na transcrição

### Exemplo de Uso

**Usuário envia:** 🎤 Áudio de 15 segundos  
**Conteúdo:** "Olá, gostaria de saber o horário de funcionamento"

**Agente:**
1. Transcreve: "Olá, gostaria de saber o horário de funcionamento"
2. Processa como texto normal
3. Responde: "Nosso horário de funcionamento é de segunda a sexta, das 8h às 18h."

### Casos de Uso

- ✅ Atendimento hands-free
- ✅ Acessibilidade para usuários com dificuldade de digitação
- ✅ Mensagens longas e complexas
- ✅ Suporte em ambientes ruidosos

---

## 🔄 Fluxo de Processamento

```
┌─────────────────┐
│ Usuário envia   │
│ Imagem/Áudio    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WAHA detecta    │
│ tipo de mídia   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Webhook extrai  │
│ mediaUrl        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent baixa     │
│ arquivo         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Gemini processa │
│ (Vision/Audio)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Resposta gerada │
│ e enviada       │
└─────────────────┘
```

---

## 🚫 Limitações

### Cache Semântico

- ❌ **Imagens e áudios NÃO são cacheados**
- ✅ Apenas mensagens de texto usam cache semântico
- Motivo: Cada imagem/áudio é único e requer processamento completo

### Formatos Suportados

**Imagens:**
- JPEG, PNG, WebP
- Tamanho máximo: depende do WAHA

**Áudio:**
- OGG (formato padrão do WhatsApp)
- MP3, WAV (se suportado pelo WAHA)

---

## 📊 Custos

| Tipo | Modelo | Custo Aproximado |
|------|--------|------------------|
| Texto | gemini-2.0-flash | Muito baixo |
| Imagem | gemini-2.0-flash-exp | Baixo |
| Áudio | gemini-1.5-flash | Médio |

💡 **Dica:** Áudios longos consomem mais tokens. Configure limites no WAHA se necessário.

---

## 🧪 Testando

### Teste Manual via API

```bash
# Simular mensagem de imagem
curl -X POST http://localhost:8000/api/v1/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "instance": "default",
    "phone": "5511999999999",
    "message": "O que é isso?",
    "session_id": "test_session"
  }'
```

### Teste Real via WhatsApp

1. Conecte seu WhatsApp no WAHA
2. Envie uma foto para o número conectado
3. Adicione uma legenda (opcional)
4. Aguarde a resposta do agente

---

## 🔧 Troubleshooting

### Imagem não é processada

**Problema:** Agente responde como se fosse texto

**Solução:**
- Verifique se `hasMedia: true` está no payload do WAHA
- Confirme que `mediaUrl` está presente
- Verifique logs: `docker compose logs app`

### Áudio não é transcrito

**Problema:** Erro ao processar áudio

**Solução:**
- Verifique formato do áudio (deve ser OGG)
- Confirme que `GEMINI_AUDIO_MODEL` está configurado
- Teste com áudio curto (< 30 segundos)

### Erro de download de mídia

**Problema:** `AIProviderError: Failed to download media`

**Solução:**
- Verifique conectividade entre containers
- Confirme que WAHA está acessível
- Verifique se `mediaUrl` é válida

---

## 📝 Exemplo de Payload WAHA

### Imagem

```json
{
  "event": "message",
  "session": "default",
  "payload": {
    "from": "5511999999999@c.us",
    "type": "image",
    "hasMedia": true,
    "mediaUrl": "http://waha:3000/api/files/message/image.jpg",
    "caption": "Quanto custa?",
    "fromMe": false
  }
}
```

### Áudio

```json
{
  "event": "message",
  "session": "default",
  "payload": {
    "from": "5511999999999@c.us",
    "type": "ptt",
    "hasMedia": true,
    "mediaUrl": "http://waha:3000/api/files/message/audio.ogg",
    "fromMe": false
  }
}
```

---

## 🎯 Próximos Passos

- [ ] Suporte a vídeos
- [ ] Suporte a documentos (PDF, DOCX)
- [ ] OCR avançado para documentos
- [ ] Análise de múltiplas imagens em sequência
- [ ] Resumo de áudios longos

---

## 📚 Referências

- [Google Gemini Vision](https://ai.google.dev/gemini-api/docs/vision)
- [Google Gemini Audio](https://ai.google.dev/gemini-api/docs/audio)
- [WAHA Media Handling](https://waha.devlike.pro/docs/how-to/media/)
