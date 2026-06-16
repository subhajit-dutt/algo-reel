"""Serve the Next.js static export and SPA-fallback to index.html for unknown paths.

The frontend is built with `output: 'export'` which produces `frontend/out/`. That tree
contains an `index.html` plus hashed `_next/` assets. Because there is no SSR, all
"routes" (e.g. `/videos/42/`) resolve client-side from the same `index.html`. So any
unknown GET that didn't match an API route should return `index.html` (200), not 404.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.logging import get_logger

_FRONTEND_OUT = Path(__file__).resolve().parent.parent / "frontend" / "out"
_log = get_logger(__name__)


class _SpaStaticFiles(StaticFiles):
    """StaticFiles that falls back to /index.html for any missing path.

    This is what makes deep links like `/videos/42/` work under a static export.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            index = Path(self.directory) / "index.html" if self.directory else None
            if index and index.is_file():
                return FileResponse(index)
            raise


def mount_frontend(app: FastAPI) -> None:
    """Mount the static SPA at `/`. Call after all API routers are registered."""
    if not _FRONTEND_OUT.is_dir():
        _log.warning("frontend.mount.skipped", path=str(_FRONTEND_OUT))
        return

    app.mount("/", _SpaStaticFiles(directory=str(_FRONTEND_OUT), html=True), name="frontend")
    _log.info("frontend.mounted", path=str(_FRONTEND_OUT))
