import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import AppError

FORBIDDEN_OBSERVATION_KEYS = {
    "claim",
    "claims",
    "claim_status",
    "approved",
    "rejected",
    "settlement",
    "payout",
    "payment",
    "authorize_payment",
}


@dataclass(frozen=True)
class ExtractionResult:
    provider: str
    model_name: str
    prompt_version: str
    fields: dict[str, Any]
    confidence: float
    raw_response: dict[str, Any]


def sanitize_observation_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Trust boundary: AI providers only produce observations, never claim/payment decisions."""
    cleaned: dict[str, Any] = {}
    for key, value in fields.items():
        if key.lower() in FORBIDDEN_OBSERVATION_KEYS:
            continue
        cleaned[key] = value
    return cleaned


class AIProvider(ABC):
    @abstractmethod
    def extract(
        self,
        *,
        document_path: Path,
        doc_type: str,
        extracted_text: str = "",
    ) -> ExtractionResult:
        raise NotImplementedError


class MockAIProvider(AIProvider):
    PROMPT_VERSION = "mock-v1.0"

    @staticmethod
    def _extract_token(text: str, label: str, default: str) -> str:
        pattern = rf"{re.escape(label)}\s*:\s*([^\r\n]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return default

    def extract(
        self,
        *,
        document_path: Path,
        doc_type: str,
        extracted_text: str = "",
    ) -> ExtractionResult:
        if doc_type == "BILL_OF_LADING":
            fields = {
                "shipment_ref": self._extract_token(
                    extracted_text, "ShipmentRef", "UNKNOWN"
                ),
                "shipper": self._extract_token(
                    extracted_text, "Shipper", "AgriFresh Farms Ltd"
                ),
                "consignee": self._extract_token(
                    extracted_text, "Consignee", "EuroCold Imports GmbH"
                ),
                "vessel": self._extract_token(
                    extracted_text, "Vessel", "MV Pacific Breeze"
                ),
                "port_of_loading": self._extract_token(
                    extracted_text, "OriginPort", "Mumbai"
                ),
                "port_of_discharge": self._extract_token(
                    extracted_text, "DestinationPort", "Rotterdam"
                ),
                "commodity": self._extract_token(
                    extracted_text, "Commodity", "Fresh Mangoes"
                ),
                "document_date": self._extract_token(
                    extracted_text, "DocumentDate", "2026-11-01T00:00:00Z"
                ),
                "quantity": self._extract_token(
                    extracted_text, "Quantity", "1200 crates"
                ),
                "weight_kg": self._extract_token(
                    extracted_text, "WeightKg", "14400"
                ),
            }
            confidence = 0.94
        elif doc_type == "INSPECTION_REPORT":
            fields = {
                "shipment_ref": self._extract_token(
                    extracted_text, "ShipmentRef", "UNKNOWN"
                ),
                "inspector": self._extract_token(
                    extracted_text, "Inspector", "SGS Cold-Chain Inspection"
                ),
                "document_date": self._extract_token(
                    extracted_text, "DocumentDate", "2026-11-02T12:00:00Z"
                ),
                "condition": self._extract_token(
                    extracted_text, "Condition", "Heat stress observed"
                ),
                "observed_temperature_c": self._extract_token(
                    extracted_text, "ObservedTempC", "11.2"
                ),
                "observed_humidity_pct": self._extract_token(
                    extracted_text, "ObservedHumidityPct", "69.0"
                ),
                "damage_notes": self._extract_token(
                    extracted_text,
                    "DamageNotes",
                    "Spoilage detected in upper pallet tier",
                ),
            }
            confidence = 0.91
        elif doc_type == "PHOTO":
            fields = {
                "scene_type": "cargo_container_interior",
                "visible_spoilage": True,
                "condensation_present": True,
                "seal_intact": True,
                "notes": f"Visual observation from {document_path.name}",
            }
            confidence = 0.88
        else:
            fields = {
                "summary": f"Observed document {document_path.name}",
                "shipment_ref": self._extract_token(
                    extracted_text, "ShipmentRef", "UNKNOWN"
                ),
            }
            confidence = 0.80

        safe_fields = sanitize_observation_fields(fields)
        return ExtractionResult(
            provider="mock",
            model_name="deterministic-mock-v1",
            prompt_version=self.PROMPT_VERSION,
            fields=safe_fields,
            confidence=confidence,
            raw_response={"observations": safe_fields, "confidence": confidence},
        )


class GeminiAIProvider(AIProvider):
    PROMPT_VERSION = "gemini-v1.0"

    def __init__(self, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def extract(
        self,
        *,
        document_path: Path,
        doc_type: str,
        extracted_text: str = "",
    ) -> ExtractionResult:
        try:
            from google import genai
        except ImportError as exc:
            raise AppError(
                "google-genai package is required when AI_PROVIDER=gemini",
                code="missing_dependency",
                status_code=500,
            ) from exc

        client = genai.Client(api_key=self.api_key)
        prompt = (
            f"PromptVersion: {self.PROMPT_VERSION}\n"
            f"Extract structured factual observations ONLY for document type {doc_type}. "
            "Return valid JSON with keys 'fields' (object) and 'confidence' (float 0-1). "
            "Do NOT include any claim approval, settlement, or payment recommendations.\n\n"
            f"Text:\n{extracted_text[:6000]}"
        )
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        raw_text = response.text or "{}"
        parsed = json.loads(raw_text)
        fields = sanitize_observation_fields(parsed.get("fields", {}))
        confidence = float(parsed.get("confidence", 0.75))
        return ExtractionResult(
            provider="gemini",
            model_name=self.model_name,
            prompt_version=self.PROMPT_VERSION,
            fields=fields,
            confidence=max(0.0, min(1.0, confidence)),
            raw_response=parsed,
        )


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "gemini":
        if not settings.gemini_api_key:
            raise AppError(
                "GEMINI_API_KEY is required when AI_PROVIDER=gemini",
                code="configuration_error",
                status_code=500,
            )
        return GeminiAIProvider(
            api_key=settings.gemini_api_key, model_name=settings.gemini_model
        )
    return MockAIProvider()
