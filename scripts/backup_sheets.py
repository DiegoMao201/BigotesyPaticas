"""Backup script — exporta todas las tabs del spreadsheet maestro a CSV + Parquet.

Uso:
    python scripts/backup_sheets.py --out backups/$(date +%Y-%m-%d)
    python scripts/backup_sheets.py --out s3://bucket/path  # (futuro)

Idempotente. Crea la carpeta destino. No depende de Streamlit.
Lee credenciales en este orden:
    1. ENV `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` (ruta a JSON)
    2. ENV `GOOGLE_SERVICE_ACCOUNT_JSON` (JSON inline)
    3. `.streamlit/secrets.toml` (sección `[google_service_account]`)
    4. `project-secrets/.env.production` (clave `GOOGLE_SERVICE_ACCOUNT_JSON`)

Y `SHEET_URL` desde las mismas fuentes.

Recomendado: agendar como cron diario (ver SPRINT0_HARDENING.md).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import gspread
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from bp_common.logging_setup import get_logger  # noqa: E402
from bp_common.tz import now_co  # noqa: E402

LOG = get_logger("backup_sheets")


def _load_service_account() -> dict[str, Any]:
    path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    inline = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if inline:
        return json.loads(inline)
    # Streamlit secrets
    secrets_toml = REPO_ROOT / ".streamlit" / "secrets.toml"
    if secrets_toml.exists():
        try:
            import tomllib  # py>=3.11
        except ImportError:  # pragma: no cover
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(secrets_toml.read_text(encoding="utf-8"))
        if "google_service_account" in data:
            return data["google_service_account"]
    raise SystemExit(
        "No se encontró service account. Define GOOGLE_SERVICE_ACCOUNT_JSON{,_PATH} "
        "o crea .streamlit/secrets.toml con [google_service_account]."
    )


def _load_sheet_url() -> str:
    url = os.getenv("SHEET_URL")
    if url:
        return url
    secrets_toml = REPO_ROOT / ".streamlit" / "secrets.toml"
    if secrets_toml.exists():
        try:
            import tomllib
        except ImportError:  # pragma: no cover
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(secrets_toml.read_text(encoding="utf-8"))
        if "SHEET_URL" in data:
            return data["SHEET_URL"]
    raise SystemExit("No se encontró SHEET_URL en ENV ni en .streamlit/secrets.toml.")


def export_workbook(
    out_dir: Path, *, formats: tuple[str, ...] = ("csv", "parquet")
) -> dict[str, int]:
    """Descarga TODAS las tabs y las guarda en out_dir. Devuelve {tab: nrows}."""
    sa = _load_service_account()
    url = _load_sheet_url()
    gc = gspread.service_account_from_dict(sa)
    sh = gc.open_by_url(url)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, int] = {}
    for ws in sh.worksheets():
        title = ws.title
        try:
            values = ws.get_all_values()
        except Exception as exc:
            LOG.error("read_failed", extra={"tab": title, "error": str(exc)})
            continue
        if not values:
            LOG.warning("empty_tab", extra={"tab": title})
            summary[title] = 0
            continue

        header = [h or f"Col_{i+1}" for i, h in enumerate(values[0])]
        df = pd.DataFrame(values[1:], columns=header)
        if "csv" in formats:
            df.to_csv(out_dir / f"{title}.csv", index=False)
        if "parquet" in formats:
            try:
                df.to_parquet(out_dir / f"{title}.parquet", index=False)
            except Exception as exc:
                LOG.warning("parquet_failed", extra={"tab": title, "error": str(exc)})
        summary[title] = len(df)
        LOG.info("tab_exported", extra={"tab": title, "rows": len(df)})

    # Manifest
    manifest = {
        "exported_at": now_co().isoformat(),
        "sheet_url": url,
        "tabs": summary,
        "formats": list(formats),
    }
    (out_dir / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    LOG.info("backup_complete", extra={"out_dir": str(out_dir), "tabs": len(summary)})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=f"backups/{now_co().strftime('%Y-%m-%d')}",
        help="Directorio destino (relativo al repo o absoluto).",
    )
    parser.add_argument("--no-parquet", action="store_true", help="Sólo CSV, sin parquet.")
    args = parser.parse_args()

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir

    formats: tuple[str, ...] = ("csv",) if args.no_parquet else ("csv", "parquet")
    summary = export_workbook(out_dir, formats=formats)
    print(json.dumps(summary, indent=2))
    return 0 if summary else 1


if __name__ == "__main__":
    raise SystemExit(main())
