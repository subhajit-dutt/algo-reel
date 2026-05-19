from dataclasses import dataclass
from decimal import Decimal

from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings
from app.domain.enums import Renderer
from app.domain.script import VideoScript
from app.llm.pricing import compute_cost
from app.llm.prompts import SCRIPT_SYSTEM_PROMPT, build_user_prompt


@dataclass(frozen=True)
class ScriptGenResult:
    script: VideoScript
    cost_usd: Decimal
    model: str


def _build_agent() -> Agent[None, VideoScript]:
    s = get_settings()
    client = AsyncOpenAI(
        base_url=s.llm_base_url,
        api_key=s.openrouter_api_key,
        default_headers={
            "HTTP-Referer": "https://algo-reel.local",
            "X-Title": "algo-reel",
        },
        timeout=float(s.llm_timeout_seconds),
    )
    model = OpenAIChatModel(s.llm_script_model, provider=OpenAIProvider(openai_client=client))
    return Agent(
        model,
        output_type=VideoScript,
        system_prompt=SCRIPT_SYSTEM_PROMPT,
    )


script_agent: Agent[None, VideoScript] = _build_agent()


async def generate_script(
    *, prompt: str, renderer: Renderer, duration_target_seconds: int
) -> ScriptGenResult:
    s = get_settings()
    user_message = build_user_prompt(
        prompt=prompt,
        renderer=renderer,
        duration_target_seconds=duration_target_seconds,
        max_scenes=s.max_scenes_per_video,
    )
    result = await script_agent.run(user_message)
    usage = result.usage
    cost = compute_cost(
        s.llm_script_model,
        input_tokens=usage.input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
    )
    return ScriptGenResult(script=result.output, cost_usd=cost, model=s.llm_script_model)
