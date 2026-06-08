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


def test_tts_and_storage_settings_load() -> None:
    get_settings.cache_clear()
    s = get_settings()
    assert s.openai_api_key == "test-openai-key"  # required, provided by conftest _env
    assert s.tts_model == "gpt-4o-mini-tts"
    assert s.tts_voice_default == "coral"
    assert s.tts_response_format == "wav"
    assert s.tts_max_concurrency == 4
    assert s.tts_max_retries == 2
    assert s.media_root == "./.media"


def test_render_settings_load() -> None:
    get_settings.cache_clear()
    s = get_settings()
    assert s.render_image == "algoreel-render:m4"
    assert s.render_video_size == "1280x720"
    assert s.render_video_fps == 30
    assert s.render_bg_color == "0x0B132B"
    assert s.render_memory == "2g"
    assert s.render_cpus == "1.0"
    assert s.render_pids_limit == 256
    assert s.render_user == "10001:10001"
    assert s.render_timeout_seconds == 120
    assert s.render_result_timeout_seconds == 900
    assert s.compose_result_timeout_seconds == 300
