"""Firefly III API client — wraps the v1 REST API for transaction sync."""
from __future__ import annotations
from typing import Any, Dict
import requests


class FireflyAuthError(Exception):
    """Raised when the API returns HTTP 401."""


class FireflyValidationError(Exception):
    """Raised when the API returns HTTP 422 (invalid payload)."""


class FireflyApiClient:
    """Thin client for Firefly III REST API v1.

    Args:
        base_url: Base URL of the Firefly instance, e.g. ``http://firefly.local``
        token: Personal Access Token from Firefly III → Profile → OAuth
    """

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def post_transaction(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """POST a single transaction to Firefly III.

        Args:
            txn: Dict with Firefly transaction fields

        Returns:
            Parsed JSON response from the API.

        Raises:
            FireflyAuthError: On HTTP 401.
            FireflyValidationError: On HTTP 422.
            requests.HTTPError: On any other non-2xx response.
        """
        url = f"{self.base_url}/api/v1/transactions"
        payload = {"transactions": [txn]}
        response = requests.post(url, json=payload, headers=self._headers())

        if response.status_code == 401:
            raise FireflyAuthError("Invalid Firefly token — check your Personal Access Token.")
        if response.status_code == 422:
            detail = response.json().get("message", "Validation error")
            raise FireflyValidationError(f"Firefly rejected transaction: {detail}")
        response.raise_for_status()
        return response.json()
