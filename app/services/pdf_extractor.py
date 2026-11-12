import io
import re
import zlib
from pathlib import Path

from app.core.errors import AppError

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - optional until owner runs pip install
    fitz = None


class PdfExtractorService:
    @staticmethod
    def is_encrypted_pdf(raw_bytes: bytes) -> bool:
        if b"/Encrypt" in raw_bytes:
            return True
        if fitz is not None:
            try:
                with fitz.open(stream=raw_bytes, filetype="pdf") as doc:
                    return bool(doc.needs_pass or doc.is_encrypted)
            except Exception as exc:
                raise AppError(
                    "Corrupted or unreadable PDF document",
                    code="invalid_pdf",
                    status_code=400,
                ) from exc
        return False

    @staticmethod
    def extract_text(file_path: Path) -> str:
        raw_bytes = file_path.read_bytes()
        if PdfExtractorService.is_encrypted_pdf(raw_bytes):
            raise AppError(
                "Encrypted PDFs are not accepted",
                code="encrypted_pdf",
                status_code=400,
            )
        if fitz is not None:
            try:
                with fitz.open(str(file_path)) as doc:
                    pages = [page.get_text("text") for page in doc]
                    return "\n".join(pages).strip()
            except Exception as exc:
                raise AppError(
                    "Failed to parse PDF document",
                    code="invalid_pdf",
                    status_code=400,
                ) from exc

        # Lightweight fallback text scan when PyMuPDF is not installed yet
        chunks: list[str] = []
        for stream_match in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.S):
            stream_data = stream_match.group(1)
            try:
                stream_data = zlib.decompress(stream_data)
            except Exception:
                pass
            for text_match in re.finditer(rb"\(([^()]{1,400})\)\s*Tj", stream_data):
                chunks.append(text_match.group(1).decode("latin-1", errors="ignore"))
        if not chunks:
            for literal in re.finditer(rb"\(([^()]{2,400})\)", raw_bytes):
                decoded = literal.group(1).decode("latin-1", errors="ignore")
                if any(ch.isalpha() for ch in decoded):
                    chunks.append(decoded)
        return "\n".join(chunks).strip()

    @staticmethod
    def render_pages_as_png(file_path: Path, *, max_pages: int = 5) -> list[bytes]:
        if fitz is None:
            # Return empty list if PyMuPDF is not installed yet
            return []
        images: list[bytes] = []
        try:
            with fitz.open(str(file_path)) as doc:
                if doc.needs_pass or doc.is_encrypted:
                    raise AppError(
                        "Encrypted PDFs are not accepted",
                        code="encrypted_pdf",
                        status_code=400,
                    )
                for idx, page in enumerate(doc):
                    if idx >= max_pages:
                        break
                    pix = page.get_pixmap(dpi=150)
                    images.append(pix.tobytes("png"))
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                "Failed to render PDF pages",
                code="invalid_pdf",
                status_code=400,
            ) from exc
        return images
