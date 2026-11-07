import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import request_id_var
from app.models.audit import AuditLog


class AuditService:
    @staticmethod
    def record(
        db: Session,
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before: Any = None,
        after: Any = None,
    ) -> AuditLog:
        previous = db.scalar(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
        )
        prev_hash = previous.hash if previous is not None else "GENESIS"
        request_id = request_id_var.get()
        payload = {
            "actor": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "request_id": request_id,
            "before": before,
            "after": after,
            "prev_hash": prev_hash,
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        )
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        entry = AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            before_json=before,
            after_json=after,
            prev_hash=prev_hash,
            hash=digest,
        )
        db.add(entry)
        db.flush()
        return entry
