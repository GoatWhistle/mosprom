from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentConfig:
    correction_limit: int = 3
    max_steps: int = 60
    tool_timeout_s: float = 120.0
    slice_timeout_s: float = 900.0
    save_timeout_s: float = 300.0
    max_attachment_bytes: int = 64 * 1024 * 1024
    max_artifact_bytes: int = 512 * 1024 * 1024
