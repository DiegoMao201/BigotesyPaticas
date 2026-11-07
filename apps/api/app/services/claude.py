"""Claude directo en Anthropic: los análisis con IA del negocio pasan por aquí.

6-nov-2026: la llave de OpenRouter murió (401 "User not found") y con ella el informe
financiero y los captions. Diego pidió usar la misma cuenta de Anthropic de
ferreinox.co (el agente del sitio y el Cotizador): ANTHROPIC_API_KEY y, como es una
llave de organización, ANTHROPIC_WORKSPACE_ID en cada llamada.

Haiku 5.5 no acepta temperature distinta de 1 y su pensamiento cuenta dentro de
max_tokens: por eso se piensa poco (effort low) y se le da holgura al tope.
"""

from __future__ import annotations

import json
import os

import httpx

URL = "https://api.anthropic.com/v1/messages"
MODELO = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")


def _cuerpo(prompt: str, max_tokens: int) -> dict:
    return {
        "model": MODELO,
        "max_tokens": max_tokens + 3000,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "low"},
    }


def _cabeceras() -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada en environment")
    h = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    if ws := os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip():
        h["anthropic-workspace-id"] = ws
    return h


def _texto(r: httpx.Response) -> str:
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text").strip()


def hay_claude() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def completar(prompt: str, max_tokens: int = 2000, timeout: float = 90) -> str:
    r = httpx.post(URL, headers=_cabeceras(), json=_cuerpo(prompt, max_tokens), timeout=timeout)
    return _texto(r)


async def completar_async(prompt: str, max_tokens: int = 2000, timeout: float = 90) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(URL, headers=_cabeceras(), json=_cuerpo(prompt, max_tokens))
    return _texto(r)


def a_json(raw: str) -> dict:
    """El modelo a veces envuelve el JSON en ```json … ```: se lo quita."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        if "```" in raw:
            raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())
