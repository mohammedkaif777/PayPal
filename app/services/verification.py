from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.evidence import EvidenceDocument, EvidenceExtraction
from app.models.shipment import Shipment
from app.models.verification import VerificationResult
from app.services.audit import AuditService
from app.services.image_qc import ImageQCService


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        cleaned = value.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)
        return _ensure_utc(parsed)
    except ValueError:
        return None


class VerificationService:
    @staticmethod
    def cross_verify_evidence(
        db: Session, shipment_id: int, *, actor: str = "system"
    ) -> list[VerificationResult]:
        shipment = db.get(Shipment, shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {shipment_id} not found",
                code="not_found",
                status_code=404,
            )

        db.execute(
            delete(VerificationResult).where(
                VerificationResult.shipment_id == shipment_id
            )
        )

        docs = list(
            db.scalars(
                select(EvidenceDocument)
                .where(EvidenceDocument.shipment_id == shipment_id)
                .order_by(EvidenceDocument.id.asc())
            ).all()
        )
        results: list[VerificationResult] = []

        dep_utc = _ensure_utc(shipment.departure_time)
        arr_utc = _ensure_utc(shipment.expected_arrival_time)

        for doc in docs:
            latest_extraction = db.scalar(
                select(EvidenceExtraction)
                .where(EvidenceExtraction.document_id == doc.id)
                .order_by(EvidenceExtraction.id.desc())
                .limit(1)
            )
            if latest_extraction is not None:
                fields = latest_extraction.extracted_fields
                ext_ref = fields.get("shipment_ref")
                if ext_ref and str(ext_ref).upper() != "UNKNOWN":
                    matched = str(ext_ref).strip() == shipment.external_ref
                    results.append(
                        VerificationResult(
                            shipment_id=shipment_id,
                            document_id=doc.id,
                            check_code="SHIPMENT_ID_MATCH",
                            passed=matched,
                            details={
                                "expected_ref": shipment.external_ref,
                                "extracted_ref": str(ext_ref),
                            },
                        )
                    )

                doc_dt = _parse_iso_dt(fields.get("document_date"))
                if doc_dt is not None:
                    window_start = dep_utc - timedelta(days=7)
                    window_end = arr_utc + timedelta(days=14)
                    in_window = window_start <= doc_dt <= window_end
                    results.append(
                        VerificationResult(
                            shipment_id=shipment_id,
                            document_id=doc.id,
                            check_code="TIMESTAMP_CONSISTENCY",
                            passed=in_window,
                            details={
                                "document_date": doc_dt.isoformat(),
                                "window_start": window_start.isoformat(),
                                "window_end": window_end.isoformat(),
                            },
                        )
                    )

            if doc.mime_type.startswith("image/"):
                duplicate = ImageQCService.find_duplicate_document(
                    db,
                    sha256=doc.sha256,
                    perceptual_hash=doc.perceptual_hash,
                    exclude_doc_id=doc.id,
                )
                cross_shipment_dup = (
                    duplicate is not None and duplicate.shipment_id != shipment_id
                )
                blur_ok = True if doc.blur_passed is None else bool(doc.blur_passed)
                results.append(
                    VerificationResult(
                        shipment_id=shipment_id,
                        document_id=doc.id,
                        check_code="IMAGE_INTEGRITY",
                        passed=blur_ok and not cross_shipment_dup,
                        details={
                            "blur_passed": doc.blur_passed,
                            "blur_score": doc.blur_score,
                            "duplicate_document_id": (
                                duplicate.id if cross_shipment_dup and duplicate else None
                            ),
                        },
                    )
                )

        for res in results:
            db.add(res)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="cross_verify_evidence",
            entity_type="shipment",
            entity_id=str(shipment_id),
            after={
                "checks_run": len(results),
                "failed": sum(1 for r in results if not r.passed),
            },
        )
        return results

    @staticmethod
    def list_by_shipment(db: Session, shipment_id: int) -> list[VerificationResult]:
        return list(
            db.scalars(
                select(VerificationResult)
                .where(VerificationResult.shipment_id == shipment_id)
                .order_by(VerificationResult.id.asc())
            ).all()
        )

