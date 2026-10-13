"""FastAPI application entrypoint for the cars-zeekr API."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin import ensure_admin_user, setup_admin
from app.api import (
    auth,
    catalog,
    catalog_meta,
    health,
    home,
    leads,
    parts,
    profile,
)
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Behind a reverse proxy the socket peer is the proxy, so with trust_proxy
    # off every request shares one IP and the login/lead rate limits become
    # global — a few requests can 429 the whole site. Warn loudly in prod.
    if settings.app_env != "dev" and not settings.trust_proxy:
        logger.warning(
            "TRUST_PROXY is off in a non-dev env: rate limits will key on the "
            "socket peer (the proxy IP if deployed behind one). Set TRUST_PROXY=true "
            "only if your proxy overwrites X-Forwarded-For."
        )

    # Provision the admin account from settings (no-op when unset). A transient
    # DB blip here shouldn't take the whole API down — log and continue serving.
    try:
        await ensure_admin_user()
    except Exception:  # noqa: BLE001
        logger.exception("Admin bootstrap failed; continuing startup")
    yield


app = FastAPI(title="cars-zeekr API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(catalog_meta.router)
app.include_router(parts.router)
app.include_router(home.router)
app.include_router(leads.router)
app.include_router(profile.router)

# SQLAdmin panel at /admin (issue #18).
setup_admin(app)
