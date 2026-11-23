"""Fall Detection backend (FastAPI). Run:  python -m falldet.serve"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from falldet import auth, config
from falldet.api import routes_auth, routes_cameras, routes_incidents, routes_misc, routes_ws
from falldet.core import logging_setup, schema
from falldet.runtime import runtime

log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(_app):
    logging_setup.setup()
    schema.init_db()
    auth.bootstrap_from_env()
    auth.purge_expired()
    if config.RUN_DETECTION:
        runtime.start()
    log.info("fall detection backend up on %s:%s (detection %s)", config.HOST, config.PORT,
             "on" if config.RUN_DETECTION else "OFF")
    try:
        yield
    finally:
        log.info("shutting down")
        runtime.stop()


app = FastAPI(title="Fall Detection", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server."})


for r in (routes_auth.router, routes_cameras.router, routes_incidents.router, routes_misc.router,
          routes_misc.public, routes_ws.router):
    app.include_router(r)

# Optional single-port deployment: serve the built frontend (frontend/dist) if present.
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = (_DIST / path).resolve()
        if path and _DIST.resolve() in target.parents and target.is_file():
            return FileResponse(target)
        return FileResponse(_DIST / "index.html")
