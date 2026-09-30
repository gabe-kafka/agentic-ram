"""Minimal requests-compatible HTTP POST used by RAM Concept's local API.

RAM Concept's Python package only uses requests.post(), response.text,
and response.raise_for_status(). Keeping this adapter local avoids adding a
machine-wide Python dependency for the localhost-only API connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass
class Response:
    status_code: int
    text: str
    reason: str = ""

    def raise_for_status(self) -> None:
        if 400 <= self.status_code:
            raise RuntimeError(
                f"HTTP {self.status_code}: {self.reason or self.text}"
            )


def post(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    data: bytes | None = None,
    timeout: float | None = None,
) -> Response:
    request = Request(
        url,
        data=data,
        headers=dict(headers or {}),
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as result:
            body = result.read().decode("utf-8")
            return Response(
                status_code=result.status,
                text=body,
                reason=getattr(result, "reason", ""),
            )
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return Response(
            status_code=error.code,
            text=body,
            reason=str(error.reason),
        )
