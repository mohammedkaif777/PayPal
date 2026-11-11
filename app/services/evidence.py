import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.evidence import EvidenceDocument, EvidenceExtraction
from app.models.shipment import Shipment
from app.services.ai_provider import get_ai_provider
from app.services.audit import AuditService
from app.services.image_qc import ImageQCService
from app.services.pdf_extractor import PdfExtractorService

MAX_EVIDENCE_BYTES = 20 * 1024 * 1024  # 20 MB

ALLOWED_DOC_TYPES = {"BILL_OF_LADING", "INSPECTION_REPORT", "PHOTO", "OTHER"}

MAGIC_MIME_MAP = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def detect_mime_from_magic(content: bytes) -> str | None:
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "upload.bin"
    if ".." in filename or "/" in filename or "\\" in filename:
        # Check for obvious traversal attempts
        if ".." in Path(filename).parts:
            raise AppError(
                "Invalid filename: path traversal is not allowed",
                code="invalid_filename",
                status_code=400,
            )
    clean = Path(filename).name.strip()
    if not clean or clean in {".", ".."}:
        raise AppError(
            "Invalid filename",
            code="invalid_filename",
            status_code=400,
        )
    return clean[:255]


class EvidenceService:
    @staticmethod
    def upload(
        db: Session,
        *,
        shipment_id: int,
        doc_type: str,
        filename: str | None,
        content: bytes,
        actor: str,
    ) -> EvidenceDocument:
        if doc_type not in ALLOWED_DOC_TYPES:
            raise AppError(
                f"Invalid doc_type '{doc_type}'",
                code="invalid_doc_type",
                status_code=400,
            )

        shipment = db.get(Shipment, shipment_id)
        if shipment is None:
            raise AppError(
                f"Shipment {shipment_id} not found",
                code="not_found",
                status_code=404,
            )

        clean_name = sanitize_filename(filename)
        if not content:
            raise AppError("Empty file uploaded", code="empty_file", status_code=400)
        if len(content) > MAX_EVIDENCE_BYTES:
            raise AppError(
                "File exceeds maximum allowed size of 20MB",
                code="file_too_large",
                status_code=413,
            )

        detected_mime = detect_mime_from_magic(content)
        if detected_mime is None or detected_mime not in MAGIC_MIME_MAP:
            raise AppError(
                "Unsupported file type (allowed: PDF, JPEG, PNG by magic bytes)",
                code="unsupported_media_type",
                status_code=415,
            )

        if detected_mime == "application/pdf" and PdfExtractorService.is_encrypted_pdf(
            content
        ):
            raise AppError(
                "Encrypted PDFs are rejected",
                code="encrypted_pdf",
                status_code=400,
            )

        sha256 = hashlib.sha256(content).hexdigest()
        settings = get_settings()
        evidence_root = settings.evidence_dir.resolve()
        evidence_root.mkdir(parents=True, exist_ok=True)
        ext = MAGIC_MIME_MAP[detected_mime]
        target_path = (evidence_root / f"{sha256}{ext}").resolve()
        if not str(target_path).startswith(str(evidence_root)):
            raise AppError("Unsafe storage path", code="invalid_path", status_code=400)

        if not target_path.exists():
            target_path.write_bytes(content)

        extracted_text: str | None = None
        perceptual_hash: str | None = None
        blur_score: float | None = None
        blur_passed: bool | None = None
        exif_summary: dict | None = None

        if detected_mime == "application/pdf":
            extracted_text = PdfExtractorService.extract_text(target_path)
        else:
            blur_passed, blur_score = ImageQCService.check_blur(content)
            perceptual_hash = ImageQCService.compute_perceptual_hash(content)
            exif_summary = ImageQCService.extract_exif(content)

        doc = EvidenceDocument(
            shipment_id=shipment_id,
            doc_type=doc_type,
            original_filename=clean_name,
            sha256=sha256,
            storage_path=str(target_path),
            mime_type=detected_mime,
            file_size=len(content),
            extracted_text=extracted_text,
            perceptual_hash=perceptual_hash,
            blur_score=blur_score,
            blur_passed=blur_passed,
            exif_summary=exif_summary,
        )
        db.add(doc)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="upload_evidence",
            entity_type="evidence_document",
            entity_id=str(doc.id),
            after={
                "shipment_id": shipment_id,
                "doc_type": doc_type,
                "sha256": sha256,
                "mime_type": detected_mime,
                "file_size": len(content),
            },
        )
        return doc

    @staticmethod
    def get(db: Session, document_id: int) -> EvidenceDocument:
        doc = db.get(EvidenceDocument, document_id)
        if doc is None:
            raise AppError(
                f"Evidence document {document_id} not found",
                code="not_found",
                status_code=404,
            )
        return doc

    @staticmethod
    def list_by_shipment(db: Session, shipment_id: int) -> list[EvidenceDocument]:
        return list(
            db.scalars(
                select(EvidenceDocument)
                .where(EvidenceDocument.shipment_id == shipment_id)
                .order_by(EvidenceDocument.id.asc())
            ).all()
        )

    @staticmethod
    def extract(
        db: Session, document_id: int, *, actor: str
    ) -> EvidenceExtraction:
        doc = EvidenceService.get(db, document_id)
        provider = get_ai_provider()
        result = provider.extract(
            document_path=Path(doc.storage_path),
            doc_type=doc.doc_type,
            extracted_text=doc.extracted_text or "",
        )
        extraction = EvidenceExtraction(
            document_id=doc.id,
            provider=result.provider,
            model_name=result.model_name,
            prompt_version=result.prompt_version,
            extracted_fields=result.fields,
            confidence=result.confidence,
            raw_response=result.raw_response,
        )
        db.add(extraction)
        db.flush()
        AuditService.record(
            db,
            actor=actor,
            action="extract_evidence",
            entity_type="evidence_extraction",
            entity_id=str(extraction.id),
            after={
                "document_id": doc.id,
                "provider": result.provider,
                "confidence": result.confidence,
            },
        )
        return extraction

    @staticmethod
    def list_extractions(db: Session, document_id: int) -> list[EvidenceExtraction]:
        return list(
            db.scalars(
                select(EvidenceExtraction)
                .where(EvidenceExtraction.document_id == document_id)
                .order_by(EvidenceExtraction.id.asc())
            ).all()
        )
