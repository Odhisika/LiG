#!/bin/sh
set -e

mkdir -p /app/logs /app/media /app/staticfiles

# Prod deploys run migrations explicitly ONCE from deploy.sh (before traffic
# switches), so long-running containers must not race each other on startup.
if [ "${RUN_MIGRATE:-true}" = "true" ]; then
    python manage.py migrate --noinput
fi

python manage.py collectstatic --noinput

exec "$@"
