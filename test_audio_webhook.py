"""Test audio webhook payload"""
import requests
import json

# Simular payload de áudio do WAHA
audio_payload = {
    "event": "message",
    "session": "default",
    "payload": {
        "from": "5511999999999@c.us",
        "type": "ptt",  # push-to-talk (áudio)
        "hasMedia": True,
        "mediaUrl": "http://waha:3000/api/files/message/audio.ogg",
        "body": "",  # áudio não tem body
        "fromMe": False
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/webhook/waha",
    json=audio_payload
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
