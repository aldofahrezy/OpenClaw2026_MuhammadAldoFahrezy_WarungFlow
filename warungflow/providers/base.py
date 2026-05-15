from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PaymentProvider(ABC):
    """Adapter-first payment integration."""

    @abstractmethod
    def create_payment_request(
        self, order_id: str, amount: int, description: str
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    def check_payment_status(self, request_id: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def list_transactions(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def simulate_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...
