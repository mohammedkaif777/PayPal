# Testing

## 1. Principles

- Verify behavior, not implementation details.
- Every financial rule and guardrail needs a deterministic test.
- Tests must run offline with the mock AI and payment providers.
- Never report a test as passing without executing it.
- Scenario tests must be repeatable from a clean database.

## 2. Test layers

| Layer | Scope | Status |
|---|---|---|
| Unit | Pure functions: splits, thresholds, fraud rules, decision hash | Planned M2-M5 |
| Service | Audit chain, idempotency, state machine transitions | M0 partial |
| API integration | FastAPI routes with a temporary SQLite database | M0 partial |
| Adapter contract | Mock and live adapters share the same interface behavior | Planned M3/M6 |
| End-to-end scenario | Scenario A valid claim and Scenario B fraud | Planned M8 |
| Security | Auth, role enforcement, upload validation, redaction | M0 partial |

## 3. Test environment

- Temporary file-backed SQLite database created per test session.
- Tables dropped and recreated before each test for isolation.
- Demo API keys seeded programmatically.
- `AI_PROVIDER=mock` and `PAYMENT_PROVIDER=mock` forced by the test config.
- No network access is required.
- FastAPI `TestClient` with lifespan enabled.

## 4. Current results (Milestone M0)

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Actual output:

```
............                                                             [100%]
12 passed, 1 warning in 0.73s
```

Warning: `StarletteDeprecationWarning` from FastAPI's `TestClient` regarding
`httpx`; it does not affect functionality.

### Implemented tests

| File | Tests | What is verified |
|---|---|---|
| `tests/test_health.py` | 3 | `/health`, `/ready`, request ID propagation |
| `tests/test_auth.py` | 4 | Missing/invalid key, actor identity, role enforcement |
| `tests/test_audit.py` | 2 | Genesis link, hash chaining, audit API ordering |
| `tests/test_idempotency.py` | 3 | Create, replay, conflict, in-progress handling |

## 5. Additional M0 verification

- `python -m alembic upgrade head` applied `0001_initial` and reported head.
- `python -m app.seed` initialized the database and seeded four roles.
- Live Uvicorn smoke test:
  - `GET /health` -> `{"status":"ok","app":"PCMSC","version":"0.1.0","env":"development"}`
  - `GET /ready` -> `{"status":"ready"}`
  - `GET /api/v1/auth/me` with the admin key -> `{"id":1,"name":"admin","role":"admin"}`

## 6. Planned test matrix

### M1 — Shipments and policies

- Create shipment and policy; activate policy.
- Reject invalid lifecycle transitions.
- Unauthorized roles receive 401/403.
- Idempotent creation returns the original resource.

### M2 — Telemetry and monitoring

- Temperature above/below threshold produces a violation fact.
- Humidity, geofence, and port-delay violations.
- Out-of-order and duplicate timestamps are handled deterministically.
- Seeded simulator produces stable values across runs.

### M3 — Evidence and AI

- PDF text and page rendering with a generated fixture.
- Reject oversize, wrong MIME, encrypted PDF, and path traversal names.
- Mock AI extraction is deterministic and schema-valid.
- Gemini adapter validated with a recorded fixture when a key is available.

### M4 — Fraud

- Scenario B manipulation triggers hard-block signals.
- Impossible temperature delta, stuck sensor, missing data, geofence jump.
- Document/telemetry timestamp mismatch.
- Every signal carries an explanation and evidence reference.

### M5 — Claims and settlement

- Policy inactive, outside window, or trigger unmet -> rejected.
- Same facts + policy -> identical decision hash.
- Split allocation sums exactly to the settlement total.
- Duplicate claim occurrence is blocked.
- Fraud hard-block prevents approval; high risk routes to review.

### M6 — Payments

- Mock payout success path.
- Duplicate payout attempt cannot create a second external payment.
- Retry reuses the same idempotency key.
- Failed payout transitions to `PAYOUT_FAILED` and can be retried safely.
- Unauthorized settlement cannot be paid.

### M7 — Dashboard

- API client smoke tests.
- Grid data loads for shipments, claims, fraud, payouts, audit.
- Scenario runner triggers A and B.

### M8 — End-to-end

- Scenario A completes through split payout.
- Scenario B ends with no payout and a fraud alert.
- Full suite green from a clean database.
- Documentation matches verified behavior.

## 7. Coverage

Coverage is measured with `pytest-cov` once domain modules exist. The target is
meaningful coverage of financial and security paths rather than a vanity number.
Command:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

## 8. Test data policy

- All PDFs and images are generated locally as fixtures.
- Telemetry is synthetic and seeded.
- No real shipment, personal, or payment data is used.
- Sandbox/mock payment identifiers only.

## 9. Known gaps

- No live Gemini or PayPal tests until credentials are provided.
- No concurrency stress test yet; SQLite is single-writer.
- Audit chain is tested within one process only.
