# Development Log

This file records completed and verified work only. Planned work belongs in
`PENDING_DEVELOPMENT.md`.

## 2026-11-07 — Stage 1: Repository Analysis (Planning)

- Repository root was empty (0 files, no `.git`). Greenfield project.
- Environment: Windows, PowerShell 5.1, Python 3.11.9, pip 24.0, git 2.51.1.
- Decision: SQLite default, PostgreSQL optional via `DATABASE_URL`.
- Decision: AI and payments behind adapter interfaces with deterministic mocks.
- Decision: deterministic claims engine is the sole financial authorizer.

## 2026-11-07 — Stage 2: Architecture and Plan Approved

- Owner approved development and instructed: no Docker, no git operations.
- Dependency installation deferred to the owner upon completion of development.

## 2026-11-07 — Milestone M0: Foundation (COMPLETED)

- Implemented core scaffold (`app/main.py`, `app/core/*`, `app/db/*`, `app/models/{api_key,audit,idempotency}.py`, `app/services/{audit,bootstrap,idempotency}.py`, `alembic/versions/0001_initial.py`).
- Executed M0 pytest suite: 12 passed.

## 2026-11-11 — Milestones M1–M8 Implementation

### Implemented modules

- **M1 (Shipments & Policies):**
  - Models: `app/models/party.py`, `app/models/shipment.py`, `app/models/policy.py`
  - Schemas: `app/schemas/party.py`, `app/schemas/shipment.py`, `app/schemas/policy.py`
  - Services: `app/services/party.py`, `app/services/shipment.py`, `app/services/policy.py`
  - APIs: `app/api/v1/parties.py`, `app/api/v1/shipments.py`, `app/api/v1/policies.py`
  - Lifecycle validation, split percentage sum validation (`supplier + logistics == 100`), idempotent creation, and audit logging.
- **M2 (Climate Monitoring & Simulator):**
  - Models: `app/models/telemetry.py`, `app/models/port_delay.py`, `app/models/violation.py`
  - Schemas: `app/schemas/telemetry.py`, `app/schemas/port_delay.py`, `app/schemas/violation.py`
  - Services: `app/services/telemetry.py`, `app/services/monitoring.py`, `app/services/simulator.py`
  - APIs: `app/api/v1/telemetry.py`, `app/api/v1/monitoring.py`, `app/api/v1/simulator.py`
  - Range/timestamp validation, out-of-order sorting, duplicate deduplication, Haversine geofence check, and deterministic seeded simulator for Scenarios A and B.
- **M3 (Evidence Intelligence):**
  - Models: `app/models/evidence.py` (`EvidenceDocument`, `EvidenceExtraction`)
  - Schemas: `app/schemas/evidence.py`
  - Services: `app/services/evidence.py`, `app/services/pdf_extractor.py`, `app/services/pdf_fixture.py`, `app/services/image_qc.py`, `app/services/ai_provider.py`
  - API: `app/api/v1/evidence.py`
  - Magic-byte MIME verification, 20MB limit, filename traversal protection, encrypted PDF rejection, SHA-256 content-addressed storage, PyMuPDF + fallback text extraction, Laplacian blur + EXIF + dHash duplicate detection, `MockAIProvider` (observations-only trust boundary), and `GeminiAIProvider`.
- **M4 (Fraud & Cross-Verification):**
  - Models: `app/models/verification.py`, `app/models/fraud.py`
  - Schemas: `app/schemas/fraud.py`
  - Services: `app/services/verification.py`, `app/services/fraud.py`
  - API: `app/api/v1/fraud.py`
  - `SHIPMENT_ID_MATCH`, `TIMESTAMP_CONSISTENCY`, `IMAGE_INTEGRITY`, `STUCK_SENSOR`, `IMPOSSIBLE_TEMP_DELTA`, `GEOFENCE_JUMP`, `DUPLICATE_EVIDENCE`, and deterministic `IsolationForest`/z-score `STATISTICAL_OUTLIER`.
- **M5 (Claims & Settlement):**
  - Models: `app/models/claim.py`, `app/models/settlement.py`
  - Schemas: `app/schemas/claim.py`, `app/schemas/settlement.py`
  - Services: `app/services/claims.py`, `app/services/settlement.py`
  - APIs: `app/api/v1/claims.py`, `app/api/v1/settlements.py`
  - Pure deterministic `compute_pure_claim_decision`, canonical input/decision SHA-256 hashes, occurrence uniqueness, human reviewer override for `REVIEW_REQUIRED`, largest-remainder cent allocation (`allocate_split`), and single-use authorization nonce + hash binding.
- **M6 (Payment Engine):**
  - Models: `app/models/payout.py` (`Payout`, `PayoutAttempt`)
  - Schemas: `app/schemas/payout.py`
  - Services: `app/services/payment.py`, `app/services/payout.py`
  - API: `app/api/v1/payouts.py`
  - `MockPaymentProvider`, `PayPalSandboxAdapter` (`PayPal-Request-Id` idempotency header), strict single-use nonce consumption, `UNIQUE(settlement_id)`, and safe retry reusing the original idempotency key.
- **M7 (Dashboard):**
  - `dashboard/__init__.py`, `dashboard/api_client.py`, `dashboard/components.py`, `dashboard/app.py`
  - Streamlit + AG Grid (with `st.dataframe` fallback) views for Overview, Shipments, Policies, Claims & Decision Trace, Fraud, Payouts, Evidence, Audit, and Scenario Runner.
- **M8 (Scenarios, Migration & Tests):**
  - `app/services/scenarios.py`, `app/schemas/scenario.py`, `app/api/v1/scenarios.py`
  - `alembic/versions/0002_domain_tables.py`
  - Test suites: `tests/helpers.py`, `tests/test_m1_shipments_policies.py`, `tests/test_m2_monitoring.py`, `tests/test_m3_evidence.py`, `tests/test_m4_fraud.py`, `tests/test_m5_claims_settlement.py`, `tests/test_m6_payments.py`, `tests/test_m7_dashboard.py`, `tests/test_m8_e2e_security.py`, `tests/test_m8_scenarios.py`

### Verification executed in sandbox & actual results

1. `python -m compileall -q app dashboard tests alembic` — exited 0 (all modules compiled).
2. `python -m pytest --collect-only -q` — collected **42 tests** cleanly across M0–M8.
3. Non-`TestClient` unit tests (`python -m pytest -v -k "test_seeded_simulator_is_deterministic or test_identical_inputs_identical_decision_hash or test_inactive_policy_and_unmet_trigger_rejected or test_hard_block_rejects_and_review_routes or test_allocate_split_sums_exactly or test_pdf_fixture_is_not_encrypted or test_dashboard_api_client_instantiation"`): **7 passed, 35 deselected**.
4. Synchronous end-to-end verification against SQLite (`ScenarioService.run`):
   - `TABLES: 18` created cleanly via SQLAlchemy `Base.metadata.create_all`.
   - Scenario A (`seed=2026`): `claim_status='PAID'`, `payout_status='SUCCEEDED'`, `hard_block=False`, `violation_count=6`, `trigger_codes=['TEMP_HIGH']`.
   - Scenario B (`seed=2026`): `claim_status='REJECTED'`, `payout_id=None`, `hard_block=True`, `fraud_rules=['STUCK_SENSOR', 'IMPOSSIBLE_TEMP_DELTA', 'GEOFENCE_JUMP', 'STATISTICAL_OUTLIER']`.
5. Synchronous service lifecycle & payout retry verification (`MockPaymentProvider(force_fail=True)` -> `FAILED` -> `PayoutService.retry_payout` -> `SUCCEEDED`, `attempts=2`): `ALL_SVC_CHECKS_OK`.

### Not yet executed (deferred to project owner outside sandbox)

- Full 42-test `pytest` run (`TestClient` uses `anyio` / `asyncio.run`, which hangs inside the Windows sandbox).
- `alembic upgrade head` (requires `alembic` package installation).
- Live Streamlit dashboard session and live Gemini / PayPal Sandbox API calls (require credentials).
