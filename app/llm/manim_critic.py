import ast
from dataclasses import dataclass, field
from decimal import Decimal

from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings
from app.llm.pricing import compute_cost
from app.llm.prompts import MANIM_CRITIC_SYSTEM_PROMPT, build_critic_prompt

_SCENE_CLASS = "GeneratedScene"


class Critique(BaseModel):
    ok: bool
    issues: list[str] = []


@dataclass(frozen=True)
class CritiqueResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    cost_usd: Decimal = Decimal("0")


def static_gate(code: str) -> tuple[bool, list[str]]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, [f"syntax error: {exc}"]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    if not any(c.name == _SCENE_CLASS for c in classes):
        return False, [f"no class named {_SCENE_CLASS}"]
    return True, []


def _build_agent() -> Agent[None, Critique]:
    s = get_settings()
    client = AsyncOpenAI(
        base_url=s.llm_base_url,
        api_key=s.openrouter_api_key,
        default_headers={"HTTP-Referer": "https://algo-reel.local", "X-Title": "algo-reel"},
        timeout=float(s.llm_timeout_seconds),
    )
    model = OpenAIChatModel(s.llm_critic_model, provider=OpenAIProvider(openai_client=client))
    return Agent(model, output_type=Critique, system_prompt=MANIM_CRITIC_SYSTEM_PROMPT)


critic_agent: Agent[None, Critique] = _build_agent()


async def critique(*, code: str, duration_seconds: str) -> CritiqueResult:
    ok, issues = static_gate(code)
    if not ok:
        return CritiqueResult(ok=False, issues=issues, cost_usd=Decimal("0"))
    s = get_settings()
    result = await critic_agent.run(build_critic_prompt(code=code, duration_seconds=duration_seconds))
    usage = result.usage
    cost = compute_cost(
        s.llm_critic_model, input_tokens=usage.input_tokens or 0, output_tokens=usage.output_tokens or 0
    )
    return CritiqueResult(ok=result.output.ok, issues=result.output.issues, cost_usd=cost)
