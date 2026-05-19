from decimal import Decimal

from app.config import get_settings


def test_settings_exposes_llm_config() -> None:
    s = get_settings()
    assert s.openrouter_api_key == "test-openrouter-key"
    assert s.llm_base_url == "https://openrouter.ai/api/v1"
    assert s.llm_script_model == "anthropic/claude-haiku-4.5"
    assert s.llm_script_max_tokens == 4000
    assert s.llm_timeout_seconds == 60
    assert s.max_script_cost_usd == Decimal("0.10")
    assert s.max_scenes_per_video == 12
