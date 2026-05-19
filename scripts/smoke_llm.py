import asyncio
import os
import sys

from app.domain.enums import Renderer
from app.llm.script_agent import generate_script


async def main() -> int:
    if os.environ.get("ALGOREEL_ALLOW_LIVE_LLM") != "1":
        print("set ALGOREEL_ALLOW_LIVE_LLM=1 to run a live LLM call", file=sys.stderr)
        return 2
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Explain quicksort in 60 seconds"
    result = await generate_script(
        prompt=prompt, renderer=Renderer.MANIM, duration_target_seconds=60
    )
    print(f"model:           {result.model}")
    print(f"cost_usd:        {result.cost_usd}")
    print(f"title:           {result.script.title}")
    print(f"total_duration:  {result.script.total_duration}")
    print(f"scene count:     {len(result.script.scenes)}")
    for s in result.script.scenes:
        print(f"  [{s.index}] {s.duration_seconds:>5.1f}s  {s.narration[:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
