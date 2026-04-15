"""Structured logging + request-id middleware.

Every request gets a ``request_id`` (from the ``X-Request-ID`` header or a
freshly-generated ``uuid4``). The id is exposed via a ``contextvars.ContextVar``
so any log statement inside the request produces a line tagged with the same
id, and is returned in the response as ``X-Request-ID`` for client-side
correlation.

Log format is plain key=value (not JSON) to stay readable in a terminal
without sacrificing machine-parseability. Switch to JSON later by swapping
the formatter if you need it.
"""

from __future__ import annotations

import contextvars
import logging
import sys
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


def current_request_id() -> str:
    return _request_id_var.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Install a root logger formatted as `time level rid=... logger: msg`.

    Idempotent — safe to call multiple times at process start.
    """
    root = logging.getLogger()
    # Wipe existing handlers so our config wins
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-5s rid=%(request_id)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(fmt)
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(level)
    # Keep uvicorn access noise down a notch
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign or propagate an X-Request-ID on every request + log timing."""

    def __init__(self, app, logger_name: str = "smartbaseai.http") -> None:
        super().__init__(app)
        self._log = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        token = _request_id_var.set(rid)
        start = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            path = request.url.path
            if path not in ("/docs", "/openapi.json", "/redoc") and not path.startswith(
                "/static"
            ):
                self._log.info(
                    "%s %s -> %s (%.1fms)",
                    request.method,
                    path,
                    status,
                    elapsed_ms,
                )
            _request_id_var.reset(token)
