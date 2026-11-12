from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.party import Party
from app.schemas.party import PartyCreate
from app.services.audit import AuditService


class PartyService:
    @staticmethod
    def create(db: Session, data: PartyCreate, *, actor: str) -> Party:
        party = Party(
            name=data.name,
            role=data.role,
            payout_email=data.payout_email,
            country_code=data.country_code,
        )
        db.add(party)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="create",
            entity_type="party",
            entity_id=str(party.id),
            after={
                "name": party.name,
                "role": party.role,
                "payout_email": party.payout_email,
            },
        )
        return party

    @staticmethod
    def get(db: Session, party_id: int) -> Party:
        party = db.get(Party, party_id)
        if party is None:
            raise AppError(
                f"Party {party_id} not found",
                code="not_found",
                status_code=404,
            )
        return party

    @staticmethod
    def list_all(db: Session, *, role: str | None = None) -> list[Party]:
        stmt = select(Party).order_by(Party.id.asc())
        if role is not None:
            stmt = stmt.where(Party.role == role)
        return list(db.scalars(stmt).all())

