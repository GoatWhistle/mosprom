import hashlib
from enum import StrEnum

from app.domain.errors import ChecksumMismatch, InvalidArtifact


class ArtifactKind(StrEnum):
    GCODE = "gcode"
    THREE_MF = "3mf"


REQUIRED_KINDS = frozenset(ArtifactKind)

CONTENT_TYPES = {
    ArtifactKind.GCODE: "text/x.gcode",
    ArtifactKind.THREE_MF: "model/3mf",
}


def parse_kind(raw: str) -> ArtifactKind:
    try:
        return ArtifactKind(raw)
    except ValueError:
        raise InvalidArtifact(f"Unknown artifact kind {raw!r}") from None


def verify_chunk_plan(chunk_index: int, chunk_count: int) -> None:
    if chunk_count < 1 or not 0 <= chunk_index < chunk_count:
        raise InvalidArtifact("Chunk index is outside the declared chunk count")


def verify_sha256(declared: str, data: bytes) -> str:
    actual = hashlib.sha256(data).hexdigest()
    if actual != declared.lower():
        raise ChecksumMismatch()
    return actual
