from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.tts.client import OpenAITTSClient


class _FakeSpeech:
    def __init__(self, create: AsyncMock) -> None:
        self.create = create


class _FakeAudio:
    def __init__(self, create: AsyncMock) -> None:
        self.speech = _FakeSpeech(create)


class _FakeOpenAI:
    def __init__(self, create: AsyncMock) -> None:
        self.audio = _FakeAudio(create)


def _resp(content: bytes) -> Any:
    obj = AsyncMock()
    obj.content = content
    return obj


def _client(create: AsyncMock, *, max_retries: int = 2) -> OpenAITTSClient:
    return OpenAITTSClient(
        client=_FakeOpenAI(create),
        model="gpt-4o-mini-tts",
        response_format="wav",
        max_retries=max_retries,
    )


async def test_returns_audio_bytes() -> None:
    create = AsyncMock(return_value=_resp(b"RIFFwavbytes"))
    client = _client(create)
    out = await client.synthesize(text="hi", voice="coral", instructions="calm")
    assert out == b"RIFFwavbytes"
    create.assert_awaited_once()
    kwargs = create.await_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini-tts"
    assert kwargs["voice"] == "coral"
    assert kwargs["input"] == "hi"
    assert kwargs["instructions"] == "calm"
    assert kwargs["response_format"] == "wav"


async def test_retries_then_succeeds() -> None:
    create = AsyncMock(side_effect=[RuntimeError("blip"), _resp(b"ok")])
    client = _client(create, max_retries=2)
    out = await client.synthesize(text="hi", voice="coral", instructions="calm")
    assert out == b"ok"
    assert create.await_count == 2


async def test_raises_after_exhausting_retries() -> None:
    create = AsyncMock(side_effect=RuntimeError("down"))
    client = _client(create, max_retries=2)
    with pytest.raises(RuntimeError):
        await client.synthesize(text="hi", voice="coral", instructions="calm")
    assert create.await_count == 3  # initial + 2 retries
