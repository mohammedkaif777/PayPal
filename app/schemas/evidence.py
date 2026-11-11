from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

DocType = Literal["BILL_OF_LADING", "INSPECTION_REPORT", "PHOTO", "OTHER"]


class EvidenceDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    doc_type: str
    original_filename: str
    sha256: str
    storage_path: str
    mime_type: str
    file_size: int
    extracted_text: str | None
    perceptual_hash: str | None
    blur_score: float | None
    blur_passed: bool | None
    exif_summary: dict[str, Any] | None
    uploaded_at: datetime


class EvidenceExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    provider: str
    model_name: str
    prompt_version: str
    extracted_fields: dict[str, Any]
    confidence: float
    raw_response: dict[str, Any]
    extracted_at: datetime


class ImageQCResponse(BaseModel):
    document_id: int
    blur_score: float | None
    blur_passed: bool | None
    perceptual_hash: str | None
    duplicate_of_document_id: int | None
    exif_summary: dict[str, Any] | None
