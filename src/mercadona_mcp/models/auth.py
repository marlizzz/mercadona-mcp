"""Authentication status models without secret material."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuthStatus(BaseModel):
    """Safe local-session state exposed to callers."""

    model_config = ConfigDict(frozen=True)

    connected: bool
    reauthentication_required: bool = False
    expires_at: datetime | None = None
