from fastapi import APIRouter, Depends

from app.core.security import Actor, get_current_actor
from app.schemas.auth import ActorResponse

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=ActorResponse)
def read_current_actor(actor: Actor = Depends(get_current_actor)) -> ActorResponse:
    return ActorResponse(id=actor.id, name=actor.name, role=actor.role)
