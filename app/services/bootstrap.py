from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_api_key
from app.models.api_key import ApiKey


def seed_api_keys(db: Session) -> None:
    settings = get_settings()
    keys = {
        "admin": (settings.admin_api_key, "admin"),
        "operator": (settings.operator_api_key, "operator"),
        "reviewer": (settings.reviewer_api_key, "reviewer"),
        "read_only": (settings.readonly_api_key, "read_only"),
    }
    for name, (raw_key, role) in keys.items():
        key_hash = hash_api_key(raw_key)
        existing = db.scalar(select(ApiKey).where(ApiKey.name == name))
        if existing is not None:
            existing.key_hash = key_hash
            existing.key_prefix = raw_key[:8]
            existing.role = role
            existing.active = True
            continue
        db.add(
            ApiKey(
                name=name,
                key_prefix=raw_key[:8],
                key_hash=key_hash,
                role=role,
                active=True,
            )
        )
    db.flush()
