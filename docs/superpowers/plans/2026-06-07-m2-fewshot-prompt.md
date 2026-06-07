# M2 Few-Shot Prompt (Manim) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a named 3Blue1Brown style reference and one worked, schema-valid `VideoScript` few-shot example to the Pass-1 prompt for the manim renderer, leaving ai_image untouched.

**Architecture:** Prompt-only change to `app/llm/prompts.py`. The few-shot example is built by constructing the real `VideoScript`/`Scene` models (so schema drift fails at import) and serialized to JSON. It is injected per-renderer inside `build_user_prompt` via an early return — never in the static `SCRIPT_SYSTEM_PROMPT`, because `script_agent` is constructed once at import with a static system prompt.

**Tech Stack:** Python 3.12, Pydantic v2, pytest. No new dependencies, no schema migration, no model/config change.

**Spec:** [docs/superpowers/specs/2026-06-07-m2-fewshot-prompt-design.md](../specs/2026-06-07-m2-fewshot-prompt-design.md)

---

### Task 1: Few-shot manim example + 3B1B style reference in `build_user_prompt`

**Files:**
- Modify: `app/llm/prompts.py`
- Test: `tests/llm/test_prompts.py`

- [ ] **Step 1: Write the failing tests**

Add these to `tests/llm/test_prompts.py`. Update the existing import line at the top of the file to also import `_MANIM_FEWSHOT_SCRIPT`:

```python
from app.llm.prompts import SCRIPT_SYSTEM_PROMPT, _MANIM_FEWSHOT_SCRIPT, build_user_prompt
```

Append these two test cases to the existing `TestBuildUserPrompt` class:

```python
    def test_manim_includes_style_reference_and_worked_example(self) -> None:
        body = build_user_prompt(
            prompt="eigenvalues", renderer=Renderer.MANIM, duration_target_seconds=60, max_scenes=12
        )
        assert "3Blue1Brown" in body
        assert "Why a² + b² = c²" in body  # worked-example title
        assert "well-formed VideoScript" in body

    def test_ai_image_excludes_manim_example_and_style_reference(self) -> None:
        body = build_user_prompt(
            prompt="eigenvalues", renderer=Renderer.AI_IMAGE, duration_target_seconds=60, max_scenes=12
        )
        assert "3Blue1Brown" not in body
        assert "Why a² + b² = c²" not in body
        assert "well-formed VideoScript" not in body
```

Add a new test class for the example's validity:

```python
class TestManimFewShot:
    def test_example_is_valid_videoscript(self) -> None:
        script = _MANIM_FEWSHOT_SCRIPT
        assert script.renderer is Renderer.MANIM
        assert len(script.scenes) >= 3
        assert all(len(scene.narration) <= 300 for scene in script.scenes)
        assert all(scene.duration_seconds > 0 for scene in script.scenes)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/llm/test_prompts.py -v`
Expected: collection/import error or FAIL — `_MANIM_FEWSHOT_SCRIPT` does not exist yet, and `build_user_prompt` does not yet emit `"3Blue1Brown"`.

- [ ] **Step 3: Implement the prompts.py changes**

Replace the entire contents of `app/llm/prompts.py` with:

```python
from app.domain.enums import Renderer
from app.domain.script import Scene, VideoScript

SCRIPT_SYSTEM_PROMPT = """You are a video-script planner for short tutorial videos.

You will be given:
- a user prompt describing the video topic
- a renderer ('manim' for diagrammatic/mathematical animation, or 'ai_image' for still-image-with-motion)
- a target total duration in seconds

You MUST return a structured VideoScript with:
- title: short title
- scenes: 3 to MAX scenes (specified in the user message)
- per scene: index (0-based), narration (<= 300 chars, TTS-friendly), visual_prompt, duration_seconds
- total_duration: sum of scene durations, within +/- 20 percent of target
- renderer and voice mirror the inputs

Narration should be plain spoken English suitable for text-to-speech. No stage directions.
"""


_RENDERER_HINTS = {
    Renderer.MANIM: (
        "Renderer is manim. For each scene, visual_prompt MUST describe a diagram, "
        "mathematical animation, or geometric construction. Avoid photographic descriptions."
    ),
    Renderer.AI_IMAGE: (
        "Renderer is ai_image. For each scene, visual_prompt MUST describe a single still image "
        "(photograph or illustration). Ken-Burns motion is added separately; do not request motion."
    ),
}

_MANIM_STYLE_REF = (
    "Match the pacing and visual style of 3Blue1Brown: clean geometric constructions, "
    "smooth transforms, one idea per scene."
)

# Built through the real models so any VideoScript/Scene schema drift fails at import
# instead of silently shipping a malformed few-shot example.
_MANIM_FEWSHOT_SCRIPT = VideoScript(
    title="Why a² + b² = c²",
    renderer=Renderer.MANIM,
    voice="alloy",
    total_duration=60.0,
    scenes=[
        Scene(
            index=0,
            narration=(
                "Start with a right triangle. Label the two short sides a and b, "
                "and the long side opposite the right angle c."
            ),
            visual_prompt=(
                "A right triangle centered on screen; the legs fade in labeled a and b, "
                "then the hypotenuse fades in labeled c."
            ),
            duration_seconds=12.0,
        ),
        Scene(
            index=1,
            narration=(
                "Now grow a square outward from each side. Their areas are a squared, "
                "b squared, and c squared."
            ),
            visual_prompt=(
                "Squares extrude outward from each of the three sides; each square is "
                "labeled with its area a^2, b^2, c^2."
            ),
            duration_seconds=16.0,
        ),
        Scene(
            index=2,
            narration=(
                "Watch the two smaller squares. Their combined area rearranges to "
                "exactly fill the largest square."
            ),
            visual_prompt=(
                "The a^2 and b^2 tiles slide and transform, tiling perfectly into the "
                "c^2 square with no gaps or overlap."
            ),
            duration_seconds=18.0,
        ),
        Scene(
            index=3,
            narration=(
                "That is the Pythagorean theorem: a squared plus b squared equals c squared."
            ),
            visual_prompt=(
                "The equation a^2 + b^2 = c^2 writes onto the screen while the triangle "
                "dims into the background."
            ),
            duration_seconds=14.0,
        ),
    ],
)
_MANIM_FEWSHOT_JSON = _MANIM_FEWSHOT_SCRIPT.model_dump_json(indent=2)


def build_user_prompt(
    *, prompt: str, renderer: Renderer, duration_target_seconds: int, max_scenes: int
) -> str:
    base = (
        f"User prompt: {prompt}\n"
        f"Renderer: {renderer.value}\n"
        f"Target total duration: {duration_target_seconds} seconds\n"
        f"Maximum scenes: {max_scenes}\n\n"
        f"{_RENDERER_HINTS[renderer]}"
    )
    if renderer is not Renderer.MANIM:
        return base
    return (
        f"{base}\n\n"
        f"{_MANIM_STYLE_REF}\n\n"
        f"Here is a well-formed VideoScript for this renderer:\n"
        f"{_MANIM_FEWSHOT_JSON}"
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/llm/test_prompts.py -v`
Expected: PASS — all tests in `TestSystemPrompt`, `TestBuildUserPrompt`, and `TestManimFewShot` green.

- [ ] **Step 5: Run lint, typecheck, and the full suite**

Run: `make fmt && make lint && make typecheck && make test`
Expected: ruff clean, mypy clean, full suite green with coverage ≥80%.

- [ ] **Step 6: Commit**

```bash
git add app/llm/prompts.py tests/llm/test_prompts.py
git commit -m "feat(m2): few-shot manim example + 3B1B style ref in Pass-1 prompt"
```

---

### Manual verification (post-merge, not a CI step)

`make smoke-llm` exercises the real OpenRouter endpoint and is the only way to judge prompt *quality* (`TestModel` is blind to it — M2 spec §13). This requires a valid `OPENROUTER_API_KEY` in `.env`; the current value is a placeholder, so fix the key first (see the earlier 401 diagnosis). Run:

```bash
make smoke-llm
```

Eyeball that a manim job returns a coherent, well-structured `VideoScript` (clean scene plan, narration ≤300 chars, durations within ±20% of target). Repeat across the 30/60/180s tiers to confirm the single example isn't over-anchoring scene count/length (spec §5 risk).

---

## Self-Review

**Spec coverage:**
- Named 3B1B style reference for manim → `_MANIM_STYLE_REF`, asserted in `test_manim_includes_style_reference_and_worked_example`. ✓
- One worked, schema-valid `VideoScript` example for manim → `_MANIM_FEWSHOT_SCRIPT` (built via models), asserted in `TestManimFewShot`. ✓
- Per-renderer injection, ai_image unchanged → early return in `build_user_prompt`, asserted in `test_ai_image_excludes_manim_example_and_style_reference`. ✓
- No schema change / no critic / no model change → `VideoScript` untouched; only `prompts.py` + its test modified. ✓
- Schema drift fails at import → example constructed through `VideoScript`/`Scene`, not a hand-typed string. ✓

**Placeholder scan:** No TBD/TODO. Example narration strings are concrete and final. All code blocks complete. ✓

**Type consistency:** `_MANIM_FEWSHOT_SCRIPT` (Task 1 def) matches the test import; `Scene`/`VideoScript` field names (`index`, `narration`, `visual_prompt`, `duration_seconds`, `title`, `renderer`, `voice`, `total_duration`, `scenes`) match `app/domain/script.py`. `build_user_prompt` signature unchanged from current callers (`script_agent.generate_script`). ✓
