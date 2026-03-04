"""Google Gemini AI provider implementation.

Wraps the Google Generative AI SDK to generate conversational
responses. Converts the internal Message format to Gemini's
expected input format.
"""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import types

from app.config import get_settings
from app.core.exceptions import AIProviderError
from app.core.interfaces import AIProvider
from app.models.message import Message, MessageRole
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
            gemini_history = self._build_history(messages)
            response = await self._call_gemini(
                system_prompt, gemini_history
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000

            return AgentResponse(
                content=response,
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
    ) -> str:
        """Execute the Gemini API call.

        Args:
            system_prompt: System instructions.
            history: Formatted conversation history.

        Returns:
            Generated text response.
        """
        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )

        if not response.text:
            raise AIProviderError("Gemini returned an empty response")

        logger.info(
            "Gemini response generated: model=%s chars=%d",
            self._model_name,
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
            role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            history.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.content)],
                )
            )
        return history
