from fastapi import APIRouter

from app.api.v1 import (
    audit,
    auth,
    claims,
    evidence,
    fraud,
    monitoring,
    parties,
    payouts,
    policies,
    scenarios,
    settlements,
    shipments,
    simulator,
    telemetry,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(audit.router)
api_router.include_router(parties.router)
api_router.include_router(shipments.router)
api_router.include_router(policies.router)
api_router.include_router(telemetry.router)
api_router.include_router(monitoring.router)
api_router.include_router(simulator.router)
api_router.include_router(evidence.router)
api_router.include_router(fraud.router)
api_router.include_router(claims.router)
api_router.include_router(settlements.router)
api_router.include_router(payouts.router)
api_router.include_router(scenarios.router)
