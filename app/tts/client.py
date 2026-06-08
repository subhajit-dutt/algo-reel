from typing import Protocol

from openai import AsyncOpenAI

from app.config import TTSResponseFormat, get_settings


class TTSClient(Protocol):
    async def synthesize(self, *, text: str, voice: str, instructions: str) -> bytes: ...


class OpenAITTSClient:
    """Direct OpenAI audio.speech client. Retries transient failures up to max_retries.

    CancelledError is a BaseException (not Exception), so cooperative cancellation
    is never swallowed by the retry loop.
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        model: str,
        response_format: TTSResponseFormat,
        max_retries: int,
    ) -> None:
        self._client = client
        self._model = model
        self._response_format = response_format
        self._max_retries = max_retries

    async def synthesize(self, *, text: str, voice: str, instructions: str) -> bytes:
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                response = await self._client.audio.speech.create(
                    model=self._model,
                    voice=voice,
                    input=text,
                    instructions=instructions,
                    response_format=self._response_format,
                )
                return response.content
            # Broad catch is intentional: any transient API/network error is retried
            # up to max_retries. CancelledError is a BaseException, so it still escapes.
            except Exception:
                if attempt == attempts - 1:
                    raise
        raise RuntimeError("unreachable: loop always returns or raises")


def get_tts_client() -> TTSClient:
    s = get_settings()
    client = AsyncOpenAI(api_key=s.openai_api_key, timeout=float(s.tts_timeout_seconds))
    return OpenAITTSClient(
        client,
        model=s.tts_model,
        response_format=s.tts_response_format,
        max_retries=s.tts_max_retries,
    )
