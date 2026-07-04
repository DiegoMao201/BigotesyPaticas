#!/bin/sh
set -e

alembic upgrade head
python -m app.cli.seed
python -m app.cli.seed_catalog

# Cron en background: publica posts y stories cada 5 min
while true; do
  python3 scripts/publish_scheduled_posts.py >> /tmp/publish_feed.log 2>&1
  python3 scripts/publish_stories.py >> /tmp/publish_stories.log 2>&1
  sleep 300
done &

exec gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --timeout 60 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -
