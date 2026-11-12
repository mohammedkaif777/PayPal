from typing import Any

import httpx


class ApiClientError(Exception):
    def __init__(self, status_code: int, message: str, details: Any = None) -> None:
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"[{status_code}] {message}")


class PCMSCApiClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "demo-admin-key",
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code >= 400:
            try:
                err = resp.json().get("error", {})
                raise ApiClientError(
                    resp.status_code,
                    err.get("message", resp.text),
                    err.get("details"),
                )
            except ValueError as exc:
                raise ApiClientError(resp.status_code, resp.text) from exc
        return resp.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def ready(self) -> dict[str, Any]:
        return self._request("GET", "/ready")

    def me(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/auth/me")

    def list_parties(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/parties")

    def list_shipments(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/shipments")

    def get_shipment(self, shipment_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/shipments/{shipment_id}")

    def list_policies(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/policies")

    def list_telemetry(self, shipment_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/telemetry/shipment/{shipment_id}")

    def list_violations(self, shipment_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/monitoring/violations/{shipment_id}")

    def list_evidence(self, shipment_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/evidence/shipment/{shipment_id}")

    def list_extractions(self, document_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/evidence/{document_id}/extractions")

    def list_fraud_signals(self, shipment_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/fraud/signals/{shipment_id}")

    def list_verifications(self, shipment_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/fraud/verifications/{shipment_id}")

    def list_claims(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/claims")

    def get_claim(self, claim_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/claims/{claim_id}")

    def review_claim(
        self, claim_id: int, *, decision: str, notes: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/claims/{claim_id}/review",
            json={"decision": decision, "notes": notes},
        )

    def get_settlement_by_claim(self, claim_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/settlements/claim/{claim_id}")

    def list_payouts(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/payouts")

    def retry_payout(self, payout_id: int) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/payouts/{payout_id}/retry")

    def list_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/audit?limit={limit}")

    def run_scenario(self, scenario: str, seed: int = 101) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/scenarios/run",
            json={"scenario": scenario, "seed": seed},
        )

