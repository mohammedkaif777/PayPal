import hashlib
import json

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.policy import PolicyCreate, PolicyResponse
from app.services.idempotency import IdempotencyService
from app.services.policy import PolicyService

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PolicyResponse:
    if idempotency_key:
        req_hash = hashlib.sha256(
            json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode("utf-8")
        ).hexdigest()
        idem = IdempotencyService.begin(
            db, scope="create_policy", key=idempotency_key, request_hash=req_hash
        )
        if not idem.created:
            response.status_code = idem.record.status_code or status.HTTP_201_CREATED
            return PolicyResponse.model_validate(idem.record.response_json)

        policy = PolicyService.create(db, payload, actor=actor.name)
        db.flush()
        db.refresh(policy)
        resp_obj = PolicyResponse.model_validate(policy)
        IdempotencyService.complete(
            db,
            idem.record,
            status_code=status.HTTP_201_CREATED,
            response=resp_obj.model_dump(mode="json"),
        )
        db.commit()
        return resp_obj

    policy = PolicyService.create(db, payload, actor=actor.name)
    db.commit()
    db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.get("", response_model=list[PolicyResponse])
def list_policies(
    shipment_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[PolicyResponse]:
    rows = PolicyService.list_all(db, shipment_id=shipment_id, status=status_filter)
    return [PolicyResponse.model_validate(row) for row in rows]


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> PolicyResponse:
    return PolicyResponse.model_validate(PolicyService.get(db, policy_id))


@router.post("/{policy_id}/activate", response_model=PolicyResponse)
def activate_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PolicyResponse:
    policy = PolicyService.transition(db, policy_id, "ACTIVE", actor=actor.name)
    db.commit()
    db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.post("/{policy_id}/cancel", response_model=PolicyResponse)
def cancel_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PolicyResponse:
    policy = PolicyService.transition(db, policy_id, "CANCELLED", actor=actor.name)
    db.commit()
    db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.post("/{policy_id}/expire", response_model=PolicyResponse)
def expire_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PolicyResponse:
    policy = PolicyService.transition(db, policy_id, "EXPIRED", actor=actor.name)
    db.commit()
    db.refresh(policy)
    return PolicyResponse.model_validate(policy)
