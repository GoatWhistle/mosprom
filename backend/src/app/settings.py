from collections.abc import Mapping
from dataclasses import dataclass, field

from app.usecase.config import AgentConfig


class ConfigError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    pool_max_size: int = 10
    llm_timeout_s: float = 120.0
    agent: AgentConfig = field(default_factory=AgentConfig)


def load_settings(env: Mapping[str, str]) -> Settings:
    database_url = env.get("DATABASE_URL", "").strip()
    if not database_url:
        raise ConfigError(
            "DATABASE_URL is required, for example postgresql://user:pass@db:5432/brim"
        )
    defaults = AgentConfig()
    return Settings(
        database_url=database_url,
        pool_max_size=int(_number(env, "DB_POOL_MAX_SIZE", 10)),
        llm_timeout_s=_number(env, "LLM_TIMEOUT_SECONDS", 120.0),
        agent=AgentConfig(
            correction_limit=int(_number(env, "CORRECTION_LIMIT", defaults.correction_limit)),
            max_steps=int(_number(env, "AGENT_MAX_STEPS", defaults.max_steps)),
            tool_timeout_s=_number(env, "TOOL_TIMEOUT_SECONDS", defaults.tool_timeout_s),
            slice_timeout_s=_number(env, "SLICE_TIMEOUT_SECONDS", defaults.slice_timeout_s),
            save_timeout_s=_number(env, "SAVE_TIMEOUT_SECONDS", defaults.save_timeout_s),
        ),
    )


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
