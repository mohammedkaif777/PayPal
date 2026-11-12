from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.settlement import (
    SettlementCreateRequest,
    SettlementLineResponse,
    SettlementResponse,
)
from app.services.settlement import SettlementService

router = APIRouter(prefix="/settlements", tags=["settlements"])


def _to_response(settlement, lines) -> SettlementResponse:
    resp = SettlementResponse.model_validate(settlement)
    resp.lines = [SettlementLineResponse.model_validate(line) for line in lines]
    return resp


@router.post("", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
def create_settlement(
    payload: SettlementCreateRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> SettlementResponse:
    settlement, lines = SettlementService.create_settlement(
        db, payload.claim_id, actor=actor.name
    )
    db.commit()
    db.refresh(settlement)
    return _to_response(settlement, lines)


@router.get("", response_model=list[SettlementResponse])
def list_settlements(
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[SettlementResponse]:
    results = []
    for settlement in SettlementService.list_all(db):
        _, lines = SettlementService.get(db, settlement.id)
        results.append(_to_response(settlement, lines))
    return results


@router.get("/claim/{claim_id}", response_model=SettlementResponse)
def get_settlement_by_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> SettlementResponse:
    settlement, lines = SettlementService.get_by_claim(db, claim_id)
    return _to_response(settlement, lines)


@router.get("/{settlement_id}", response_model=SettlementResponse)
def get_settlement(
    settlement_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> SettlementResponse:
    settlement, lines = SettlementService.get(db, settlement_id)
    return _to_response(settlement, lines)
