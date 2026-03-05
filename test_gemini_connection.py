"""Test Gemini API connection."""
import asyncio
from google import genai
from app.config import get_settings
#
async def test_connection():
    settings = get_settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    print(f"Testing connection with model: {settings.GEMINI_MODEL}")
    
    response = await client.aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents="Say 'Connection successful!' in Portuguese",
    )
    
    print(f"✓ Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_connection())
