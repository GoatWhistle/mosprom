import pytest

from app.settings import ConfigError, load_settings


def test_database_url_is_required() -> None:
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_settings({})


def test_defaults_and_overrides() -> None:
    settings = load_settings({"DATABASE_URL": "postgresql://x", "CORRECTION_LIMIT": "5"})

    assert settings.database_url == "postgresql://x"
    assert settings.agent.correction_limit == 5
    assert settings.agent.max_steps == 60
    assert settings.llm_timeout_s == 120.0


@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_numbers_are_rejected(value: str) -> None:
    with pytest.raises(ConfigError, match="TOOL_TIMEOUT_SECONDS"):
        load_settings({"DATABASE_URL": "postgresql://x", "TOOL_TIMEOUT_SECONDS": value})
