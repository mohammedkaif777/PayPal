from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import Actor, require_roles
from app.db.session import get_db
from app.schemas.evidence import (
    EvidenceDocumentResponse,
    EvidenceExtractionResponse,
    ImageQCResponse,
)
from app.services.evidence import EvidenceService
from app.services.image_qc import ImageQCService

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post(
    "/upload",
    response_model=EvidenceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    shipment_id: int = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> EvidenceDocumentResponse:
    content = await file.read()
    doc = EvidenceService.upload(
        db,
        shipment_id=shipment_id,
        doc_type=doc_type,
        filename=file.filename,
        content=content,
        actor=actor.name,
    )
    db.commit()
    db.refresh(doc)
    return EvidenceDocumentResponse.model_validate(doc)


@router.get("/shipment/{shipment_id}", response_model=list[EvidenceDocumentResponse])
def list_evidence_by_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[EvidenceDocumentResponse]:
    docs = EvidenceService.list_by_shipment(db, shipment_id)
    return [EvidenceDocumentResponse.model_validate(d) for d in docs]


@router.get("/{document_id}", response_model=EvidenceDocumentResponse)
def get_evidence(
    document_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> EvidenceDocumentResponse:
    return EvidenceDocumentResponse.model_validate(EvidenceService.get(db, document_id))


@router.post("/{document_id}/extract", response_model=EvidenceExtractionResponse)
def extract_evidence(
    document_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator")),
) -> EvidenceExtractionResponse:
    extraction = EvidenceService.extract(db, document_id, actor=actor.name)
    db.commit()
    db.refresh(extraction)
    return EvidenceExtractionResponse.model_validate(extraction)


@router.get("/{document_id}/extractions", response_model=list[EvidenceExtractionResponse])
def list_extractions(
    document_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> list[EvidenceExtractionResponse]:
    rows = EvidenceService.list_extractions(db, document_id)
    return [EvidenceExtractionResponse.model_validate(r) for r in rows]


@router.get("/{document_id}/qc", response_model=ImageQCResponse)
def get_image_qc(
    document_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("admin", "operator", "reviewer", "read_only")),
) -> ImageQCResponse:
    doc = EvidenceService.get(db, document_id)
    duplicate = ImageQCService.find_duplicate_document(
        db,
        sha256=doc.sha256,
        perceptual_hash=doc.perceptual_hash,
        exclude_doc_id=doc.id,
    )
    return ImageQCResponse(
        document_id=doc.id,
        blur_score=doc.blur_score,
        blur_passed=doc.blur_passed,
        perceptual_hash=doc.perceptual_hash,
        duplicate_of_document_id=duplicate.id if duplicate is not None else None,
        exif_summary=doc.exif_summary,
    )
