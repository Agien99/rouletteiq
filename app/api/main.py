from app.api.auth_guard import roulette_ownership_middleware
from app.api.routers.account_security import router as security_router
from app.api.routers.google_oauth import router as google_router
from app.api.routers.recovery import router as recovery_router
from app.api.routers.auth import (
    router as auth_router,
)
from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.config import settings
from app.api.errors import (
    register_exception_handlers,
)
from app.api.logging import (
    configure_logging,
    request_logging_middleware,
)
from app.api.routers.health import (
    router as health_router,
)
from app.api.routers.models import (
    router as models_router,
)
from app.api.routers.sessions import (
    router as sessions_router,
)


configure_logging(
    settings.log_level
)


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url=(
        "/docs"
        if settings.docs_enabled
        else None
    ),
    redoc_url=(
        "/redoc"
        if settings.docs_enabled
        else None
    ),
    openapi_url=(
        "/openapi.json"
        if settings.docs_enabled
        else None
    ),
)


app.middleware("http")(
    request_logging_middleware
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        settings.cors_origins
    ),
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=["*"],
)


app.middleware("http")(roulette_ownership_middleware)

register_exception_handlers(app)


app.include_router(
    health_router
)

app.include_router(
    auth_router
)
app.include_router(security_router)
app.include_router(google_router)

app.include_router(
    sessions_router
)

app.include_router(
    models_router
)
app.include_router(recovery_router)
