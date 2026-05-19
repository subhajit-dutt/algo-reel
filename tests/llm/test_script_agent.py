from decimal import Decimal

import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.settings import ModelSettings

from app.domain.enums import Renderer
from app.domain.script import Scene, VideoScript
from app.llm.script_agent import ScriptGenResult, generate_script, script_agent

models.ALLOW_MODEL_REQUESTS = False  # safety: no real API calls in unit tests


def _canned_script(n: int = 4, total: float = 60.0) -> VideoScript:
    per = total / n
    return VideoScript(
        title="merge sort",
        renderer=Renderer.MANIM,
        voice="alloy",
        total_duration=total,
        scenes=[
            Scene(index=i, narration=f"step {i}", visual_prompt=f"diagram {i}", duration_seconds=per)
            for i in range(n)
        ],
    )


class TestGenerateScript:
    async def test_returns_script_and_cost(self) -> None:
        canned = _canned_script()
        with script_agent.override(model=TestModel(custom_output_args=canned.model_dump())):
            result = await generate_script(
                prompt="explain merge sort", renderer=Renderer.MANIM, duration_target_seconds=60
            )
        assert isinstance(result, ScriptGenResult)
        assert result.script.title == "merge sort"
        assert len(result.script.scenes) == 4
        assert result.cost_usd >= Decimal("0")
        assert result.model == "anthropic/claude-haiku-4.5"

    async def test_passes_user_prompt_through(self) -> None:
        canned = _canned_script()
        captured: dict[str, str] = {}

        class CapturingModel(TestModel):
            async def request(
                self,
                messages: list[ModelMessage],
                model_settings: ModelSettings | None,
                model_request_parameters: ModelRequestParameters,
            ) -> ModelResponse:
                captured["last_user"] = next(
                    (
                        part.content
                        for m in reversed(messages)
                        for part in m.parts
                        if getattr(part, "part_kind", "") == "user-prompt"
                    ),
                    "",
                )
                return await super().request(messages, model_settings, model_request_parameters)

        with script_agent.override(model=CapturingModel(custom_output_args=canned.model_dump())):
            await generate_script(
                prompt="quicksort vs mergesort",
                renderer=Renderer.MANIM,
                duration_target_seconds=60,
            )
        assert "quicksort vs mergesort" in captured["last_user"]
        assert "manim" in captured["last_user"].lower()

    async def test_rejects_when_live_calls_blocked(self) -> None:
        with pytest.raises(Exception):
            await generate_script(
                prompt="x", renderer=Renderer.MANIM, duration_target_seconds=60
            )
