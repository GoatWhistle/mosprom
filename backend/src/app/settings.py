from collections.abc import Mapping
from dataclasses import dataclass, field


class ConfigError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    llm_timeout_s: float = 120.0
    mirror_base_url: str = ""
    mirror_api_key: str = field(default="", repr=False)
    mirror_model: str = ""

    @property
    def mirror_enabled(self) -> bool:
        return bool(self.mirror_base_url and self.mirror_api_key and self.mirror_model)


def load_settings(env: Mapping[str, str]) -> Settings:
    return Settings(
        llm_timeout_s=_number(env, "LLM_TIMEOUT_SECONDS", 120.0),
        mirror_base_url=env.get("MIRROR_BASE_URL", "").strip(),
        mirror_api_key=env.get("MIRROR_API_KEY", "").strip(),
        mirror_model=env.get("MIRROR_MODEL", "").strip(),
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
