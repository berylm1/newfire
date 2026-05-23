"""
OpenClaw v1 entrypoint.

Startup posture check:
  - If neither openclaw_dev_email nor cf_access_aud is set, refuse to start.
"""
import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_pool, close_pool
from .routes import health, whoami, dispatch, runs

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("openclaw")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.openclaw_dev_email and not settings.cf_access_aud:
        log.error("REFUSING TO START: neither OPENCLAW_DEV_EMAIL nor CF_ACCESS_AUD is set.")
        sys.exit(2)
    if settings.openclaw_dev_email:
        log.warning("DEV MODE: JWT bypass active, all requests authenticate as %s",
                    settings.openclaw_dev_email)
    await init_pool()
    log.info("OpenClaw v1 ready on port %d", settings.service_port)
    yield
    await close_pool()


app = FastAPI(
    title="OpenClaw v1",
    description="Junior dev coordinator: classify, execute, report.",
    version="1.0.0-pr2",
    lifespan=lifespan,
)

# API routes
app.include_router(health.router, tags=["health"])
app.include_router(whoami.router, tags=["identity"])
app.include_router(dispatch.router, tags=["dispatch"])
app.include_router(runs.router, tags=["runs"])

# Static UI: serve index.html at / and any static asset at /static/*
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root_ui() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api", include_in_schema=False)
async def api_info() -> dict:
    return {
        "service": "openclaw",
        "version": "1.0.0-pr2",
        "docs": "/docs",
        "ui": "/",
        "health": "/v1/health",
    }
