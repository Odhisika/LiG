#!/bin/sh
set -e

mkdir -p /app/logs /app/media /app/staticfiles

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
