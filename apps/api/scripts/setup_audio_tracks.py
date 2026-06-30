#!/usr/bin/env python3
"""Genera tracks de audio con ffmpeg (síntesis CC0) y los sube al CDN.

Uso: docker exec <api> python3 scripts/setup_audio_tracks.py
"""

import os
import subprocess
import tempfile
from pathlib import Path

import boto3
from botocore.client import Config

CDN_BUCKET = os.environ.get("S3_BUCKET", "catalogo-ferreinox")
CDN_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
CDN_REGION = os.environ.get("S3_REGION", "nyc3")
CDN_BASE = os.environ.get(
    "S3_PUBLIC_URL", "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com"
)

# Síntesis ffmpeg: acordes/tonos CC0 propios — 30 segundos cada uno
TRACKS = {
    # Acorde mayor brillante C-E-G + harmónicos
    "upbeat_corporate": (
        "aevalsrc='0.25*sin(2*PI*261.63*t)+0.2*sin(2*PI*329.63*t)+0.2*sin(2*PI*392*t)"
        "+0.1*sin(2*PI*523.25*t)+0.05*sin(2*PI*659.25*t)|"
        "0.25*sin(2*PI*261.63*t)+0.2*sin(2*PI*329.63*t)+0.2*sin(2*PI*392*t)"
        "+0.1*sin(2*PI*523.25*t)+0.05*sin(2*PI*659.25*t)':s=44100:c=stereo:d=30"
    ),
    # Tono suave Re menor (D-F-A) — acústico tranquilo
    "gentle_acoustic": (
        "aevalsrc='0.2*sin(2*PI*293.66*t)+0.15*sin(2*PI*349.23*t)+0.15*sin(2*PI*440*t)"
        "+0.05*sin(2*PI*587.33*t)|"
        "0.2*sin(2*PI*293.66*t)+0.15*sin(2*PI*349.23*t)+0.15*sin(2*PI*440*t)"
        "+0.05*sin(2*PI*587.33*t)':s=44100:c=stereo:d=30"
    ),
    # Acorde Sol mayor (G-B-D) alegre — happy
    "happy_pet": (
        "aevalsrc='0.25*sin(2*PI*392*t)+0.2*sin(2*PI*493.88*t)+0.2*sin(2*PI*587.33*t)"
        "+0.1*sin(2*PI*784*t)|"
        "0.25*sin(2*PI*392*t)+0.2*sin(2*PI*493.88*t)+0.2*sin(2*PI*587.33*t)"
        "+0.1*sin(2*PI*784*t)':s=44100:c=stereo:d=30"
    ),
    # Fa mayor (F-A-C) suave — inspiring calm
    "calm_inspiring": (
        "aevalsrc='0.18*sin(2*PI*174.61*t)+0.15*sin(2*PI*220*t)+0.15*sin(2*PI*261.63*t)"
        "+0.08*sin(2*PI*349.23*t)|"
        "0.18*sin(2*PI*174.61*t)+0.15*sin(2*PI*220*t)+0.15*sin(2*PI*261.63*t)"
        "+0.08*sin(2*PI*349.23*t)':s=44100:c=stereo:d=30"
    ),
}

s3 = boto3.client(
    "s3",
    region_name=CDN_REGION,
    endpoint_url=CDN_ENDPOINT,
    aws_access_key_id=os.environ.get("S3_ACCESS_KEY", ""),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY", ""),
    config=Config(signature_version="s3v4"),
)

with tempfile.TemporaryDirectory() as tmp:
    for genre, expr in TRACKS.items():
        cdn_key = f"bigotesypaticas/audio/{genre}.mp3"
        try:
            s3.head_object(Bucket=CDN_BUCKET, Key=cdn_key)
            print(f"  ✓ ya existe: {genre}")
            continue
        except Exception:
            pass

        out = Path(tmp) / f"{genre}.mp3"
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            expr,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(out),
        ]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            print(f"  ✗ ffmpeg falló para {genre}: {r.stderr[-200:]}")
            continue

        s3.upload_file(
            str(out),
            CDN_BUCKET,
            cdn_key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": "audio/mpeg",
                "CacheControl": "public, max-age=31536000",
            },
        )
        print(f"  ✓ generado y subido: {genre} → {CDN_BASE}/{cdn_key}")

print("Audio tracks CC0 listos en CDN")
