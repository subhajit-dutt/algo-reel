from app.domain.enums import Renderer

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


def build_user_prompt(
    *, prompt: str, renderer: Renderer, duration_target_seconds: int, max_scenes: int
) -> str:
    return (
        f"User prompt: {prompt}\n"
        f"Renderer: {renderer.value}\n"
        f"Target total duration: {duration_target_seconds} seconds\n"
        f"Maximum scenes: {max_scenes}\n\n"
        f"{_RENDERER_HINTS[renderer]}"
    )
