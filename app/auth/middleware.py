import json
import logging
import time
import uuid

from fastapi import Request
from starlette.concurrency import iterate_in_threadpool

from app.core.logging_ctx import request_id_var, user_var

log = logging.getLogger("access")

HEADER = "X-Request-ID"
USER_HEADER = "X-User"
SENSITIVE = {"password", "parola", "token", "secret", "access_token", "authorization"}
MAX_LEN = 2000


def _safe(raw: bytes):
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return raw[:MAX_LEN].decode("utf-8", "replace")
    if isinstance(data, dict):
        data = {k: ("***" if k.lower() in SENSITIVE else v) for k, v in data.items()}
    out = json.dumps(data, ensure_ascii=False)
    return out[:MAX_LEN] + ("…" if len(out) > MAX_LEN else "")


async def request_context(request: Request, call_next):
    rid = request.headers.get(HEADER) or uuid.uuid4().hex[:16]
    user = request.headers.get(USER_HEADER) or "anonymous"
    token = request_id_var.set(rid)
    user_token = user_var.set(user)
    start = time.perf_counter()

    body = await request.body()
    request._body = body

    try:
        response = await call_next(request)
        response.headers[HEADER] = rid

        chunks = [c async for c in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(chunks))

        log.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "user": user,
                "payload": _safe(body),
                "response": _safe(b"".join(chunks)),
            },
        )
        return response
    except Exception:
        log.exception(
            "http_error",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "user": user,
                "payload": _safe(body),
            },
        )
        raise
    finally:
        request_id_var.reset(token)
        user_var.reset(user_token)