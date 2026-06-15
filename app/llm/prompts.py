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


MANIM_CODEGEN_SYSTEM_PROMPT = """You write Manim Community Edition (v0.18+) Python code for one short tutorial scene.

Hard requirements:
- Output ONLY a complete, self-contained Python module. No prose, no markdown fences.
- Define exactly one Scene subclass named `GeneratedScene` with a `construct(self)` method.
- `from manim import *` at the top. Do not import anything else.
- No file, network, OS, or subprocess access. No reading external assets.
- The animation MUST run for approximately the given duration in seconds. Use
  `self.play(..., run_time=...)` and `self.wait(...)` so the total runtime matches.
- Keep it to one clear idea. Prefer Text/MarkupText, MathTex, shapes, arrows, and
  smooth transforms in the style of 3Blue1Brown. Use a dark background.
- Do not add audio; narration is muxed in separately.
"""

MANIM_CRITIC_SYSTEM_PROMPT = """You are a pre-render checker for Manim Community code.
Given a Python module and a target duration, decide whether it is safe and likely to
render. Return ok=false with specific issues if: it does not define a Scene subclass
named `GeneratedScene`, it imports modules other than manim, it performs file/network/OS
access, or it has obvious syntax/name errors. Otherwise ok=true.
"""


def build_codegen_prompt(
    *,
    visual_prompt: str,
    narration: str,
    duration_seconds: str,
    prev_code: str | None = None,
    stderr: str | None = None,
) -> str:
    base = (
        f"Visual prompt: {visual_prompt}\n"
        f"Narration (for timing/context, do not render as a caption verbatim): {narration}\n"
        f"Target duration (seconds): {duration_seconds}\n"
    )
    if prev_code is None or stderr is None:
        return base
    return (
        f"{base}\n"
        f"The previous attempt failed. Fix it. Failing code:\n"
        f"```python\n{prev_code}\n```\n"
        f"Error output:\n{stderr}\n"
    )


def build_critic_prompt(*, code: str, duration_seconds: str) -> str:
    return f"Target duration (seconds): {duration_seconds}\n\nCode:\n```python\n{code}\n```"
