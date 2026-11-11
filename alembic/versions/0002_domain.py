"""domain schema for shipments through payouts

Revision ID: 0002_domain
Revises: 0001_initial
Create Date: 2026-11-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_domain"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("payout_email", sa.String(length=255), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_parties"),
    )
    op.create_index("ix_parties_role", "parties", ["role"], unique=False)

    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_ref", sa.String(length=64), nullable=False),
        sa.Column("commodity", sa.String(length=128), nullable=False),
        sa.Column("origin_port", sa.String(length=128), nullable=False),
        sa.Column("destination_port", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("declared_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("logistics_id", sa.Integer(), nullable=False),
        sa.Column("route_waypoints", sa.JSON(), nullable=True),
        sa.Column("departure_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_arrival_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_arrival_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["parties.id"], name="fk_shipments_supplier_id_parties"
        ),
        sa.ForeignKeyConstraint(
            ["logistics_id"], ["parties.id"], name="fk_shipments_logistics_id_parties"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shipments"),
    )
    op.create_index("ix_shipments_external_ref", "shipments", ["external_ref"], unique=True)
    op.create_index("ix_shipments_supplier_id", "shipments", ["supplier_id"], unique=False)
    op.create_index("ix_shipments_logistics_id", "shipments", ["logistics_id"], unique=False)
    op.create_index("ix_shipments_status", "shipments", ["status"], unique=False)

    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_number", sa.String(length=64), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("coverage_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("premium_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("temp_min_c", sa.Float(), nullable=False),
        sa.Column("temp_max_c", sa.Float(), nullable=False),
        sa.Column("humidity_max_pct", sa.Float(), nullable=False),
        sa.Column("delay_hours_max", sa.Float(), nullable=False),
        sa.Column("geofence_max_km", sa.Float(), nullable=False),
        sa.Column("coverage_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_split_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("logistics_split_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"], ["shipments.id"], name="fk_policies_shipment_id_shipments"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_policies"),
    )
    op.create_index("ix_policies_policy_number", "policies", ["policy_number"], unique=True)
    op.create_index("ix_policies_shipment_id", "policies", ["shipment_id"], unique=False)
    op.create_index("ix_policies_status", "policies", ["status"], unique=False)

    op.create_table(
        "telemetry_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("humidity_pct", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name="fk_telemetry_readings_shipment_id_shipments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_telemetry_readings"),
        sa.UniqueConstraint(
            "shipment_id",
            "device_id",
            "recorded_at",
            name="uq_telemetry_shipment_device_ts",
        ),
    )
    op.create_index(
        "ix_telemetry_readings_shipment_id",
        "telemetry_readings",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_telemetry_readings_device_id",
        "telemetry_readings",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_telemetry_readings_recorded_at",
        "telemetry_readings",
        ["recorded_at"],
        unique=False,
    )

    op.create_table(
        "port_delays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("port_name", sa.String(length=128), nullable=False),
        sa.Column("delay_hours", sa.Numeric(8, 2), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"], ["shipments.id"], name="fk_port_delays_shipment_id_shipments"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_port_delays"),
    )
    op.create_index("ix_port_delays_shipment_id", "port_delays", ["shipment_id"], unique=False)
    op.create_index("ix_port_delays_reported_at", "port_delays", ["reported_at"], unique=False)

    op.create_table(
        "violations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("trigger_code", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=True),
        sa.Column("port_delay_id", sa.Integer(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"], ["shipments.id"], name="fk_violations_shipment_id_shipments"
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["policies.id"], name="fk_violations_policy_id_policies"
        ),
        sa.ForeignKeyConstraint(
            ["reading_id"],
            ["telemetry_readings.id"],
            name="fk_violations_reading_id_telemetry_readings",
        ),
        sa.ForeignKeyConstraint(
            ["port_delay_id"],
            ["port_delays.id"],
            name="fk_violations_port_delay_id_port_delays",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_violations"),
    )
    op.create_index("ix_violations_shipment_id", "violations", ["shipment_id"], unique=False)
    op.create_index("ix_violations_policy_id", "violations", ["policy_id"], unique=False)
    op.create_index("ix_violations_trigger_code", "violations", ["trigger_code"], unique=False)
    op.create_index("ix_violations_occurred_at", "violations", ["occurred_at"], unique=False)

    op.create_table(
        "evidence_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("perceptual_hash", sa.String(length=32), nullable=True),
        sa.Column("blur_score", sa.Float(), nullable=True),
        sa.Column("blur_passed", sa.Boolean(), nullable=True),
        sa.Column("exif_summary", sa.JSON(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name="fk_evidence_documents_shipment_id_shipments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_documents"),
    )
    op.create_index(
        "ix_evidence_documents_shipment_id",
        "evidence_documents",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_documents_doc_type", "evidence_documents", ["doc_type"], unique=False
    )
    op.create_index(
        "ix_evidence_documents_sha256", "evidence_documents", ["sha256"], unique=False
    )
    op.create_index(
        "ix_evidence_documents_perceptual_hash",
        "evidence_documents",
        ["perceptual_hash"],
        unique=False,
    )

    op.create_table(
        "evidence_extractions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["evidence_documents.id"],
            name="fk_evidence_extractions_document_id_evidence_documents",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_extractions"),
    )
    op.create_index(
        "ix_evidence_extractions_document_id",
        "evidence_extractions",
        ["document_id"],
        unique=False,
    )

    op.create_table(
        "verification_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("check_code", sa.String(length=64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name="fk_verification_results_shipment_id_shipments",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["evidence_documents.id"],
            name="fk_verification_results_document_id_evidence_documents",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_results"),
    )
    op.create_index(
        "ix_verification_results_shipment_id",
        "verification_results",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_verification_results_check_code",
        "verification_results",
        ["check_code"],
        unique=False,
    )

    op.create_table(
        "fraud_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            ["shipments.id"],
            name="fk_fraud_signals_shipment_id_shipments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fraud_signals"),
    )
    op.create_index(
        "ix_fraud_signals_shipment_id", "fraud_signals", ["shipment_id"], unique=False
    )
    op.create_index("ix_fraud_signals_rule_code", "fraud_signals", ["rule_code"], unique=False)
    op.create_index("ix_fraud_signals_severity", "fraud_signals", ["severity"], unique=False)

    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("trigger_code", sa.String(length=32), nullable=False),
        sa.Column("occurrence_key", sa.String(length=128), nullable=False),
        sa.Column("claimed_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_trace", sa.JSON(), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("decision_hash", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["policies.id"], name="fk_claims_policy_id_policies"
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"], ["shipments.id"], name="fk_claims_shipment_id_shipments"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_claims"),
        sa.UniqueConstraint(
            "policy_id",
            "trigger_code",
            "occurrence_key",
            name="uq_claims_policy_trigger_occurrence",
        ),
    )
    op.create_index("ix_claims_policy_id", "claims", ["policy_id"], unique=False)
    op.create_index("ix_claims_shipment_id", "claims", ["shipment_id"], unique=False)
    op.create_index("ix_claims_trigger_code", "claims", ["trigger_code"], unique=False)
    op.create_index("ix_claims_status", "claims", ["status"], unique=False)
    op.create_index("ix_claims_idempotency_key", "claims", ["idempotency_key"], unique=True)

    op.create_table(
        "settlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("supplier_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("logistics_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("authorization_nonce", sa.String(length=64), nullable=False),
        sa.Column("authorization_hash", sa.String(length=64), nullable=False),
        sa.Column("nonce_used", sa.Boolean(), nullable=False),
        sa.Column(
            "settled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claims.id"], name="fk_settlements_claim_id_claims"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_settlements"),
    )
    op.create_index("ix_settlements_claim_id", "settlements", ["claim_id"], unique=True)
    op.create_index(
        "ix_settlements_authorization_nonce",
        "settlements",
        ["authorization_nonce"],
        unique=True,
    )

    op.create_table(
        "settlement_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("party_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["settlement_id"],
            ["settlements.id"],
            name="fk_settlement_lines_settlement_id_settlements",
        ),
        sa.ForeignKeyConstraint(
            ["party_id"], ["parties.id"], name="fk_settlement_lines_party_id_parties"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_settlement_lines"),
    )
    op.create_index(
        "ix_settlement_lines_settlement_id",
        "settlement_lines",
        ["settlement_id"],
        unique=False,
    )
    op.create_index(
        "ix_settlement_lines_party_id", "settlement_lines", ["party_id"], unique=False
    )

    op.create_table(
        "payouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["settlement_id"],
            ["settlements.id"],
            name="fk_payouts_settlement_id_settlements",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payouts"),
    )
    op.create_index("ix_payouts_settlement_id", "payouts", ["settlement_id"], unique=True)
    op.create_index("ix_payouts_idempotency_key", "payouts", ["idempotency_key"], unique=True)
    op.create_index("ix_payouts_status", "payouts", ["status"], unique=False)

    op.create_table(
        "payout_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payout_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("request_summary", sa.JSON(), nullable=False),
        sa.Column("response_summary", sa.JSON(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["payout_id"], ["payouts.id"], name="fk_payout_attempts_payout_id_payouts"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payout_attempts"),
    )
    op.create_index(
        "ix_payout_attempts_payout_id", "payout_attempts", ["payout_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("payout_attempts")
    op.drop_table("payouts")
    op.drop_table("settlement_lines")
    op.drop_table("settlements")
    op.drop_table("claims")
    op.drop_table("fraud_signals")
    op.drop_table("verification_results")
    op.drop_table("evidence_extractions")
    op.drop_table("evidence_documents")
    op.drop_table("violations")
    op.drop_table("port_delays")
    op.drop_table("telemetry_readings")
    op.drop_table("policies")
    op.drop_table("shipments")
    op.drop_table("parties")
