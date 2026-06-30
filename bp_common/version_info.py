"""Información de versión / build — visible en sidebar y en logs."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache

from bp_common import __version__


@lru_cache(maxsize=1)
def get_git_sha(short: bool = True) -> str:
    """Devuelve el SHA del HEAD actual (o ENV `GIT_SHA` si está definido).

    Si no hay git ni ENV, devuelve ``"unknown"``. Cacheado para no hacer
    fork por cada rerun de Streamlit.
    """
    env_sha = os.getenv("GIT_SHA") or os.getenv("COOLIFY_GIT_COMMIT_SHA")
    if env_sha:
        return env_sha[:7] if short else env_sha
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short" if short else "HEAD", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def get_build_info() -> dict:
    return {
        "version": __version__,
        "git_sha": get_git_sha(),
        "env": os.getenv("APP_ENV", "local"),
    }


def render_streamlit_badge(st) -> None:
    """Renderiza un badge discreto en el sidebar con versión + sha + env.

    Requiere pasar el módulo `streamlit` (no se importa aquí para evitar
    forzar la dependencia en quien sólo usa lógica pura).
    """
    info = get_build_info()
    st.sidebar.caption(f"v{info['version']} · {info['git_sha']} · {info['env']}")
