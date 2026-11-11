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
   claims, settlements, or payments (`FORBIDDEN_OBSERVATION_KEYS` enforced).
2. The claims engine (`compute_pure_claim_decision`) is a pure function of policy
   terms, verified facts, and fraud signals. Identical inputs produce an identical
   decision hash.
3. Only the claims engine (or explicit `reviewer`/`admin` resolution of `REVIEW_REQUIRED`)
   can produce `APPROVED`.
4. Only a `Settlement` with a valid, single-use authorization nonce (`nonce_used=False`)
   and verified `authorization_hash` can be paid.
5. A payment adapter never receives raw telemetry or model output.

## 4. Module responsibilities

| Module | Responsibility | Status |
|---|---|---|
| `core` | Settings, JSON logging, error envelope, API-key auth, request IDs | Implemented (M0) |
| `db` | Engine, session, declarative base, init | Implemented (M0) |
| `models` | All 18 ORM entities (`api_keys`..`payout_attempts`) | Implemented (M0–M6) |
| `services.audit` | Hash-chained append-only audit log | Implemented (M0) |
| `services.idempotency` | Idempotency key lifecycle | Implemented (M0) |
| `party / shipment / policy` | Parties, shipments, policies, lifecycle validation | Implemented (M1) |
| `monitoring / simulator` | Telemetry validation, derived violations, seeded simulator | Implemented (M2) |
| `evidence` | Secure upload, SHA-256, PDF extraction, image QC | Implemented (M3) |
| `ai_provider` | `AIProvider` interface, `MockAIProvider`, `GeminiAIProvider` | Implemented (M3) |
| `verification` | Document/image/telemetry cross-checks | Implemented (M4) |
| `fraud` | Rules, `IsolationForest` + z-score anomalies, explanations | Implemented (M4) |
| `claims` | Pure deterministic eligibility, payout formula, trace, hashes | Implemented (M5) |
| `settlement` | Largest-remainder split and single-use authorization nonce | Implemented (M5) |
| `payments / payout` | Mock and PayPal Sandbox adapters, idempotent retries | Implemented (M6) |
| `dashboard` | Streamlit + AG Grid UI (`dashboard/app.py`) | Implemented (M7) |
| `scenarios` | Repeatable end-to-end Scenario A / Scenario B runner | Implemented (M8) |

## 5. Database design (18 tables)

| Table | Key fields |
|---|---|
| `api_keys` | `name`, `key_prefix`, `key_hash`, `role`, `active` |
| `audit_logs` | `actor`, `action`, `entity_type`, `entity_id`, `request_id`, `before_json`, `after_json`, `prev_hash`, `hash` |
| `idempotency_keys` | `scope`, `key`, `request_hash`, `status_code`, `response_json`; unique `(scope, key)` |
| `parties` | `role` (supplier/logistics), `name`, `payout_email`, `country_code` |
| `shipments` | `external_ref` (unique), `commodity`, `origin_port`, `destination_port`, `mode`, `declared_value`, `route_waypoints`, `status` |
| `policies` | `policy_number` (unique), `shipment_id`, `coverage_amount`, `premium_amount`, thresholds, coverage window, `supplier_split_pct`, `logistics_split_pct`, `version`, `status` |
| `telemetry_readings` | `shipment_id`, `device_id`, `recorded_at`, `temperature_c`, `humidity_pct`, `latitude`, `longitude`, `source` |
| `port_delays` | `shipment_id`, `port_name`, `delay_hours`, `reported_at` |
| `violations` | `shipment_id`, `policy_id`, `trigger_code`, `reading_id`, `port_delay_id`, `threshold_value`, `actual_value`, `explanation` |
| `evidence_documents` | `shipment_id`, `doc_type`, `sha256`, `storage_path`, `mime_type`, `file_size`, `extracted_text`, `perceptual_hash`, `blur_score`, `blur_passed` |
| `evidence_extractions` | `document_id`, `provider`, `model_name`, `prompt_version`, `extracted_fields`, `confidence`, `raw_response` |
| `verification_results` | `shipment_id`, `document_id`, `check_code`, `passed`, `details` |
| `fraud_signals` | `shipment_id`, `rule_code`, `severity`, `score`, `explanation`, `evidence_refs` |
| `claims` | `policy_id`, `trigger_code`, `occurrence_key` (unique tuple), `claimed_amount`, `approved_amount`, `status`, `decision_trace`, `input_hash`, `decision_hash`, `idempotency_key` (unique) |
| `settlements` | `claim_id` (unique), `total_amount`, `currency`, `supplier_amount`, `logistics_amount`, `authorization_nonce` (unique), `authorization_hash`, `nonce_used` |
| `settlement_lines` | `settlement_id`, `party_id`, `role`, `recipient_email`, `amount` |
| `payouts` | `settlement_id` (unique), `idempotency_key` (unique), `provider`, `external_id`, `status`, `amount`, `currency`, `attempts` |
| `payout_attempts` | `payout_id`, `attempt_number`, `request_summary`, `response_summary`, `success` |

## 6. State machines

- **Shipment:** `REGISTERED -> IN_TRANSIT -> DELIVERED -> CLOSED`, `CANCELLED`
- **Policy:** `DRAFT -> ACTIVE -> TRIGGERED -> SETTLED`, `EXPIRED`, `CANCELLED`
- **Claim:** `SUBMITTED -> EVALUATING -> APPROVED | REJECTED | REVIEW_REQUIRED`;
  `APPROVED -> SETTLED -> PAYOUT_PENDING -> PAID`; `PAYOUT_FAILED`.
  Only `reviewer` / `admin` can resolve `REVIEW_REQUIRED`.
- **Payout:** `PENDING -> SENT -> SUCCEEDED | FAILED`; `FAILED -> RETRYING -> SENT`

## 7. Idempotency and financial integrity

- Claim occurrence is unique per `(policy_id, trigger_code, occurrence_key)`.
- One settlement per claim (`UNIQUE(claim_id)`); one payout per settlement (`UNIQUE(settlement_id)`).
- `UNIQUE(idempotency_key)` on claims and payouts.
- PayPal `PayPal-Request-Id` equals the payout idempotency key.
- Payment authorization is a single-use nonce bound to settlement id, amount,
  currency, and decision hash.
- Money is handled with `Decimal` and stored as `NUMERIC(18,2)`; allocation uses
  largest-remainder rounding (`allocate_split`) so the sum exactly equals the settlement total.
- Failed payouts retry with the same idempotency key; a second external payout
  cannot be created.
