# Pending Development Tracker

## Current status

- **Milestones M0–M8 (code implementation):** IMPLEMENTED across models, schemas, services, API v1 routes, Alembic migration `0002_domain_tables`, Streamlit dashboard, scenario runner, and pytest suite (42 collected tests).
- **Verification status:** Synchronous compileall, pure unit tests (7/7), synchronous Scenario A & B runs, and synchronous payout retry checks passed. Full HTTP `TestClient` pytest run (35 remaining tests) and Alembic CLI upgrade remain pending execution outside the Windows sandbox.
- **Constraints:** no Docker, no git operations.
- **Dependencies:** installation of optional/missing packages (`alembic`, `PyMuPDF`, `opencv-python-headless`, `scikit-learn`, `streamlit-aggrid`, `google-genai`, `psycopg`) deferred to the project owner.
- **Environment:** SQLite default; Gemini and PayPal use deterministic mock providers by default.

## Completed / Implemented tasks

| ID | Task | Priority | Status | Verified by |
|---|---|---|---|---|
| PCMS-001..009 | M0 Foundation, auth, audit, idempotency, health, Alembic `0001_initial` | P0 | COMPLETED | M0 pytest (12 passed) |
| PCMS-101 | `parties`, `shipments` models, schemas, services, APIs | P0 | IMPLEMENTED | `compileall`; synchronous service & scenario check |
| PCMS-102 | `policies` model, thresholds, lifecycle, APIs | P0 | IMPLEMENTED | `compileall`; synchronous service & scenario check |
| PCMS-103 | M1 tests (`tests/test_m1_shipments_policies.py`) | P0 | IMPLEMENTED | Collected by pytest (5 tests; HTTP run pending outside sandbox) |
| PCMS-201 | `telemetry_readings`, `port_delays` models + ingest API | P0 | IMPLEMENTED | `compileall`; synchronous ingest check |
| PCMS-202 | Monitoring engine: temp, humidity, geofence, port delay | P0 | IMPLEMENTED | `compileall`; synchronous Scenario A/B check |
| PCMS-203 | Deterministic seeded simulator | P0 | IMPLEMENTED | `test_seeded_simulator_is_deterministic` PASSED |
| PCMS-204 | Monitoring tests (`tests/test_m2_monitoring.py`) | P0 | IMPLEMENTED | 1 unit test passed; 3 HTTP tests pending outside sandbox |
| PCMS-301 | Secure evidence upload, SHA-256, content-addressed store | P0 | IMPLEMENTED | `compileall`; synchronous Scenario A/B upload |
| PCMS-302 | PDF text + page rendering (`PdfExtractorService` w/ PyMuPDF + fallback) | P0 | IMPLEMENTED | `test_pdf_fixture_is_not_encrypted` PASSED |
| PCMS-303 | `AIProvider` interface + deterministic `MockAIProvider` | P0 | IMPLEMENTED | Synchronous Scenario A/B extraction |
| PCMS-304 | `GeminiAIProvider`, JSON schema, prompt versioning (`gemini-v1.0`) | P1 | IMPLEMENTED | `compileall` (live path requires `GEMINI_API_KEY`) |
| PCMS-305 | Image QC (`ImageQCService`: blur, EXIF, dHash duplicate check) | P1 | IMPLEMENTED | Synchronous Scenario A/B image QC |
| PCMS-306 | Evidence tests (`tests/test_m3_evidence.py`) | P0 | IMPLEMENTED | 1 unit test passed; 4 HTTP tests pending outside sandbox |
| PCMS-401 | Evidence cross-verification (`VerificationService`) | P0 | IMPLEMENTED | Synchronous Scenario A/B verification |
| PCMS-402 | Rule-based `FraudEngine` with explanations & severity tiers | P0 | IMPLEMENTED | Synchronous Scenario B check (`STUCK_SENSOR`, `IMPOSSIBLE_TEMP_DELTA`, `GEOFENCE_JUMP`) |
| PCMS-403 | Statistical anomaly detection (`IsolationForest` + z-score) | P1 | IMPLEMENTED | Synchronous Scenario B check (`STATISTICAL_OUTLIER`) |
| PCMS-404 | Fraud tests (`tests/test_m4_fraud.py`) | P0 | IMPLEMENTED | Collected by pytest (2 HTTP tests pending outside sandbox) |
| PCMS-501 | Claim model, submission, occurrence uniqueness, idempotency | P0 | IMPLEMENTED | Synchronous service & Scenario A/B check |
| PCMS-502 | Deterministic `ClaimsEngine` + rule trace + hashes | P0 | IMPLEMENTED | 3 pure unit tests PASSED (`test_m5_claims_settlement.py`) |
| PCMS-503 | `SettlementService` split + single-use authorization nonce | P0 | IMPLEMENTED | `test_allocate_split_sums_exactly` PASSED; sync check passed |
| PCMS-504 | Claims/settlement tests (`tests/test_m5_claims_settlement.py`) | P0 | IMPLEMENTED | 4 unit tests passed; 1 HTTP test pending outside sandbox |
| PCMS-601 | `PaymentAdapter` interface + `MockPaymentProvider` | P0 | IMPLEMENTED | Synchronous Scenario A & service checks |
| PCMS-602 | `PayPalSandboxAdapter` (`PayPal-Request-Id` idempotency) | P1 | IMPLEMENTED | `compileall` (live path requires sandbox credentials) |
| PCMS-603 | `PayoutService` retry and failure handling | P0 | IMPLEMENTED | Synchronous `force_fail=True` -> `retry_payout` check passed |
| PCMS-604 | Payment tests (`tests/test_m6_payments.py`) | P0 | IMPLEMENTED | Collected by pytest (3 HTTP tests pending outside sandbox) |
| PCMS-701..704 | Streamlit + AG Grid dashboard (`dashboard/`) + API client | P1 | IMPLEMENTED | `test_dashboard_api_client_instantiation` PASSED |
| PCMS-801 | Scenario A end-to-end (`ScenarioService` + `tests/test_m8_*`) | P0 | IMPLEMENTED | Synchronous Scenario A (`PAID`, `SUCCEEDED`) passed; HTTP tests pending |
| PCMS-802 | Scenario B end-to-end (`ScenarioService` + `tests/test_m8_*`) | P0 | IMPLEMENTED | Synchronous Scenario B (`REJECTED`, no payout) passed; HTTP tests pending |
| PCMS-803 | Security checks (auth, magic-byte/traversal/encrypted PDF, nonce, audit) | P0 | IMPLEMENTED | Implemented & covered by test suite |
| PCMS-804 | Alembic `0002_domain_tables` & documentation updates | P0 | IMPLEMENTED | All docs & migration file updated |

## Remaining tasks for verification & future development

### Immediate Owner Verification (Local Environment Outside Sandbox)

| ID | Task | Priority | Status | Acceptance criteria |
|---|---|---|---|---|
| VER-001 | Create `.venv` and install `requirements.txt` (`alembic`, `PyMuPDF`, `opencv-python-headless`, `scikit-learn`, `streamlit-aggrid`, `google-genai`, `psycopg[binary]`) | P0 | PENDING_OWNER | `pip install -r requirements.txt` succeeds |
| VER-002 | Run `python -m alembic upgrade head` against SQLite | P0 | PENDING_OWNER | Applies `0001_initial` and `0002_domain_tables` cleanly |
| VER-003 | Run full pytest suite `python -m pytest -q` (and `--cov=app`) outside sandbox | P0 | PENDING_OWNER | All 42 collected tests pass (`TestClient` hangs inside sandbox `asyncio`) |
| VER-004 | Smoke-test FastAPI (`uvicorn app.main:app --port 8000`) + Streamlit (`streamlit run dashboard/app.py --server.port 8501`) | P1 | PENDING_OWNER | Dashboard loads all views and runs Scenarios A & B |
| VER-005 | Optional live credential verification (`AI_PROVIDER=gemini`, `PAYMENT_PROVIDER=paypal`) | P2 | BLOCKED_NO_CREDS | Verified with real Gemini API key & PayPal Sandbox client ID/secret |

### Future Product & Platform Enhancements

#### Shipment and policy
- Policy versioning and dynamic actuarial premium pricing model.
- Multi-leg shipments with carrier-specific terms and intermediate handoff events.

#### Monitoring
- External weather and port congestion API adapters with signed provenance.
- Proactive alerting webhooks when telemetry approaches policy thresholds.

#### Evidence and AI
- Barcode/QR verification and stamped-signature OCR on Bills of Lading.
- Satellite imagery change detection for port/route disruptions.
- Prompt evaluation harness with recorded Gemini response fixtures.

#### Fraud
- Labeled calibration dataset and model drift monitoring for `IsolationForest`.
- Human reviewer feedback loop persisting labeled fraud outcomes.

#### Claims and settlement
- Multi-currency support with locked FX rate snapshots at policy issuance / settlement.
- Formal dispute / appeal workflow for `REJECTED` claims.

#### Payments
- PayPal Payouts webhook listener & reconciliation state machine (`BATCH_PROCESSING` / `ITEM_UNCLAIMED` / `REFUNDED`).
- PostgreSQL advisory locks (`pg_advisory_xact_lock`) for multi-worker concurrent payout safety.

#### Platform & Security
- JWT/OAuth2 user authentication alongside API keys.
- Rate limiting middleware and OpenTelemetry metrics/tracing.
- External immutable audit log anchoring and data retention policy.
- Cursor-based pagination and filtering across all list endpoints (`shipments`, `policies`, `claims`, `audit`).

## Known limitations & technical debt

- Windows `asyncio` (`TestClient` / `anyio` blocking portal) hangs inside the restricted sandbox; the 35 `TestClient` API integration tests must be executed locally by the project owner.
- `PyMuPDF`, `opencv-python-headless`, `scikit-learn`, `streamlit-aggrid`, `alembic`, and `google-genai` are not yet installed in the local global Python 3.12 environment (fallback paths are active for PDF text scan, NumPy Laplacian blur check, z-score outlier detection, and `st.dataframe`).
- SQLite single-writer locking; production multi-worker deployment requires PostgreSQL + advisory locks.
- Live Gemini and PayPal Sandbox HTTP paths remain unverified without credentials.
