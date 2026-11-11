from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError


@dataclass(frozen=True)
class PayoutLineItem:
    role: str
    recipient_email: str
    amount: Decimal


@dataclass(frozen=True)
class PaymentResult:
    provider: str
    success: bool
    external_id: str | None
    request_summary: dict[str, Any]
    response_summary: dict[str, Any]


class PaymentAdapter(ABC):
    @abstractmethod
    def pay(
        self,
        *,
        settlement_id: int,
        currency: str,
        lines: list[PayoutLineItem],
        idempotency_key: str,
    ) -> PaymentResult:
        raise NotImplementedError


class MockPaymentProvider(PaymentAdapter):
    def __init__(self, *, force_fail: bool = False) -> None:
        self.force_fail = force_fail

    def pay(
        self,
        *,
        settlement_id: int,
        currency: str,
        lines: list[PayoutLineItem],
        idempotency_key: str,
    ) -> PaymentResult:
        req_summary = {
            "settlement_id": settlement_id,
            "currency": currency,
            "idempotency_key": idempotency_key,
            "items": [
                {
                    "role": line.role,
                    "recipient_email": line.recipient_email,
                    "amount": f"{line.amount:.2f}",
                }
                for line in lines
                if line.amount > Decimal("0.00")
            ],
        }
        if self.force_fail:
            return PaymentResult(
                provider="mock",
                success=False,
                external_id=None,
                request_summary=req_summary,
                response_summary={"status": "FAILED", "reason": "Simulated provider error"},
            )
        external_id = f"MOCK-BATCH-{settlement_id}-{idempotency_key[:12]}"
        return PaymentResult(
            provider="mock",
            success=True,
            external_id=external_id,
            request_summary=req_summary,
            response_summary={"status": "SUCCESS", "batch_id": external_id},
        )


class PayPalSandboxAdapter(PaymentAdapter):
    def __init__(
        self, *, client_id: str, client_secret: str, base_url: str
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")

    def _fetch_access_token(self) -> str:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    def pay(
        self,
        *,
        settlement_id: int,
        currency: str,
        lines: list[PayoutLineItem],
        idempotency_key: str,
    ) -> PaymentResult:
        items = [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": f"{line.amount:.2f}", "currency": currency},
                "receiver": line.recipient_email,
                "note": f"PCMSC parametric settlement #{settlement_id} ({line.role})",
                "sender_item_id": f"s{settlement_id}-{line.role}-{idempotency_key[:16]}",
            }
            for line in lines
            if line.amount > Decimal("0.00")
        ]
        body = {
            "sender_batch_header": {
                "sender_batch_id": f"pcmsc-{settlement_id}-{idempotency_key[:24]}",
                "email_subject": "PCMSC Parametric Climate Payout",
            },
            "items": items,
        }
        req_summary = {
            "settlement_id": settlement_id,
            "currency": currency,
            "paypal_request_id": idempotency_key,
            "item_count": len(items),
        }
        try:
            token = self._fetch_access_token()
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    f"{self.base_url}/v1/payments/payouts",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "PayPal-Request-Id": idempotency_key,
                    },
                )
            data = resp.json()
            if resp.status_code in {200, 201}:
                batch_id = data.get("batch_header", {}).get("payout_batch_id")
                return PaymentResult(
                    provider="paypal",
                    success=True,
                    external_id=batch_id,
                    request_summary=req_summary,
                    response_summary={
                        "status_code": resp.status_code,
                        "payout_batch_id": batch_id,
                    },
                )
            return PaymentResult(
                provider="paypal",
                success=False,
                external_id=None,
                request_summary=req_summary,
                response_summary={"status_code": resp.status_code, "error": data},
            )
        except Exception as exc:
            return PaymentResult(
                provider="paypal",
                success=False,
                external_id=None,
                request_summary=req_summary,
                response_summary={"error": str(exc)},
            )


def get_payment_adapter() -> PaymentAdapter:
    settings = get_settings()
    if settings.payment_provider == "paypal":
        if not (settings.paypal_client_id and settings.paypal_client_secret):
            raise AppError(
                "PayPal sandbox credentials are required when PAYMENT_PROVIDER=paypal",
                code="configuration_error",
                status_code=500,
            )
        return PayPalSandboxAdapter(
            client_id=settings.paypal_client_id,
            client_secret=settings.paypal_client_secret,
            base_url=settings.paypal_base_url,
        )
    return MockPaymentProvider()

