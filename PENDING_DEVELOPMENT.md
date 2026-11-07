# Pending Development Tracker

## Current status

- **Milestone:** M0 (foundation) COMPLETED and verified.
- **Next milestone:** M1 (shipments and policies) NOT_STARTED.
- **Approval:** awaiting explicit YES to begin M1.
- **Constraints:** no Docker, no git operations.
- **Dependencies:** installation deferred to the project owner. No installs are
  run by development after M0 bootstrap.
- **Environment:** SQLite default; Gemini and PayPal use mock providers.

## Completed tasks (historical, preserved)

| ID | Task | Priority | Status | Verified by |
|---|---|---|---|---|
| PCMS-001 | Project scaffold, requirements, `.env.example` | P0 | COMPLETED | Files present; app imports |
| PCMS-002 | Settings, JSON logging, error envelope | P0 | COMPLETED | Tests; live smoke |
| PCMS-003 | DB engine, base, session, init, SQLite pragmas | P0 | COMPLETED | Tests; seed; smoke |
| PCMS-004 | API-key auth, SHA-256 hashing, role enforcement | P0 | COMPLETED | `test_auth.py` |
| PCMS-005 | Append-only hash-chained audit log | P0 | COMPLETED | `test_audit.py` |
| PCMS-006 | Idempotency model and service | P0 | COMPLETED | `test_idempotency.py` |
| PCMS-007 | Health/readiness, request ID middleware | P0 | COMPLETED | `test_health.py` |
| PCMS-008 | Alembic environment and `0001_initial` migration | P0 | COMPLETED | `alembic upgrade head` |
| PCMS-009 | M0 pytest suite | P0 | COMPLETED | 12 passed |

## Pending tasks

### M1 — Shipment and policy management

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-101 | `parties`, `shipments` models, schemas, APIs | P0 | NOT_STARTED | PCMS-003/004 | Create/list/get shipment; validation; audit entry |
| PCMS-102 | `policies` model, thresholds, lifecycle, APIs | P0 | NOT_STARTED | PCMS-101 | Draft/activate/cancel; invalid transitions rejected |
| PCMS-103 | M1 tests | P0 | NOT_STARTED | PCMS-101/102 | Lifecycle, auth, validation tests green |

### M2 — Climate monitoring

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-201 | `telemetry_readings`, `port_delays` models + ingest API | P0 | NOT_STARTED | PCMS-101 | Bulk ingest; reject invalid ranges/timestamps |
| PCMS-202 | Monitoring engine: temp, humidity, geofence, delay | P0 | NOT_STARTED | PCMS-201 | Derived violation facts with provenance |
| PCMS-203 | Deterministic seeded simulator | P0 | NOT_STARTED | PCMS-201 | Same seed -> same series |
| PCMS-204 | Monitoring tests | P0 | NOT_STARTED | PCMS-202/203 | Threshold and edge-case tests green |

### M3 — Evidence intelligence

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-301 | Secure evidence upload, SHA-256, content-addressed store | P0 | NOT_STARTED | PCMS-101 | Bad type/size/encrypted PDF rejected; path safe |
| PCMS-302 | PyMuPDF text + page rendering | P0 | NOT_STARTED | PCMS-301 | Text and images extracted from fixture PDF |
| PCMS-303 | `AIProvider` interface + deterministic mock | P0 | NOT_STARTED | PCMS-302 | Schema-valid observations; no claim access |
| PCMS-304 | Gemini adapter, JSON schema, prompt versioning | P1 | NOT_STARTED | PCMS-303 | Validated extraction when key supplied |
| PCMS-305 | OpenCV image QC and duplicate detection | P1 | NOT_STARTED | PCMS-301 | Blur, EXIF, perceptual hash checks |
| PCMS-306 | Evidence tests | P0 | NOT_STARTED | PCMS-301..305 | Fixture-based tests green |

### M4 — Fraud detection

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-401 | Evidence cross-verification facts | P0 | NOT_STARTED | PCMS-306 | Shipment ID and timestamp checks recorded |
| PCMS-402 | Rule-based fraud engine with explanations | P0 | NOT_STARTED | PCMS-202/401 | Hard-block and review tiers |
| PCMS-403 | Statistical anomaly detection | P1 | NOT_STARTED | PCMS-202 | Deterministic z-score / IsolationForest score |
| PCMS-404 | Fraud tests including Scenario B | P0 | NOT_STARTED | PCMS-402/403 | Manipulated sensors detected and explained |

### M5 — Claims and settlement

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-501 | Claim model, submission, occurrence uniqueness, idempotency | P0 | NOT_STARTED | PCMS-102/402 | Duplicate occurrence blocked |
| PCMS-502 | Deterministic claims engine + rule trace + hashes | P0 | NOT_STARTED | PCMS-501 | Identical inputs -> identical decision hash |
| PCMS-503 | Settlement split + single-use authorization nonce | P0 | NOT_STARTED | PCMS-502 | Split sums exactly; nonce bound to settlement |
| PCMS-504 | Claims/settlement tests | P0 | NOT_STARTED | PCMS-502/503 | Eligibility, fraud gate, rounding tests green |

### M6 — Payment engine

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-601 | Payment adapter interface + mock provider | P0 | NOT_STARTED | PCMS-503 | Pay only authorized settlement |
| PCMS-602 | PayPal Payouts Sandbox adapter | P1 | NOT_STARTED | PCMS-601 | Request ID = idempotency key; no live money |
| PCMS-603 | Retry and failure handling | P0 | NOT_STARTED | PCMS-601 | Failed payout retries safely; no duplicates |
| PCMS-604 | Payment tests | P0 | NOT_STARTED | PCMS-601..603 | Duplicate payout prevention proven |

### M7 — Dashboard

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-701 | API client and dashboard shell | P1 | NOT_STARTED | PCMS-601 | Connects with API key; health indicator |
| PCMS-702 | AG Grid shipment/policy/claim/fraud/payout views | P1 | NOT_STARTED | PCMS-701 | Tables load real API data |
| PCMS-703 | Claim trace, evidence, and audit views | P1 | NOT_STARTED | PCMS-702 | Explainability visible |
| PCMS-704 | Scenario runner UI | P1 | NOT_STARTED | PCMS-701 | Buttons trigger A and B |

### M8 — End-to-end and handoff

| ID | Task | Priority | Status | Depends on | Acceptance criteria |
|---|---|---|---|---|---|
| PCMS-801 | Scenario A end-to-end test | P0 | NOT_STARTED | PCMS-604 | Valid claim pays split exactly once |
| PCMS-802 | Scenario B end-to-end test | P0 | NOT_STARTED | PCMS-604 | Fraud claim produces no payout |
| PCMS-803 | Security pass | P0 | NOT_STARTED | all | Auth, uploads, secrets, audit verified |
| PCMS-804 | Documentation and demo script finalization | P0 | NOT_STARTED | PCMS-801..803 | Docs match verified behavior |

## Blockers

1. Awaiting explicit approval to start M1.
2. Gemini and PayPal credentials are absent. Not blocking: mock providers are the
   default and all tests are offline.
3. Dependency installation is deferred to the project owner after development.

## Technical debt and known limitations

- SQLite has no row-level locking; idempotency relies on unique constraints and a
  single API worker.
- Audit hash chaining is verified within one process only.
- Audit listing supports a limit but no cursor pagination.
- Demo API keys are stored in `.env`; production validation exists but secrets
  management is not implemented.
- No rate limiting yet.
- Live Gemini and PayPal code paths remain unverified without credentials.
- FastAPI 0.162/Starlette 1.10 nest included routers; route introspection differs
  from older versions.
- The Streamlit dashboard does not exist yet.

## Potential improvements by module

### Shipment and policy
- Policy versioning and premium pricing model.
- Multi-leg shipments and carrier-specific terms.

### Monitoring
- Weather and port provider adapters with provenance.
- Alerting on approaching thresholds.

### Evidence and AI
- Barcode/QR verification and stamped-signature OCR.
- Satellite image change detection.
- Prompt evaluation harness and recorded fixtures.

### Fraud
- Calibration dataset and drift monitoring.
- Reviewer feedback loop with labeled outcomes.

### Claims and settlement
- Multi-currency support and FX snapshots.
- Appeal workflow for rejected claims.

### Payments
- PayPal webhook reconciliation.
- Postgres advisory locks for concurrent payout safety.

### Platform
- JWT/OAuth, rate limiting, metrics, tracing.
- External audit anchoring and retention policy.
- Pagination and filtering across list endpoints.

## Next three recommended tasks

1. **PCMS-101** — Parties and shipments models, schemas, APIs.
2. **PCMS-102** — Policies, thresholds, lifecycle, and APIs.
3. **PCMS-103** — M1 tests for lifecycle, auth, and validation.

## Definition of done for each milestone

- Code is typed, validated, and error-handled.
- Tests are written and executed; actual results recorded.
- `DEVELOPMENT_LOG.md` updated with verified work.
- `PENDING_DEVELOPMENT.md` updated with status and blockers.
- Handoff report presented and approval requested before the next milestone.
