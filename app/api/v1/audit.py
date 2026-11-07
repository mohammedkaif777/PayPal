from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin")),
) -> list[AuditLogResponse]:
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    ).all()
    return [
        AuditLogResponse(
            id=row.id,
            actor=row.actor,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            request_id=row.request_id,
            before=row.before_json,
            after=row.after_json,
            prev_hash=row.prev_hash,
            hash=row.hash,
            created_at=row.created_at,
        )
        for row in rows
    ]
