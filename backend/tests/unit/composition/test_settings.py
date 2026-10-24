import pytest

from app.settings import ConfigError, load_settings


def test_defaults_and_overrides() -> None:
    assert load_settings({}).llm_timeout_s == 120.0
    assert load_settings({"LLM_TIMEOUT_SECONDS": "30"}).llm_timeout_s == 30.0


@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_numbers_are_rejected(value: str) -> None:
    with pytest.raises(ConfigError, match="LLM_TIMEOUT_SECONDS"):
        load_settings({"LLM_TIMEOUT_SECONDS": value})


def test_mirror_requires_url_key_and_model() -> None:
    env = {
        "MIRROR_BASE_URL": "https://llm.example/v1",
        "MIRROR_API_KEY": "secret",
        "MIRROR_MODEL": "qwen",
    }
    settings = load_settings(env)
    assert settings.mirror_enabled
    assert "secret" not in repr(settings)
    for name in env:
        assert not load_settings({**env, name: " "}).mirror_enabled
