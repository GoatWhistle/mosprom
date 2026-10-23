from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    llm_timeout_s: float = 120.0


def load_settings(env: Mapping[str, str]) -> Settings:
    return Settings(llm_timeout_s=_number(env, "LLM_TIMEOUT_SECONDS", 120.0))


def _number(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(f"{name}={raw!r} is not a number") from None
    if value <= 0:
        raise ConfigError(f"{name}={raw!r} must be positive")
    return value
