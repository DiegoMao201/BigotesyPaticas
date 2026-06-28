"""
Sube todos los assets de marca a DO Spaces bajo bigotesypaticas/branding/
"""
import mimetypes
from pathlib import Path
import boto3
from botocore.client import Config

ENDPOINT   = "https://nyc3.digitaloceanspaces.com"
REGION     = "nyc3"
BUCKET     = "catalogo-ferreinox"
ACCESS_KEY = "DO8014RFF6H69FRGMQZB"
SECRET_KEY = "nIUpBuZgYIr5cOHUa7sULB7UE6qblM1z7vZP9XOWXxM"
PREFIX     = "bigotesypaticas/branding"
CDN_BASE   = "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com"

FILES = [
    Path("dist/brand/cdn-uploads/logo-256.png"),
    Path("dist/brand/cdn-uploads/logo-512.png"),
    Path("dist/brand/cdn-uploads/logo-1024.png"),
    Path("dist/brand/cdn-uploads/logo.svg"),
    Path("dist/brand/cdn-uploads/logo-original-1254.png"),
]

client = boto3.client(
    "s3",
    region_name=REGION,
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version="s3v4"),
)

for path in FILES:
    if not path.exists():
        print(f"  ⚠️  SKIP (no existe): {path}")
        continue
    key = f"{PREFIX}/{path.name}"
    ct = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        client.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=f,
            ACL="public-read",
            ContentType=ct,
            CacheControl="public, max-age=86400",
        )
    url = f"{CDN_BASE}/{key}"
    print(f"  ✓ {url}")

print("\n✅ CDN upload completo.")
