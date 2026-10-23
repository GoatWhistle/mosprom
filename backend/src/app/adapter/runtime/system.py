import secrets
import uuid
from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidGenerator:
    def new_id(self) -> str:
        return str(uuid.uuid4())

    def new_token(self) -> str:
        return secrets.token_urlsafe(32)
