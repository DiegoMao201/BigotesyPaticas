"""Bigotes y Paticas API — entrypoint FastAPI."""

from __future__ import annotations

import os
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import api_router
from app.config import get_settings
from app.middleware import RequestIDMiddleware, configure_logging

settings = get_settings()
configure_logging(settings.log_level)
log = structlog.get_logger("startup")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=__import__(
            "fastapi.responses", fromlist=["ORJSONResponse"]
        ).ORJSONResponse,
    )

    app.add_middleware(RequestIDMiddleware)

    # 29-sep-2026: un error no controlado salía como 500 SIN cabeceras CORS (lo genera
    # Starlette por fuera de CORSMiddleware), así que el navegador no podía leerlo y el
    # admin decía "No se pudo conectar con el servidor" (p. ej. al crear un cliente con
    # una cédula repetida). Este middleware, dentro de CORS, lo convierte en un 500 legible.
    class _ErrorLegible(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            try:
                return await call_next(request)
            except Exception:  # noqa: BLE001 — ya lo registró RequestIDMiddleware
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Ocurrió un error en el servidor. Intenta de nuevo; si sigue, avísanos."},
                )

    app.add_middleware(_ErrorLegible)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.exception_handler(IntegrityError)
    async def _dato_repetido(request: Request, exc: IntegrityError) -> JSONResponse:
        log.warning("integrity_error", path=request.url.path, error=str(exc.orig)[:300])
        return JSONResponse(
            status_code=409,
            content={"detail": "Ese dato ya está registrado (por ejemplo, la cédula o el código). Revisa si ya existe."},
        )

    app.include_router(api_router)

    # Servir archivos de media (fotos de mascotas, facturas)
    _media_root = Path(os.getenv("PORTAL_UPLOADS_PATH", "/data/portal-uploads"))
    _media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(_media_root)), name="media")

    @app.on_event("startup")
    async def _startup() -> None:
        log.info(
            "api_started",
            version=__version__,
            environment=settings.environment,
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
