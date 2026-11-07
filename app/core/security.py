import hashlib
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models.api_key import ApiKey


@dataclass(frozen=True)
class Actor:
    id: int
    name: str
    role: str


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_current_actor(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Actor:
    if not x_api_key:
        raise AppError("Missing API key", code="unauthorized", status_code=401)
    api_key = db.scalar(
        select(ApiKey).where(
            ApiKey.key_hash == hash_api_key(x_api_key),
            ApiKey.active.is_(True),
        )
    )
    if api_key is None:
        raise AppError("Invalid API key", code="unauthorized", status_code=401)
    return Actor(id=api_key.id, name=api_key.name, role=api_key.role)


def require_roles(*roles: str):
    def dependency(actor: Actor = Depends(get_current_actor)) -> Actor:
        if actor.role not in roles:
            raise AppError(
                "Insufficient permissions",
                code="forbidden",
                status_code=403,
                details={"required_roles": list(roles)},
            )
        return actor

    return dependency
