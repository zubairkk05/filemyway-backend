"""cPanel / Phusion Passenger entry point for the FileMyWay backend.

Passenger (via LiteSpeed's ``lswsgi``) only speaks WSGI, while FastAPI is ASGI.
Wrapping the app with ``a2wsgi.ASGIMiddleware`` hangs under ``lswsgi`` -- the
request never returns and the child process is killed with ``SIGTERM`` -- so we
bridge ASGI to WSGI ourselves: each request runs the coroutine synchronously in
the request thread via ``asyncio.run`` and buffers the response body as a *list
of chunks* (never a second concatenated copy).

Why ``receive()`` blocks
------------------------
Starlette's ``FileResponse`` starts a ``listen_for_disconnect(receive)`` loop
next to the file stream. If ``receive()`` returned ``{"type": "http.request"}``
on every call, that loop would spin without ever yielding, starving the event
loop -- the download hangs and the worker burns CPU until killed. Instead we
deliver the request body exactly once and then *block* on an ``asyncio.Event``
created per request (``asyncio.run`` installs a new event loop each call, so the
event must not live at module scope). Starlette cancels the blocked listener
when the response finishes, or it returns ``http.disconnect`` once the final
body chunk has been sent.

Trade-off: responses are buffered in memory rather than streamed over WSGI.
Peak RAM per in-flight response is about the size of one output file; per-tool
caps live in ``app/core/tool_registry.py`` (up to ``max_total_mb``). With
``CONCURRENCY`` simultaneous downloads that is the worst-case memory ceiling.

cPanel -> "Setup Python App" settings::

    Application startup file:  passenger_wsgi.py
    Application Entry point:   application

Reminder: re-saving the cPanel Python App screen regenerates this file from a
template. Always run ``git checkout -- passenger_wsgi.py`` before/after a
``git pull`` (or after touching the cPanel UI) and then restart the app.
"""

import asyncio
import sys
from pathlib import Path

# Passenger may run with a different CWD; make the ``app`` package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # ``resource`` is POSIX-only; guard so the module also imports on Windows.
    import resource  # noqa: F401
except ImportError:  # pragma: no cover - Windows dev only
    resource = None  # type: ignore[assignment]

# The in-process worker sets RLIMIT_AS on import; never let it throttle the web
# process (it also breaks Passenger's spawn handshake). No-op where unavailable.
if resource is not None:
    resource.setrlimit = lambda *args, **kwargs: None  # type: ignore[assignment]

from app.main import app as _asgi_app  # noqa: E402

_REASONS = {
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    206: "Partial Content",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    413: "Payload Too Large",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def _scope_from_environ(environ: dict) -> dict:
    headers = []
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            headers.append(
                (
                    key[5:].replace("_", "-").lower().encode("latin-1"),
                    str(value).encode("latin-1"),
                )
            )
        elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            headers.append(
                (
                    key.replace("_", "-").lower().encode("latin-1"),
                    str(value).encode("latin-1"),
                )
            )
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": environ.get("SERVER_PROTOCOL", "HTTP/1.1").split("/")[-1],
        "method": environ.get("REQUEST_METHOD", "GET").upper(),
        "scheme": environ.get("wsgi.url_scheme", "http"),
        "path": environ.get("PATH_INFO", "/") or "/",
        "raw_path": (environ.get("PATH_INFO", "/") or "/").encode("latin-1"),
        "query_string": environ.get("QUERY_STRING", "").encode("latin-1"),
        "root_path": environ.get("SCRIPT_NAME", ""),
        "headers": headers,
        "client": (environ.get("REMOTE_ADDR", "127.0.0.1"), 0),
        "server": (
            environ.get("SERVER_NAME", "localhost"),
            int(environ.get("SERVER_PORT") or 80),
        ),
    }


def application(environ, start_response):
    """Run the ASGI app for a single WSGI request and return the buffered body."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    body = environ["wsgi.input"].read(length) if length > 0 else b""

    scope = _scope_from_environ(environ)
    captured = {"status": 500, "headers": [], "body": []}

    # Per-request state: ``asyncio.run`` builds a fresh event loop every call, so
    # these must be created here (never at module scope).
    request_delivered = False
    response_done = asyncio.Event()

    async def receive():
        nonlocal request_delivered
        if not request_delivered:
            request_delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        # Body already delivered: block (yield to the loop) until the response
        # finishes, instead of returning immediately and spinning.
        await response_done.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            captured["status"] = message["status"]
            # Preserve order and duplicates (e.g. several Set-Cookie headers).
            captured["headers"] = [
                (
                    k.decode("latin-1") if isinstance(k, bytes) else str(k),
                    v.decode("latin-1") if isinstance(v, bytes) else str(v),
                )
                for k, v in message.get("headers", [])
            ]
        elif message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                captured["body"].append(chunk)
            if not message.get("more_body", False):
                # Final chunk: release the disconnect listener cleanly.
                response_done.set()

    try:
        asyncio.run(_asgi_app(scope, receive, send))
    except Exception as exc:  # noqa: BLE001 - surface any boot/runtime failure
        import traceback

        traceback.print_exc()
        start_response(
            "500 Internal Server Error",
            [("Content-Type", "text/plain; charset=utf-8")],
        )
        return [f"Internal Server Error: {exc}".encode("utf-8")]

    status = captured["status"]
    start_response(f"{status} {_REASONS.get(status, 'OK')}", captured["headers"])
    # The body is already a list of bytes chunks; hand it straight to the server
    # so we never build a second concatenated copy.
    return captured["body"] or [b""]
