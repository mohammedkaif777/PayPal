import hashlib
import json

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.claim import ClaimResponse, ClaimReviewRequest, ClaimSubmitRequest
from app.services.claims import ClaimsEngine
from app.services.idempotency import IdempotencyService

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def submit_claim(
    payload: ClaimSubmitRequest,
    response: Response,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> ClaimResponse:
    req_hash = hashlib.sha256(
        json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    idem = IdempotencyService.begin(
        db, scope="submit_claim", key=payload.idempotency_key, request_hash=req_hash
    )
    if not idem.created:
        response.status_code = idem.record.status_code or status.HTTP_201_CREATED
        return ClaimResponse.model_validate(idem.record.response_json)

    claim = ClaimsEngine.submit(
        db,
        policy_id=payload.policy_id,
        trigger_code=payload.trigger_code,
        occurrence_key=payload.occurrence_key,
        idempotency_key=payload.idempotency_key,
        actor=actor.name,
    )
    db.flush()
    db.refresh(claim)
    resp_obj = ClaimResponse.model_validate(claim)
    IdempotencyService.complete(
        db,
        idem.record,
        status_code=status.HTTP_201_CREATED,
        response=resp_obj.model_dump(mode="json"),
    )
    db.commit()
    return resp_obj


@router.get("", response_model=list[ClaimResponse])
def list_claims(
    shipment_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[ClaimResponse]:
    rows = ClaimsEngine.list_all(
        db, shipment_id=shipment_id, status_filter=status_filter
    )
    return [ClaimResponse.model_validate(r) for r in rows]


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> ClaimResponse:
    return ClaimResponse.model_validate(ClaimsEngine.get(db, claim_id))


@router.post("/{claim_id}/evaluate", response_model=ClaimResponse)
def evaluate_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> ClaimResponse:
    claim = ClaimsEngine.evaluate(db, claim_id, actor=actor.name)
    db.commit()
    db.refresh(claim)
    return ClaimResponse.model_validate(claim)


@router.post("/{claim_id}/review", response_model=ClaimResponse)
def review_claim(
    claim_id: int,
    payload: ClaimReviewRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("reviewer", "admin")),
) -> ClaimResponse:
    claim = ClaimsEngine.review(
        db,
        claim_id,
        decision=payload.decision,
        notes=payload.notes,
        actor=actor.name,
    )
    db.commit()
    db.refresh(claim)
    return ClaimResponse.model_validate(claim)

