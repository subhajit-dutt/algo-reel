from app.domain.enums import Renderer
from app.llm.prompts import _MANIM_FEWSHOT_SCRIPT, SCRIPT_SYSTEM_PROMPT, build_user_prompt


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

    def test_manim_includes_style_reference_and_worked_example(self) -> None:
        body = build_user_prompt(
            prompt="eigenvalues", renderer=Renderer.MANIM, duration_target_seconds=60, max_scenes=12
        )
        assert "3Blue1Brown" in body
        assert "Why a² + b² = c²" in body  # worked-example title
        assert "well-formed VideoScript" in body

    def test_ai_image_excludes_manim_example_and_style_reference(self) -> None:
        body = build_user_prompt(
            prompt="eigenvalues",
            renderer=Renderer.AI_IMAGE,
            duration_target_seconds=60,
            max_scenes=12,
        )
        assert "3Blue1Brown" not in body
        assert "Why a² + b² = c²" not in body
        assert "well-formed VideoScript" not in body


class TestManimFewShot:
    def test_example_is_valid_videoscript(self) -> None:
        script = _MANIM_FEWSHOT_SCRIPT
        assert script.renderer is Renderer.MANIM
        assert len(script.scenes) >= 3
        assert all(len(scene.narration) <= 300 for scene in script.scenes)
        assert all(scene.duration_seconds > 0 for scene in script.scenes)
        total = sum(scene.duration_seconds for scene in script.scenes)
        assert abs(total - script.total_duration) <= 0.2 * script.total_duration
