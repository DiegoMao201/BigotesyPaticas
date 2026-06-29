#!/usr/bin/env python3
"""Descarga tracks CC0 de Pixabay y los sube al CDN una sola vez.

Uso: docker exec <api> python3 scripts/setup_audio_tracks.py
"""
import io, os, sys, requests, boto3
from botocore.client import Config

CDN_BUCKET   = os.environ.get("S3_BUCKET", "catalogo-ferreinox")
CDN_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
CDN_REGION   = os.environ.get("S3_REGION", "nyc3")
CDN_BASE     = os.environ.get("S3_PUBLIC_URL", "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com")

# Tracks CC0 de Pixabay (URL directa de descarga pública)
TRACKS = {
    "upbeat_corporate": "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946bc4763b.mp3",
    "gentle_acoustic":  "https://cdn.pixabay.com/download/audio/2022/11/22/audio_febc508520.mp3",
    "happy_pet":        "https://cdn.pixabay.com/download/audio/2022/10/30/audio_b6f4e57a78.mp3",
    "calm_inspiring":   "https://cdn.pixabay.com/download/audio/2023/01/24/audio_5a1bba8d48.mp3",
}

s3 = boto3.client(
    "s3", region_name=CDN_REGION, endpoint_url=CDN_ENDPOINT,
    aws_access_key_id=os.environ.get("S3_ACCESS_KEY",""),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY",""),
    config=Config(signature_version="s3v4"),
)

for genre, url in TRACKS.items():
    cdn_key = f"bigotesypaticas/audio/{genre}.mp3"
    # Saltar si ya existe
    try:
        s3.head_object(Bucket=CDN_BUCKET, Key=cdn_key)
        print(f"  ✓ ya existe: {genre}")
        continue
    except Exception:
        pass

    print(f"  ↓ descargando {genre}...")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    s3.put_object(
        Bucket=CDN_BUCKET, Key=cdn_key, Body=r.content,
        ACL="public-read", ContentType="audio/mpeg",
        CacheControl="public, max-age=31536000",
    )
    print(f"  ✓ subido: {CDN_BASE}/{cdn_key}")

print("Audio tracks listos en CDN")
