# PCMSC — Parametric Climate Micro-Insurance for Supply Chains

Status: **Milestone M0 complete** (foundation). Domain modules are pending.

A production-inspired fintech application for the PayPal AI Hackathon: parametric
climate micro-insurance for agricultural supply chains and cross-border logistics.
The platform is built as a secure modular monolith with deterministic claim
authorization, explainable fraud detection, and sandbox-only payments.

## Target capabilities

- Register shipments and create climate-linked insurance policies.
- Ingest temperature, humidity, location, weather, and port-delay telemetry.
- Detect threshold, geofence, and delay violations deterministically.
- Extract Bill of Lading data and analyze container/satellite images with Gemini.
- Cross-verify evidence, detect spoofed sensors and inconsistent documents.
- Evaluate claims with a deterministic, explainable claims engine.
- Split settlements between suppliers and logistics providers.
- Execute PayPal Payouts Sandbox or mock payouts with idempotency guarantees.
- Display risks, claims, evidence, fraud alerts, and payments in Streamlit + AG Grid.

## Safety guarantees

- AI never approves claims or moves money. It only produces typed observations.
- Only the deterministic claims engine can authorize a settlement.
- Payments can only execute against an authorized settlement.
- Duplicate claims and payouts are blocked by unique constraints and idempotency keys.
- Sandbox or mock payments only. No real transfers.
- Secrets are read from environment variables; API keys are stored hashed.
- Every state change is written to an append-only, hash-chained audit log.

## Stack

FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic · SQLite (PostgreSQL optional) ·
Gemini via `google-genai` · PyMuPDF · OpenCV · scikit-learn · Streamlit + AG Grid ·
PayPal Payouts Sandbox · pytest. **No Docker.**

## Repository layout

```
app/
  main.py                 FastAPI app factory, health/ready, middleware
  seed.py                 Database initialization + API key seeding
  core/                   Config, logging, errors, security (API keys/roles)
  db/                     SQLAlchemy base, engine/session, init
  models/                 ORM models (M0: api_keys, audit_logs, idempotency_keys)
  schemas/                Pydantic response models
  api/v1/                 Versioned routers
  services/               Audit, idempotency, bootstrap
  ai/ vision/ payments/    Reserved for M3 and M6
dashboard/                Streamlit app (M7)
tests/                    pytest suite
alembic/                  Migration environment + 0001_initial
data/                     Runtime SQLite DB and evidence store (ignored)
```

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.seed
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

The dashboard will be added in M7:

```powershell
streamlit run dashboard/app.py --server.port 8501
```

## Configuration

All settings are read from environment variables or `.env`. See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | `development`, `test`, `production` |
| `DATABASE_URL` | `sqlite:///./data/pcmsc.db` | SQLite by default; PostgreSQL supported |
| `LOG_LEVEL` | `INFO` | Structured JSON log level |
| `CORS_ORIGINS` | `http://localhost:8501` | Comma-separated dashboard origins |
| `ADMIN_API_KEY` | demo value | Admin role key |
| `OPERATOR_API_KEY` | demo value | Operator role key |
| `REVIEWER_API_KEY` | demo value | Reviewer role key |
| `READONLY_API_KEY` | demo value | Read-only role key |
| `AI_PROVIDER` | `mock` | `mock` or `gemini` |
| `GEMINI_API_KEY` | empty | Required for `AI_PROVIDER=gemini` |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `PAYMENT_PROVIDER` | `mock` | `mock` or `paypal` |
| `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` | empty | Required for `PAYMENT_PROVIDER=paypal` |
| `PAYPAL_BASE_URL` | sandbox URL | PayPal sandbox base URL |

The default demo API keys are for local development only. Startup fails in
`APP_ENV=production` if demo keys or incomplete live-provider credentials are used.

## Implemented API (M0)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | public | Liveness |
| GET | `/ready` | public | Database readiness |
| GET | `/api/v1/auth/me` | any role | Current actor |
| GET | `/api/v1/audit` | admin | Recent audit entries (hash-chained) |

Send the API key in the `X-API-Key` header. Example:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/audit -Headers @{ "X-API-Key" = "demo-admin-key" }
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Current result: **12 passed** (M0). See `TESTING.md` for the full strategy.

## Demo scenarios (planned, M8)

- **Scenario A — Valid claim:** shipment → policy → heat breach → evidence →
  verification → fraud checks → deterministic evaluation → settlement →
  split PayPal sandbox/mock payout → dashboard update.
- **Scenario B — Fraudulent claim:** manipulated sensors → anomaly detection →
  claim blocked or flagged → no payout.

## Documentation

- `ARCHITECTURE.md` — system design, trust boundaries, data flow, database plan.
- `TESTING.md` — test strategy, current results, planned matrix.
- `DEVELOPMENT_LOG.md` — completed and verified work only.
- `PENDING_DEVELOPMENT.md` — active tracker, priorities, blockers, next tasks.

## Disclaimer

Educational hackathon project using simulated telemetry, mock AI providers by
default, and sandbox/mock payments. Not a real insurance product.
