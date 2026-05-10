"""Health & version endpoints."""
from __future__ import annotations

import os
import subprocess

from fastapi import APIRouter
from sqlalchemy import text

from app.deps import DBSession

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: DBSession) -> dict:
    """Verifica conectividad a DB."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        return {"status": "ok", "db": "ok"}
    except Exception as exc:
        return {"status": "degraded", "db": str(exc)}


def _get_git_sha() -> str:
    sha = (
        os.getenv("GIT_SHA")
        or os.getenv("COOLIFY_GIT_COMMIT_SHA")
        or os.getenv("SOURCE_COMMIT")
    )
    if sha:
        return sha[:7]
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


@router.get("/version")
async def version() -> dict:
    from app import __version__

    return {
        "version": __version__,
        "git_sha": _get_git_sha(),
        "environment": os.getenv("ENVIRONMENT", "local"),
    }
