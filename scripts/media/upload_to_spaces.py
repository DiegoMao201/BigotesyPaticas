"""
Sube assets a DigitalOcean Spaces bajo el prefix de Bigotes y Paticas.
Idempotente vía ETag (compara MD5).

Uso:
    python scripts/media/upload_to_spaces.py --src local-assets/optimized
    python scripts/media/upload_to_spaces.py --src local-assets/optimized --dry-run

Requiere ENV vars (mismas que la API):
    S3_ENDPOINT_URL, S3_REGION, S3_BUCKET, S3_PREFIX, S3_ACCESS_KEY, S3_SECRET_KEY
"""
from __future__ import annotations

import argparse
import hashlib
import mimetypes
import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError
except ImportError:
    print("Falta boto3. Instalar:  pip install boto3", file=sys.stderr)
    raise


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        region_name=os.environ.get("S3_REGION", "nyc3"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        config=Config(signature_version="s3v4"),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, type=Path)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--public", action="store_true", default=True,
                   help="Marca objetos como public-read (default true)")
    args = p.parse_args()

    if not args.src.exists():
        print(f"src no existe: {args.src}", file=sys.stderr)
        return 1

    bucket = os.environ["S3_BUCKET"]
    prefix = os.environ.get("S3_PREFIX", "").strip("/")
    client = make_client() if not args.dry_run else None

    uploaded = skipped = 0
    for f in args.src.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(args.src).as_posix()
        key = f"{prefix}/{rel}" if prefix else rel
        local_md5 = md5_of(f)

        if not args.dry_run:
            try:
                head = client.head_object(Bucket=bucket, Key=key)
                etag = head["ETag"].strip('"')
                if etag == local_md5:
                    skipped += 1
                    continue
            except ClientError as e:
                if e.response["Error"]["Code"] not in {"404", "NoSuchKey"}:
                    raise

        ctype, _ = mimetypes.guess_type(f.name)
        ctype = ctype or "application/octet-stream"
        extra = {
            "ContentType": ctype,
            "CacheControl": "public, max-age=31536000, immutable",
        }
        if args.public:
            extra["ACL"] = "public-read"

        if args.dry_run:
            print(f"[dry] PUT s3://{bucket}/{key} ({ctype})")
        else:
            client.upload_file(str(f), bucket, key, ExtraArgs=extra)
            print(f"  ↑ s3://{bucket}/{key}")
        uploaded += 1

    print(f"\nSubidos: {uploaded} | Saltados (sin cambios): {skipped}")
    cdn = os.environ.get("S3_PUBLIC_URL")
    if cdn:
        print(f"\nCDN base: {cdn}/{prefix}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
