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
| Unit | Pure functions: splits, thresholds, fraud rules, decision hash, simulator | Implemented & 7/7 executed |
| Service | Audit chain, idempotency, state machine transitions, payout retry | Implemented & verified synchronously |
| API integration | FastAPI routes with a temporary SQLite database (35 `TestClient` tests) | Implemented; pending local run outside sandbox |
| Adapter contract | Mock and live adapters (`AIProvider`, `PaymentAdapter`) | Mock verified; live adapters require credentials |
| End-to-end scenario | Scenario A valid claim and Scenario B fraud | Verified synchronously; API tests pending local run |
| Security | Auth, role enforcement, upload validation, nonce, audit | Implemented across M0/M3/M6/M8 test suites |

## 3. Current results

- `python -m compileall -q app dashboard tests alembic` -> **passed (0 errors)**
- `python -m pytest --collect-only -q` -> **42 tests collected**
- Non-`TestClient` unit test subset (`python -m pytest -v -k "test_seeded_simulator_is_deterministic or test_identical_inputs_identical_decision_hash or test_inactive_policy_and_unmet_trigger_rejected or test_hard_block_rejects_and_review_routes or test_allocate_split_sums_exactly or test_pdf_fixture_is_not_encrypted or test_dashboard_api_client_instantiation"`): **7 passed, 35 deselected**.
- Synchronous end-to-end verification (`ScenarioService.run` for A & B, 18 SQLite tables, payout retry with `MockPaymentProvider(force_fail=True)` -> `retry_payout`): **passed**.
- Note: Full `pytest` execution (`TestClient` / `anyio` blocking portal) hangs inside the Windows sandbox due to `asyncio.run` socketpair restrictions. Run the full suite locally outside the sandbox:

```powershell
python -m pytest -q
```

## 4. Test inventory (42 collected tests)

| File | Tests | Scope |
|---|---|---|
| `tests/test_health.py` | 3 | `/health`, `/ready`, request ID propagation |
| `tests/test_auth.py` | 4 | Missing/invalid key, actor identity, role enforcement |
| `tests/test_audit.py` | 2 | Genesis link, hash chaining, audit API ordering |
| `tests/test_idempotency.py` | 3 | Create, replay, conflict, in-progress handling |
| `tests/test_m1_shipments_policies.py` | 5 | Parties, shipments, policies, lifecycles, RBAC, idempotency |
| `tests/test_m2_monitoring.py` | 4 | Threshold/geofence/delay violations, validation, deduplication, seeded simulator |
| `tests/test_m3_evidence.py` | 5 | PDF text extraction, encrypted PDF & path traversal rejection, image QC & duplicate hash |
| `tests/test_m4_fraud.py` | 2 | Scenario B sensor manipulation hard-blocks, document timestamp mismatch |
| `tests/test_m5_claims_settlement.py` | 5 | Pure decision hashing, fraud gates, largest-remainder split, duplicate occurrence block |
| `tests/test_m6_payments.py` | 3 | Mock payout, duplicate payout block, invalid nonce rejection, safe retry |
| `tests/test_m7_dashboard.py` | 1 | Dashboard API client instantiation |
| `tests/test_m8_e2e_security.py` | 2 | Scenario A & Scenario B E2E API assertions |
| `tests/test_m8_scenarios.py` | 3 | Scenario A & Scenario B E2E + unauthenticated domain route rejection |

## 5. Known gaps

- 35 `TestClient` API tests require local execution outside the sandboxed `asyncio` environment.
- No live Gemini or PayPal tests until credentials are provided.
- `alembic upgrade head` for `0002_domain_tables` pending local `alembic` install.
