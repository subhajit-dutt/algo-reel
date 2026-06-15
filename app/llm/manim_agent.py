from dataclasses import dataclass
from decimal import Decimal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings
from app.llm.pricing import compute_cost
from app.llm.prompts import MANIM_CODEGEN_SYSTEM_PROMPT, build_codegen_prompt


class ManimCode(BaseModel):
    code: str = Field(min_length=1)


@dataclass(frozen=True)
class ManimCodeResult:
    code: str
    cost_usd: Decimal
    model: str


def _build_agent() -> Agent[None, ManimCode]:
    s = get_settings()
    client = AsyncOpenAI(
        base_url=s.llm_base_url,
        api_key=s.openrouter_api_key,
        default_headers={"HTTP-Referer": "https://algo-reel.local", "X-Title": "algo-reel"},
        timeout=float(s.llm_timeout_seconds),
    )
    model = OpenAIChatModel(s.llm_codegen_model, provider=OpenAIProvider(openai_client=client))
    return Agent(model, output_type=ManimCode, system_prompt=MANIM_CODEGEN_SYSTEM_PROMPT)


manim_agent: Agent[None, ManimCode] = _build_agent()


async def generate_manim_code(
    *,
    visual_prompt: str,
    narration: str,
    duration_seconds: str,
    model: str,
    prev_code: str | None = None,
    stderr: str | None = None,
) -> ManimCodeResult:
    s = get_settings()
    user_message = build_codegen_prompt(
        visual_prompt=visual_prompt,
        narration=narration,
        duration_seconds=duration_seconds,
        prev_code=prev_code,
        stderr=stderr,
    )
    run_model = OpenAIChatModel(
        model,
        provider=OpenAIProvider(
            openai_client=AsyncOpenAI(
                base_url=s.llm_base_url,
                api_key=s.openrouter_api_key,
                default_headers={"HTTP-Referer": "https://algo-reel.local", "X-Title": "algo-reel"},
                timeout=float(s.llm_timeout_seconds),
            )
        ),
    )
    result = await manim_agent.run(user_message, model=run_model)
    usage = result.usage
    cost = compute_cost(
        model, input_tokens=usage.input_tokens or 0, output_tokens=usage.output_tokens or 0
    )
    return ManimCodeResult(code=result.output.code, cost_usd=cost, model=model)
