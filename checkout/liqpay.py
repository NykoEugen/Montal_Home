import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from django.conf import settings


class LiqPayConfigurationError(RuntimeError):
    """Raised when LiqPay credentials are missing."""


class LiqPaySignatureMismatch(RuntimeError):
    """Raised when LiqPay callback signature cannot be verified."""


def _require_credentials() -> Tuple[str, str]:
    public = getattr(settings, "LIQPAY_PUBLIC_KEY", "") or ""
    private = getattr(settings, "LIQPAY_PRIVATE_KEY", "") or ""
    if not public or not private:
        raise LiqPayConfigurationError("LiqPay credentials are not configured")
    return public, private


@dataclass(slots=True)
class LiqPayClient:
    """
    Minimal LiqPay helper that mirrors the official liqpay-python-sdk behaviour.

    The SDK simply base64-encodes the payload JSON and signs it via
    SHA1(private_key + data + private_key), so we replicate the same logic here
    to avoid an extra runtime dependency.
    """

    public_key: str
    private_key: str

    def _encode(self, payload: Dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return base64.b64encode(data.encode("utf-8")).decode("ascii")

    def _signature(self, data: str) -> str:
        raw = f"{self.private_key}{data}{self.private_key}".encode("utf-8")
        digest = hashlib.sha1(raw).digest()
        return base64.b64encode(digest).decode("ascii")

    def build_checkout(self, params: Dict[str, Any]) -> Tuple[str, str]:
        """Attach defaults, encode payload and return (data, signature)."""
        payload = {
            "public_key": self.public_key,
            "version": getattr(settings, "LIQPAY_API_VERSION", "3"),
            **params,
        }
        data = self._encode(payload)
        sign = self._signature(data)
        return data, sign

    def decode(self, data: str, signature: str) -> Dict[str, Any]:
        """Verify callback payload and return parsed JSON."""
        expected = self._signature(data)
        if signature != expected:
            raise LiqPaySignatureMismatch("Callback signature is invalid")
        decoded = base64.b64decode(data).decode("utf-8")
        return json.loads(decoded)


def get_liqpay_client() -> LiqPayClient:
    public, private = _require_credentials()
    return LiqPayClient(public_key=public, private_key=private)
