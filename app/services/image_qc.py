import io
from typing import Any

import numpy as np
from PIL import ExifTags, Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceDocument

try:
    import cv2
except ImportError:  # pragma: no cover - optional until owner runs pip install
    cv2 = None


class ImageQCService:
    @staticmethod
    def check_blur(
        image_bytes: bytes, *, threshold: float = 50.0
    ) -> tuple[bool, float]:
        if cv2 is not None:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                variance = float(cv2.Laplacian(img, cv2.CV_64F).var())
                return variance >= threshold, round(variance, 2)

        with Image.open(io.BytesIO(image_bytes)) as img:
            gray = np.asarray(img.convert("L"), dtype=np.float64)
        if gray.shape[0] < 3 or gray.shape[1] < 3:
            return False, 0.0
        # 3x3 discrete Laplacian kernel: [0,1,0; 1,-4,1; 0,1,0]
        lap = (
            gray[:-2, 1:-1]
            + gray[2:, 1:-1]
            + gray[1:-1, :-2]
            + gray[1:-1, 2:]
            - 4.0 * gray[1:-1, 1:-1]
        )
        variance = float(np.var(lap))
        return variance >= threshold, round(variance, 2)

    @staticmethod
    def extract_exif(image_bytes: bytes) -> dict[str, Any]:
        with Image.open(io.BytesIO(image_bytes)) as img:
            exif_data = img.getexif()
            result: dict[str, Any] = {
                "format": img.format,
                "width": img.width,
                "height": img.height,
                "tags": {},
            }
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    result["tags"][tag_name] = str(value)[:128]
            return result

    @staticmethod
    def compute_perceptual_hash(image_bytes: bytes) -> str:
        """Compute 64-bit difference hash (dHash) as a 16-char hex string."""
        with Image.open(io.BytesIO(image_bytes)) as img:
            resized = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = np.asarray(resized, dtype=np.int16)
        diff = pixels[:, 1:] > pixels[:, :-1]
        bits = 0
        for val in diff.flatten():
            bits = (bits << 1) | int(bool(val))
        return f"{bits:016x}"

    @staticmethod
    def hamming_distance(hash_a: str, hash_b: str) -> int:
        return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()

    @staticmethod
    def find_duplicate_document(
        db: Session,
        *,
        sha256: str,
        perceptual_hash: str | None,
        exclude_doc_id: int | None = None,
        max_hamming_distance: int = 5,
    ) -> EvidenceDocument | None:
        stmt = select(EvidenceDocument)
        if exclude_doc_id is not None:
            stmt = stmt.where(EvidenceDocument.id != exclude_doc_id)
        candidates = db.scalars(stmt).all()
        for doc in candidates:
            if doc.sha256 == sha256:
                return doc
            if (
                perceptual_hash
                and doc.perceptual_hash
                and ImageQCService.hamming_distance(perceptual_hash, doc.perceptual_hash)
                <= max_hamming_distance
            ):
                return doc
        return None
