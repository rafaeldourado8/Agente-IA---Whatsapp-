"""Google Gemini AI provider implementation.

Wraps the Google Generative AI SDK to generate conversational
responses. Converts the internal Message format to Gemini's
expected input format.
"""

from __future__ import annotations

import logging
import time

import google.generativeai as genai

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
        _model: Configured GenerativeModel instance.
    """

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.GEMINI_MODEL
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(self._model_name)

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
        history: list[dict[str, str]],
    ) -> str:
        """Execute the Gemini API call.

        Args:
            system_prompt: System instructions.
            history: Formatted conversation history.

        Returns:
            Generated text response.
        """
        chat = self._model.start_chat(history=history[:-1])

        last_message = history[-1]["parts"] if history else ""

        full_prompt = (
            f"{system_prompt}\n\n{last_message}"
            if not history[:-1]
            else last_message
        )

        response = await chat.send_message_async(full_prompt)

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
    ) -> list[dict[str, str]]:
        """Convert internal messages to Gemini's history format.

        Gemini expects: [{"role": "user"|"model", "parts": "text"}, ...]

        Args:
            messages: Internal message list.

        Returns:
            Gemini-formatted history.
        """
        history = []
        for msg in messages:
            role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            history.append({
                "role": role,
                "parts": msg.content,
            })
        return history
