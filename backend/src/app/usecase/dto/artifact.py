from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactDTO:
    id: str
    run_id: str
    kind: str
    scene_version: int
    name: str
    content_type: str
    size: int
    sha256: str
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactBlob:
    meta: ArtifactDTO
    data: bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactChunk:
    run_id: str
    kind: str
    scene_version: int
    chunk_index: int
    chunk_count: int
    sha256: str
    data: bytes
