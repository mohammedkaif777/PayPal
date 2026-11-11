# PCMSC — Parametric Climate Micro-Insurance for Supply Chains

Status: **Milestones M0–M8 implemented** (local `pytest` full HTTP verification & dependency install pending owner run outside sandbox).

A production-inspired fintech application for the PayPal AI Hackathon: parametric
climate micro-insurance for agricultural supply chains and cross-border logistics.
The platform is built as a secure modular monolith with deterministic claim
authorization, explainable fraud detection, and sandbox-only payments.

## Capabilities

- Register parties and shipments, and manage climate-linked insurance policy lifecycles (`M1`).
- Ingest temperature, humidity, location, and port-delay telemetry with deterministic seeded simulation (`M2`).
- Detect threshold, geofence, and port-delay violations with reading provenance (`M2`).
- Securely upload Bills of Lading & container photos (magic-byte check, encrypted PDF rejection, SHA-256 content-addressed store), extract PDF text, run image QC (blur, EXIF, perceptual hash), and extract structured observations via Mock/Gemini AI (`M3`).
- Cross-verify evidence and detect spoofed sensors, impossible temperature deltas, geofence jumps, and statistical anomalies (`M4`).
- Evaluate claims with a pure, deterministic, hash-verifiable claims engine (`M5`).
- Split settlements using largest-remainder cent rounding with single-use authorization nonces (`M5`).
- Execute Mock or PayPal Payouts Sandbox payouts with strict idempotency and safe retry (`M6`).
- Inspect shipments, policies, claims, decision traces, fraud signals, payouts, audit logs, and run Scenarios A & B in Streamlit + AG Grid (`M7`–`M8`).

## Safety guarantees

- AI never approves claims or moves money. It only produces typed observations (`FORBIDDEN_OBSERVATION_KEYS` enforced).
- Only the deterministic claims engine (or a `reviewer`/`admin` resolving `REVIEW_REQUIRED`) can authorize a settlement.
- Payments can only execute against an authorized settlement with a single-use nonce.
- Duplicate claims and payouts are blocked by unique constraints and idempotency keys.
- Sandbox or mock payments only. No real transfers.
- Every state change is written to an append-only, hash-chained audit log.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.seed
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

Launch the Streamlit dashboard:

```powershell
streamlit run dashboard/app.py --server.port 8501
```

## Implemented API v1 Endpoints

| Area | Method | Path | Auth |
|---|---|---|---|
| System | GET | `/health`, `/ready` | public |
| Auth & Audit | GET | `/api/v1/auth/me`, `/api/v1/audit` | any role / admin |
| Parties | POST, GET | `/api/v1/parties`, `/api/v1/parties/{id}` | operator+ / read |
| Shipments | POST, GET | `/api/v1/shipments`, `/api/v1/shipments/{id}`, `/api/v1/shipments/{id}/transition` | operator+ / read |
| Policies | POST, GET | `/api/v1/policies`, `/api/v1/policies/{id}`, `/{id}/activate`, `/{id}/cancel`, `/{id}/expire` | operator+ / read |
| Telemetry | POST, GET | `/api/v1/telemetry/ingest`, `/api/v1/telemetry/shipment/{id}`, `/api/v1/telemetry/port-delays` | operator+ / read |
| Monitoring | POST, GET | `/api/v1/monitoring/evaluate`, `/api/v1/monitoring/violations/{shipment_id}` | operator+ / read |
| Simulator | POST | `/api/v1/simulator/run` | operator+ |
| Evidence | POST, GET | `/api/v1/evidence/upload`, `/shipment/{id}`, `/{id}`, `/{id}/extract`, `/{id}/extractions`, `/{id}/qc` | operator+ / read |
| Fraud | POST, GET | `/api/v1/fraud/evaluate`, `/api/v1/fraud/signals/{shipment_id}`, `/api/v1/fraud/verifications/{shipment_id}` | reviewer+/read |
| Claims | POST, GET | `/api/v1/claims`, `/{id}`, `/{id}/evaluate`, `/{id}/review` | operator+/reviewer+ |
| Settlements | POST, GET | `/api/v1/settlements`, `/api/v1/settlements/claim/{claim_id}`, `/{id}` | operator+ / read |
| Payouts | POST, GET | `/api/v1/payouts`, `/{id}`, `/{id}/retry` | operator+ / read |
| Scenarios | POST | `/api/v1/scenarios/run` | operator+ |

## Tests

```powershell
python -m pytest -q
```

See [TESTING.md](file:///c:/Users/HARSH/PayPal/TESTING.md) and [PENDING_DEVELOPMENT.md](file:///c:/Users/HARSH/PayPal/PENDING_DEVELOPMENT.md) for verified sandbox checks and remaining owner-side runs.
