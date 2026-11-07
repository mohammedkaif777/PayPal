from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str
    request_id: str
    before: Any | None
    after: Any | None
    prev_hash: str
    hash: str
    created_at: datetime
