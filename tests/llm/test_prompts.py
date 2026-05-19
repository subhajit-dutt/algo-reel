from app.domain.enums import Renderer
from app.llm.prompts import SCRIPT_SYSTEM_PROMPT, build_user_prompt


class TestSystemPrompt:
    def test_mentions_videoscript_fields(self) -> None:
        assert "narration" in SCRIPT_SYSTEM_PROMPT
        assert "visual_prompt" in SCRIPT_SYSTEM_PROMPT
        assert "duration_seconds" in SCRIPT_SYSTEM_PROMPT


class TestBuildUserPrompt:
    def test_includes_prompt_and_target(self) -> None:
        body = build_user_prompt(
            prompt="merge sort", renderer=Renderer.MANIM, duration_target_seconds=60, max_scenes=12
        )
        assert "merge sort" in body
        assert "60" in body
        assert "manim" in body.lower()
        assert "12" in body

    def test_renderer_style_hint_manim(self) -> None:
        body = build_user_prompt(
            prompt="x", renderer=Renderer.MANIM, duration_target_seconds=60, max_scenes=12
        )
        assert "diagram" in body.lower() or "mathematic" in body.lower()

    def test_renderer_style_hint_ai_image(self) -> None:
        body = build_user_prompt(
            prompt="x", renderer=Renderer.AI_IMAGE, duration_target_seconds=60, max_scenes=12
        )
        assert "still image" in body.lower() or "photograph" in body.lower()
