"""Claude directo en Anthropic para los scripts sueltos (6-nov-2026).

OpenRouter murió (401) y Diego pidió pasar todo a la cuenta de Anthropic de
ferreinox.co, que tiene crédito gratuito. `claude_post` recibe el mismo cuerpo
estilo OpenAI que ya armaban los scripts y devuelve un httpx.Response con la forma
de OpenAI (`choices[0].message.content`, `usage.prompt_tokens`), así el resto de
cada script no cambia.

La llave: ANTHROPIC_API_KEY / ANTHROPIC_WORKSPACE_ID, o ~/.config/bp/anthropic.json.
Haiku 5.5 no acepta temperature distinta de 1 ni response_format, y su pensamiento
cuenta dentro de max_tokens: se piensa poco y se le da holgura al tope.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

URL = "https://api.anthropic.com/v1/messages"
#: El más económico. Alcanza para etiquetar, clasificar, describir productos y
#: redactar blogs y landings en JSON.
HAIKU = "claude-haiku-5-5"


def _llave() -> tuple[str, str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID", "")
    archivo = Path.home() / ".config/bp/anthropic.json"
    if not key and archivo.exists():
        d = json.loads(archivo.read_text())
        key, ws = d.get("api_key", ""), ws or d.get("workspace_id", "")
    return key, ws


def hay_claude() -> bool:
    return bool(_llave()[0])


async def claude_post(client: httpx.AsyncClient, json: dict, timeout: float = 90) -> httpx.Response:
    key, ws = _llave()
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    if ws:
        headers["anthropic-workspace-id"] = ws
    system = "\n\n".join(m["content"] for m in json["messages"] if m["role"] == "system")
    cuerpo = {
        "model": json.get("model") or HAIKU,
        "max_tokens": json.get("max_tokens", 2000) + 3000,
        "messages": [m for m in json["messages"] if m["role"] != "system"],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "low"},
    }
    if system:
        cuerpo["system"] = system
    r = await client.post(URL, headers=headers, json=cuerpo, timeout=timeout)
    r.raise_for_status()
    d = r.json()
    texto = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
    u = d.get("usage", {})
    return httpx.Response(200, request=r.request, json={
        "choices": [{"message": {"content": texto}}],
        "usage": {"prompt_tokens": u.get("input_tokens", 0), "completion_tokens": u.get("output_tokens", 0)},
    })
