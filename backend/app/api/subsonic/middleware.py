"""
ASGI middleware for Subsonic API compatibility.

Historically Subsonic endpoints carry a ``.view`` suffix (``/rest/ping.view``),
but the suffix is optional in the spec and several OpenSubsonic clients call the
bare form (``/rest/ping``). The handlers only register the ``.view`` routes, so
bare calls would hit the catch-all and 404.

This middleware rewrites a bare ``/rest/<endpoint>`` request path to
``/rest/<endpoint>.view`` before routing, so both forms work with no per-route
duplication. Paths whose last segment already contains a dot (``.view``, static
assets, etc.) are left untouched.
"""

from starlette.types import ASGIApp, Receive, Scope, Send


class SubsonicViewSuffixMiddleware:
    """Append the optional ``.view`` suffix to bare ``/rest`` endpoints."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path.startswith("/rest/"):
                last_segment = path.rsplit("/", 1)[-1]
                if last_segment and "." not in last_segment:
                    new_path = path + ".view"
                    scope = dict(scope)
                    scope["path"] = new_path
                    if scope.get("raw_path") is not None:
                        # raw_path excludes the query string; re-encode the new path
                        scope["raw_path"] = new_path.encode()
        await self.app(scope, receive, send)
