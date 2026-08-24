#!/usr/bin/env bash
# Deploys the LiG store + embedded PricePilot app from Docker, ZERO downtime,
# behind YOUR EXISTING APACHE. Manages containers with PLAIN DOCKER COMMANDS
# (no compose — the engine on this server bundles a nonstandard compose).
#
# Run as the deploy user, from anywhere:   ./deploy.sh
#
# Flow: pull -> backup -> build -> migrate -> boot standby -> health check ->
#       graceful Apache flip -> drain old -> restart PricePilot services.
#
# Prerequisites: .env.production present; Apache wired per
# deploy/apache/vhost-snippet.conf (once).
#
# Rollback:  docker tag lig-app:previous lig-app:latest && ROLLBACK=1 ./deploy.sh
set -euo pipefail

APP_ROOT="${APP_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "$APP_ROOT"

# --- self-modification guard -------------------------------------------------
# Step 1 hard-resets the repo this script lives in, and bash streams script
# files lazily — mutating $0 mid-run corrupts execution. Copy to /tmp, exec that.
if [ -z "${DEPLOY_SELF_COPY:-}" ]; then
    SELF_COPY="$(mktemp /tmp/lig-deploy.XXXXXX)"
    cp "$0" "$SELF_COPY"
    export DEPLOY_SELF_COPY=1 APP_ROOT
    exec bash "$SELF_COPY" "$@"
fi

ENV_FILE="${ENV_FILE:-$APP_ROOT/.env.production}"
ACTIVE_CONF="$APP_ROOT/deploy/apache/active.conf"
BACKUP_DIR="$APP_ROOT/backups"
HEALTH_TIMEOUT=180
NET=lig-prod-net

say() { echo "== $*"; }
die() { echo "!! $*" >&2; exit 1; }
get_env() { grep -E "^${1}=" "$ENV_FILE" | head -1 | cut -d= -f2-; }

wait_healthy() {  # $1=container  [$2=timeout]
    local waited=0 limit="${2:-$HEALTH_TIMEOUT}"
    until [ "$(docker inspect -f '{{.State.Health.Status}}' "$1" 2>/dev/null)" = healthy ]; do
        waited=$((waited + 3))
        [ "$waited" -ge "$limit" ] && return 1
        sleep 3
    done
}

proxy_block() {  # $1 = 8001|8002
    cat <<EOF
ProxyPreserveHost On
RequestHeader set X-Forwarded-Proto "https"
ProxyPass / http://127.0.0.1:$1/ retry=0 connectiontimeout=5 timeout=120
ProxyPassReverse / http://127.0.0.1:$1/
EOF
}

reload_apache() {  # $1 = 8001|8002 — installs block, TESTS it, reverts on failure
    local tmp; tmp="$(mktemp)"
    proxy_block "$1" > "$tmp"
    cp "$ACTIVE_CONF" "${ACTIVE_CONF}.bak"
    sudo cp "$tmp" "$ACTIVE_CONF"; rm -f "$tmp"
    if ! sudo apache2ctl configtest </dev/null; then
        sudo cp "${ACTIVE_CONF}.bak" "$ACTIVE_CONF"; rm -f "${ACTIVE_CONF}.bak"
        return 1
    fi
    rm -f "${ACTIVE_CONF}.bak"
    sudo systemctl reload apache2      # graceful — no dropped connections
}

start_web() {  # $1=name  $2=hostport
    docker rm -f "$1" >/dev/null 2>&1 || true
    docker run -d --name "$1" --restart unless-stopped --network "$NET" \
        --env-file "$ENV_FILE" -e RUN_MIGRATE=false \
        -e DJANGO_SETTINGS_MODULE=LiG.settings \
        -p "127.0.0.1:$2:8000" \
        -v "$APP_ROOT/staticfiles:/app/staticfiles" \
        -v "$APP_ROOT/media:/app/media" \
        -v "$APP_ROOT/logs:/app/logs" \
        --health-cmd "python -c \"import http.client as c;s=c.HTTPConnection('127.0.0.1',8000,timeout=3);s.request('GET','/');r=s.getresponse();r.read()\"" \
        --health-interval=5s --health-timeout=5s --health-retries=12 --health-start-period=30s \
        --stop-timeout=30 \
        lig-app:latest
}

start_pp_web() {
    docker rm -f lig-pp-web >/dev/null 2>&1 || true
    docker run -d --name lig-pp-web --restart unless-stopped --network "$NET" \
        --env-file "$ENV_FILE" -e DJANGO_DEBUG=False \
        -p "127.0.0.1:8003:8000" \
        -v "$APP_ROOT/media:/var/www/LiG/media" \
        --health-cmd "curl -fsS -H 'X-Forwarded-Proto: https' -o /dev/null http://localhost:8000/admin/login/" \
        --health-interval=10s --health-timeout=5s --health-retries=12 --health-start-period=40s \
        pp-app:latest \
        sh -c "python manage.py migrate --noinput && exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 --access-logfile - config.wsgi:application"
}

start_pp_worker() {
    docker rm -f lig-pp-worker >/dev/null 2>&1 || true
    docker run -d --name lig-pp-worker --restart unless-stopped --network "$NET" \
        --env-file "$ENV_FILE" \
        -v "$APP_ROOT/media:/var/www/LiG/media" \
        --stop-timeout=900 \
        pp-app:latest celery -A config worker -l info
}

start_pp_beat() {
    docker rm -f lig-pp-beat >/dev/null 2>&1 || true
    docker run -d --name lig-pp-beat --restart unless-stopped --network "$NET" \
        --env-file "$ENV_FILE" \
        -v "$APP_ROOT/media:/var/www/LiG/media" \
        --stop-timeout=30 \
        pp-app:latest celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
}

ensure_backends() {
    docker network create "$NET" >/dev/null 2>&1 || true
    docker volume create lig-pgdata >/dev/null 2>&1 || true

    if [ -z "$(docker ps -aq --filter name=^lig-prod-db$)" ]; then
        say "Starting Postgres (first time)"
        docker run -d --name lig-prod-db --restart unless-stopped --network "$NET" \
            --network-alias db \
            -e "POSTGRES_DB=$(get_env DB_NAME)" \
            -e "POSTGRES_USER=$(get_env DB_USER)" \
            -e "POSTGRES_PASSWORD=$(get_env DB_PASSWORD)" \
            -e "PRICEPILOT_DB_NAME=$(get_env PRICEPILOT_DB_NAME)" \
            -e "PRICEPILOT_DB_USER=$(get_env PRICEPILOT_DB_USER)" \
            -e "PRICEPILOT_DB_PASSWORD=$(get_env PRICEPILOT_DB_PASSWORD)" \
            -v lig-pgdata:/var/lib/postgresql/data \
            -v "$APP_ROOT/deploy/postgres-init.sh:/docker-entrypoint-initdb.d/10-pricepilot.sh:ro" \
            --health-cmd "pg_isready -U $(get_env DB_USER) -d $(get_env DB_NAME)" \
            --health-interval=5s --health-timeout=5s --health-retries=10 \
            postgres:16-alpine
    elif [ -z "$(docker ps -q --filter name=^lig-prod-db$)" ]; then
        docker start lig-prod-db >/dev/null
    fi
    wait_healthy lig-prod-db || die "db never became healthy — check: docker logs lig-prod-db"

    if [ -z "$(docker ps -aq --filter name=^lig-prod-redis$)" ]; then
        say "Starting Redis"
        docker run -d --name lig-prod-redis --restart unless-stopped --network "$NET" \
            --network-alias redis \
            --health-cmd "redis-cli ping" \
            --health-interval=5s --health-timeout=5s --health-retries=10 \
            redis:7-alpine
    elif [ -z "$(docker ps -q --filter name=^lig-prod-redis$)" ]; then
        docker start lig-prod-redis >/dev/null
    fi
    wait_healthy lig-prod-redis || die "redis never became healthy"
}

[ -f "$ENV_FILE" ] || die "$ENV_FILE missing — copy .env.production.example and fill it in"
[ -f "$ACTIVE_CONF" ] || proxy_block 8001 > "$ACTIVE_CONF"

# ---------------------------------------------------------------- 1. code ---
if [ "${ROLLBACK:-0}" != 1 ]; then
    say "Fetching latest code"
    git fetch origin
    git reset --hard origin/main
fi

# ------------------------------------------------------------- 2. safety ----
if [ -n "$(docker ps -q --filter name=^lig-prod-db$)" ]; then
    mkdir -p "$BACKUP_DIR"
    say "Backing up database -> $BACKUP_DIR/"
    docker exec lig-prod-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
        | gzip > "$BACKUP_DIR/pre-deploy-$(date +%Y%m%d-%H%M%S).sql.gz"
    ls -1t "$BACKUP_DIR"/pre-deploy-*.sql.gz | tail -n +8 | xargs -r rm --
fi

if docker image inspect lig-app:latest >/dev/null 2>&1; then
    say "Tagging current image as rollback point"
    docker tag lig-app:latest lig-app:previous
fi

# ---------------------------------------------------------------- 3. build --
if [ "${ROLLBACK:-0}" = 1 ]; then
    say "ROLLBACK mode — skipping fetch/build/migrate, reusing lig-app:previous"
else
    say "Building images"
    docker buildx build -t lig-app:latest --load .
    docker buildx build -t pp-app:latest --load ./pricepilot
fi

# ------------------------------------------------------------ 4. backends ---
say "Ensuring db/redis are up"
ensure_backends

# ------------------------------------------------------------ 5. migrate ----
if [ "${ROLLBACK:-0}" != 1 ]; then
    # Plain `docker run` against the shared network; old containers keep
    # serving throughout — migrations must stay additive/backward-compatible.
    say "Migrating LiG database"
    docker run --rm --network "$NET" --env-file "$ENV_FILE" \
        lig-app:latest python manage.py migrate --noinput

    say "Migrating PricePilot database"
    docker run --rm --network "$NET" --env-file "$ENV_FILE" \
        pp-app:latest python manage.py migrate --noinput
fi

# --------------------------------------------------- 6. blue-green switch ---
ACTIVE_PORT="$(grep -oE '127\.0\.0\.1:800[12]' "$ACTIVE_CONF" | head -1 | cut -d: -f2)"
case "$ACTIVE_PORT" in
    8001) ACTIVE_SVC=web-a; STANDBY_SVC=web-b; STANDBY_PORT=8002 ;;
    8002) ACTIVE_SVC=web-b; STANDBY_SVC=web-a; STANDBY_PORT=8001 ;;
    *)    ACTIVE_SVC="";    STANDBY_SVC=web-a; STANDBY_PORT=8001 ;;  # fresh
esac

A_RUNNING=$(docker ps -q --filter name=^lig-web-a$ | wc -l)
B_RUNNING=$(docker ps -q --filter name=^lig-web-b$ | wc -l)

if [ -z "$ACTIVE_SVC" ] || { [ "$A_RUNNING" = 0 ] && [ "$B_RUNNING" = 0 ]; }; then
    # ---------------------------------------------------- cold bootstrap ---
    say "No web container up yet — cold bootstrap (first deploy)"
    start_web lig-web-a 8001
    say "Waiting for web-a to become healthy"
    wait_healthy lig-web-a || { docker logs --tail 50 lig-web-a >&2 || true; die "web-a failed its health check"; }
    say "Starting PricePilot services"
    start_pp_web; start_pp_worker; start_pp_beat
    if reload_apache 8001; then
        say "Done — site live on web-a via Apache"
    else
        say "WARNING: containers are up and healthy on 127.0.0.1:8001, but Apache"
        say "could not be reloaded. Wire the vhost include first — see"
        say "deploy/apache/vhost-snippet.conf — then rerun ./deploy.sh"
    fi
    exit 0
fi

say "Active: $ACTIVE_SVC (port $ACTIVE_PORT) — deploying to standby $STANDBY_SVC"
start_web "lig-$STANDBY_SVC" "$STANDBY_PORT"

say "Waiting for $STANDBY_SVC to become healthy"
if ! wait_healthy "lig-$STANDBY_SVC"; then
    docker logs --tail 50 "lig-$STANDBY_SVC" >&2 || true
    die "$STANDBY_SVC failed its health check — $ACTIVE_SVC still serving, NOTHING was switched"
fi

say "Flipping Apache -> $STANDBY_SVC (port $STANDBY_PORT, graceful reload)"
if ! reload_apache "$STANDBY_PORT"; then
    die "Apache config test/reload failed — reverted, $ACTIVE_SVC still serving"
fi

say "Draining and removing old $ACTIVE_SVC"
docker stop -t 30 "lig-$ACTIVE_SVC" >/dev/null
docker rm "lig-$ACTIVE_SVC" >/dev/null

say "Restarting PricePilot web/worker/beat on the new image"
start_pp_web; start_pp_worker; start_pp_beat

say "Pruning dangling images"
docker image prune -f >/dev/null

say "Deployment complete — live on $STANDBY_SVC, rollback image: lig-app:previous"
