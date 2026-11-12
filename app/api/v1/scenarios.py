from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.scenario import ScenarioRunRequest, ScenarioRunResponse
from app.services.scenarios import ScenarioService

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/run", response_model=ScenarioRunResponse)
def run_scenario(
    payload: ScenarioRunRequest,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> ScenarioRunResponse:
    result = ScenarioService.run(
        db, scenario=payload.scenario, seed=payload.seed, actor=actor.name
    )
    db.commit()
    return ScenarioRunResponse.model_validate(result)
