import pytest

from app.settings import ConfigError, load_settings


def test_defaults_and_overrides() -> None:
    assert load_settings({}).llm_timeout_s == 120.0
    assert load_settings({"LLM_TIMEOUT_SECONDS": "30"}).llm_timeout_s == 30.0


@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_numbers_are_rejected(value: str) -> None:
    with pytest.raises(ConfigError, match="LLM_TIMEOUT_SECONDS"):
        load_settings({"LLM_TIMEOUT_SECONDS": value})
