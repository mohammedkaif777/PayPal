from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.party import PartyCreate, PartyResponse
from app.services.party import PartyService

router = APIRouter(prefix="/parties", tags=["parties"])


@router.post("", response_model=PartyResponse, status_code=status.HTTP_201_CREATED)
def create_party(
    payload: PartyCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> PartyResponse:
    party = PartyService.create(db, payload, actor=actor.name)
    db.commit()
    db.refresh(party)
    return PartyResponse.model_validate(party)


@router.get("", response_model=list[PartyResponse])
def list_parties(
    role: str | None = Query(default=None),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[PartyResponse]:
    return [PartyResponse.model_validate(p) for p in PartyService.list_all(db, role=role)]


@router.get("/{party_id}", response_model=PartyResponse)
def get_party(
    party_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> PartyResponse:
    return PartyResponse.model_validate(PartyService.get(db, party_id))
