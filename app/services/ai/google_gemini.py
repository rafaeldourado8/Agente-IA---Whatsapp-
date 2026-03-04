"""Google Gemini AI provider implementation.

Wraps the Google Generative AI SDK to generate conversational
responses. Supports text, image, and audio processing.
"""

from __future__ import annotations

import logging
import time
import httpx

from google import genai
from google.genai import types

from app.config import get_settings
from app.core.exceptions import AIProviderError
from app.core.interfaces import AIProvider
from app.models.message import Message, MessageRole, MessageType
from app.models.response import AgentResponse, ResponseSource

logger = logging.getLogger(__name__)


class GoogleGeminiProvider(AIProvider):
    """AI response generation powered by Google Gemini.

    Attributes:
        _model_name: Gemini model identifier.
        _client: Configured genai client.
    """

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.GEMINI_MODEL
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
    ) -> AgentResponse:
        """Generate a response using Google Gemini.

        Args:
            messages: Conversation history.
            system_prompt: Tenant-specific system instructions.

        Returns:
            AgentResponse with the generated text and metadata.

        Raises:
            AIProviderError: If the Gemini API call fails.
        """
        start_time = time.monotonic()

        try:
            # Check if last message needs special processing
            last_msg = messages[-1] if messages else None
            
            if last_msg and last_msg.message_type == MessageType.IMAGE:
                response_text = await self._process_image(last_msg, system_prompt, messages[:-1])
            elif last_msg and last_msg.message_type == MessageType.AUDIO:
                response_text = await self._process_audio(last_msg, system_prompt, messages[:-1])
            else:
                gemini_history = self._build_history(messages)
                response_text = await self._call_gemini(
                    system_prompt, gemini_history, self._model_name
                )
            
            elapsed_ms = (time.monotonic() - start_time) * 1000

            return AgentResponse(
                content=response_text,
                source=ResponseSource.AI,
                cached=False,
                latency_ms=round(elapsed_ms, 2),
                tokens_used=0,
            )

        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(
                f"Gemini API call failed: {exc}"
            ) from exc

    async def _call_gemini(
        self,
        system_prompt: str,
        history: list[types.Content],
        model_name: str | None = None,
    ) -> str:
        """Execute the Gemini API call.

        Args:
            system_prompt: System instructions.
            history: Formatted conversation history.
            model_name: Override model name.

        Returns:
            Generated text response.
        """
        response = await self._client.aio.models.generate_content(
            model=model_name or self._model_name,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )

        if not response.text:
            raise AIProviderError("Gemini returned an empty response")

        logger.info(
            "Gemini response generated: model=%s chars=%d",
            model_name or self._model_name,
            len(response.text),
        )

        return response.text

    @staticmethod
    def _build_history(
        messages: list[Message],
    ) -> list[types.Content]:
        """Convert internal messages to Gemini's history format.

        Args:
            messages: Internal message list.

        Returns:
            Gemini-formatted history.
        """
        history = []
        for msg in messages:
            if msg.message_type != MessageType.TEXT:
                continue
            role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            history.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.content)],
                )
            )
        return history

    async def _process_image(self, message: Message, system_prompt: str, history: list[Message]) -> str:
        """Process image message using vision model with conversation context."""
        settings = get_settings()
        
        if not message.media_url:
            raise AIProviderError("Image message missing media_url")
        
        # Fix localhost URLs to use container name
        media_url = message.media_url.replace("http://localhost:3000", settings.WAHA_API_URL.rstrip("/"))
        
        # Download image with WAHA API key authentication
        headers = {"X-Api-Key": settings.WAHA_API_KEY} if settings.WAHA_API_KEY else {}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Downloading image from: %s", media_url)
                img_response = await client.get(media_url, headers=headers)
                img_response.raise_for_status()
                image_data = img_response.content
            
            # Detect MIME type from response headers
            content_type = img_response.headers.get("content-type", "image/jpeg")
            mime_type = content_type.split(";")[0].strip()
            logger.info("Image downloaded: size=%d bytes, mime=%s", len(image_data), mime_type)
        except Exception as e:
            raise AIProviderError(f"Failed to download image from {media_url}: {e}")
        
        # Build conversation history for context
        gemini_history = self._build_history(history)
        
        # User's caption or a natural prompt
        user_text = message.content if message.content else (
            "O usuário enviou esta imagem. Analise e responda de forma "
            "natural e humanizada, dentro do contexto da conversa."
        )
        
        # Add the image as the last user message with context
        gemini_history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(text=user_text),
                    types.Part(inline_data=types.Blob(
                        mime_type=mime_type,
                        data=image_data
                    ))
                ]
            )
        )
        
        response = await self._client.aio.models.generate_content(
            model=settings.GEMINI_VISION_MODEL,
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        
        if not response.text:
            raise AIProviderError("Vision model returned empty response")
        
        logger.info("Image processed: model=%s", settings.GEMINI_VISION_MODEL)
        return response.text

    async def _process_audio(self, message: Message, system_prompt: str, history: list[Message]) -> str:
        """Process audio message using audio model."""
        settings = get_settings()
        
        if not message.media_url:
            raise AIProviderError("Audio message missing media_url")
        
        # Fix localhost URLs to use container name
        media_url = message.media_url.replace("http://localhost:3000", settings.WAHA_API_URL.rstrip("/"))
        
        # Download audio with WAHA API key authentication
        headers = {"X-Api-Key": settings.WAHA_API_KEY} if settings.WAHA_API_KEY else {}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Downloading audio from: %s", media_url)
                audio_response = await client.get(media_url, headers=headers)
                audio_response.raise_for_status()
                audio_data = audio_response.content
            
            # Detect MIME type from response headers
            content_type = audio_response.headers.get("content-type", "audio/ogg")
            mime_type = content_type.split(";")[0].strip()
            logger.info("Audio downloaded: size=%d bytes, mime=%s", len(audio_data), mime_type)
        except Exception as e:
            raise AIProviderError(f"Failed to download audio from {media_url}: {e}")
        
        # Transcribe audio
        try:
            transcription_response = await self._client.aio.models.generate_content(
                model=settings.GEMINI_AUDIO_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text="Transcreva este áudio:"),
                            types.Part(inline_data=types.Blob(
                                mime_type=mime_type,
                                data=audio_data
                            ))
                        ]
                    )
                ],
            )
            
            if not transcription_response.text:
                raise AIProviderError("Audio transcription failed")
            
            transcription = transcription_response.text
            logger.info("Audio transcribed: %d chars", len(transcription))
        except Exception as e:
            raise AIProviderError(f"Audio transcription error: {e}")
        
        # Generate response based on transcription
        gemini_history = self._build_history(history)
        gemini_history.append(
            types.Content(
                role="user",
                parts=[types.Part(text=transcription)]
            )
        )
        
        return await self._call_gemini(system_prompt, gemini_history, self._model_name)
