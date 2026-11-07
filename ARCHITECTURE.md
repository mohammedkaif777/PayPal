# Architecture

## 1. Goals and constraints

- Demonstrate an end-to-end parametric climate micro-insurance flow.
- Keep AI inference, evidence verification, policy evaluation, financial
  authorization, and payment execution strictly separated.
- Remain runnable on a developer laptop with no Docker and no live credentials.
- Prefer a modular monolith over distributed infrastructure.

Constraints adopted from the project owner:

- **No Docker.** Local Python venv, SQLite by default.
- **No git operations.**
- PostgreSQL is optional via `DATABASE_URL`; there is no local PostgreSQL server.
- Gemini and PayPal credentials may be absent, so deterministic mocks are default.
- Dependency installation is deferred to the project owner after development.

## 2. Deployment topology

```
Developer machine
├── FastAPI process (uvicorn, port 8000)
│   ├── modular monolith services
│   ├── SQLite database file (data/pcmsc.db)
│   └── local evidence store (data/evidence)
├── Streamlit process (port 8501) -> calls FastAPI over HTTP
└── Optional external services
    ├── Gemini API (AI_PROVIDER=gemini)
    └── PayPal Payouts Sandbox (PAYMENT_PROVIDER=paypal)
```

No message broker, cache, or vector database is used. The simulator advances
telemetry deterministically from seeded scenarios.

## 3. Trust boundaries and data flow

```
Telemetry / weather / port ──► Monitoring ───────────────► FACTS
BoL PDF / images ──► AI extraction ──► OBSERVATIONS ──► Verification ──► FACTS
FACTS + Policy + Fraud signals ──► CLAIMS ENGINE ──► Settlement + one-time authorization
Settlement + authorization ──► PAYMENT ENGINE ──► PayPal Sandbox / Mock
Every transition ──► append-only hash-chained AUDIT LOG
```

Hard boundaries:

1. AI providers return observations with confidence only. They cannot reference
   claims, settlements, or payments.
2. The claims engine is a pure function of policy terms, verified facts, and
   fraud signals. Identical inputs produce an identical decision hash.
3. Only the claims engine can produce `APPROVED`.
4. Only a `Settlement` with a valid, single-use authorization nonce can be paid.
5. A payment adapter never receives raw telemetry or model output.

## 4. Module responsibilities

| Module | Responsibility | Status |
|---|---|---|
| `core` | Settings, JSON logging, error envelope, API-key auth, request IDs | M0 complete |
| `db` | Engine, session, declarative base, init | M0 complete |
| `models` | ORM entities | M0 partial (api_keys, audit_logs, idempotency_keys) |
| `services.audit` | Hash-chained append-only audit log | M0 complete |
| `services.idempotency` | Idempotency key lifecycle | M0 complete |
| `shipment_policy` | Shipments, policies, lifecycle | M1 pending |
| `monitoring` | Telemetry validation and derived violations | M2 pending |
| `evidence` | Secure upload, hashing, PDF parsing, image QC | M3 pending |
| `ai` | Provider interface, Gemini adapter, mock adapter | M3 pending |
| `verification` | Document/image/telemetry cross-checks | M4 pending |
| `fraud` | Rules, statistical anomalies, explanations | M4 pending |
| `claims` | Deterministic eligibility, payout formula, trace | M5 pending |
| `settlement` | Currency-safe split and authorization nonce | M5 pending |
| `payments` | Mock and PayPal Sandbox adapters, retries | M6 pending |
| `dashboard` | Streamlit + AG Grid UI | M7 pending |
| `simulation` | Repeatable Scenario A/B | M8 pending |

## 5. Database design

### Implemented in M0

| Table | Key fields |
|---|---|
| `api_keys` | `name`, `key_prefix`, `key_hash`, `role`, `active` |
| `audit_logs` | `actor`, `action`, `entity_type`, `entity_id`, `request_id`, `before_json`, `after_json`, `prev_hash`, `hash` |
| `idempotency_keys` | `scope`, `key`, `request_hash`, `status_code`, `response_json`; unique `(scope, key)` |

### Planned domain tables

| Table | Key fields |
|---|---|
| `parties` | role (supplier/logistics), name, sandbox payout email |
| `shipments` | external ref, commodity, route, mode, declared value, times, status |
| `policies` | coverage, premium, thresholds, coverage window, split rules, version |
| `telemetry_readings` | shipment, device, timestamp, temperature, humidity, lat/lon, source |
| `port_delays` | shipment, port, delay hours, reported_at |
| `evidence_documents` | type, sha256, path, mime, size |
| `evidence_extractions` | provider, model, prompt version, fields, confidence, raw response |
| `verification_results` | check code, passed, details |
| `fraud_signals` | rule code, severity, score, explanation, evidence refs |
| `claims` | occurrence key, amounts, status, decision trace, input/decision hashes |
| `settlements` | claim, total, currency, allocation, authorization nonce/hash |
| `settlement_lines` | party, role, amount |
| `payouts` | settlement (unique), idempotency key (unique), external id, status, attempts |
| `payout_attempts` | attempt number, request/response summary, success |

## 6. State machines

- **Shipment:** `REGISTERED -> IN_TRANSIT -> DELIVERED -> CLOSED`, `CANCELLED`
- **Policy:** `DRAFT -> ACTIVE -> TRIGGERED -> SETTLED`, `EXPIRED`, `CANCELLED`
- **Claim:** `SUBMITTED -> EVALUATING -> APPROVED | REJECTED | REVIEW_REQUIRED`;
  `APPROVED -> SETTLED -> PAYOUT_PENDING -> PAID`; `PAYOUT_FAILED`.
  Only a human reviewer can resolve `REVIEW_REQUIRED`.
- **Payout:** `PENDING -> SENT -> SUCCEEDED | FAILED`; `FAILED -> RETRYING -> SENT`

## 7. Idempotency and financial integrity

- Claim occurrence is unique per `(policy_id, trigger_code, occurrence_key)`.
- One settlement per claim; one payout per settlement (`UNIQUE(settlement_id)`).
- `UNIQUE(idempotency_key)` on claims and payouts.
- PayPal `PayPal-Request-Id` equals the payout idempotency key.
- Payment authorization is a single-use nonce bound to settlement id, amount,
  currency, and decision hash.
- Money is handled with `Decimal` and stored as `NUMERIC(18,2)`; allocation uses
  largest-remainder rounding so the sum exactly equals the settlement total.
- Failed payouts retry with the same idempotency key; a second external payout
  cannot be created.

## 8. Audit and security

- API keys are stored as SHA-256 hashes with a display prefix only.
- Roles: `admin`, `operator`, `reviewer`, `read_only`.
- Startup refuses demo keys in production.
- Structured JSON logs include a request ID; secrets are never logged.
- Audit log is append-only and hash-chained (`prev_hash -> hash`). It is
  tamper-evident for demonstration; production would add external anchoring.
- Evidence uploads will be size/type/magic-byte validated, path-sanitized, and
  stored content-addressed by SHA-256.
- All timestamps are UTC-aware.

## 9. Architecture decisions

| Decision | Rationale |
|---|---|
| Modular monolith | Fast to build, simple to operate, keeps boundaries explicit |
| SQLite default, Postgres optional | No Docker and no local PostgreSQL server |
| Adapter interfaces for AI/payments | Deterministic mocks enable offline tests and demos |
| Deterministic claims engine | Financial authorization must be reproducible and explainable |
| AI observations only | Prevents an LLM from ever authorizing money |
| Hash-chained audit log | Tamper-evident history without extra infrastructure |
| Local content-addressed evidence | Simple, verifiable, no object storage dependency |

## 10. Known limitations

- SQLite has no row-level locking; rely on unique constraints and a single API
  worker for the demo.
- Live Gemini and PayPal paths remain unverified until credentials are supplied.
- Audit chaining is serialized per process; concurrent writers would need a
  database-level sequence or a Postgres advisory lock.
- The simulator is synthetic and does not represent real IoT or weather feeds.
