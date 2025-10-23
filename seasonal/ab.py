from __future__ import annotations

import hashlib
from typing import Optional


def bucket_user(request, *, salt: Optional[str] = None) -> int:
    """
    Produce a stable bucket (0-99) for request based on sid cookie or UA+IP.
    """
    identifier = _identifier_from_request(request)
    if salt:
        identifier = f"{salt}:{identifier}"
    digest = hashlib.sha1(identifier.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _identifier_from_request(request) -> str:
    if request is None:
        return "anonymous"

    cookies = getattr(request, "COOKIES", {}) or {}
    sid = cookies.get("sid")
    if sid:
        return f"sid:{sid}"

    meta = getattr(request, "META", {}) or {}
    user_agent = meta.get("HTTP_USER_AGENT", "unknown")
    ip = meta.get("REMOTE_ADDR", "unknown")
    return f"ua:{user_agent}|ip:{ip}"

