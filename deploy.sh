#!/usr/bin/env bash
# Deploys the LiG store + embedded PricePilot app from Docker, with ZERO downtime.
#
# Run as the deploy user, from anywhere:
#   ./deploy.sh
#
# How it works (blue-green behind YOUR existing Apache):
#   build new image -> migrate DB -> boot the STANDBY web container ->
#   health-check it -> rewrite Apache's proxy include -> graceful reload ->
#   stop the old one.
#   Visitors never hit a dead port: Apache keeps serving the old container
#   until the reload completes, and open connections never drop.
#
# Prerequisites:
#   - repo cloned at /var/www/LiG (so ./staticfiles ./media match your Apache
#     Alias lines), Docker + compose plugin installed
#   - .env.production present (copy .env.production.example)
#   - ONE-TIME: wire Apache per deploy/apache/vhost-snippet.conf
#
# Rollback to the previous release (skips fetch/build/migrate):
#   ROLLBACK=1 ./deploy.sh
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_ROOT"

ENV_FILE="${ENV_FILE:-$APP_ROOT/.env.production}"
ACTIVE_CONF="$APP_ROOT/deploy/apache/active.conf"
BACKUP_DIR="$APP_ROOT/backups"
HEALTH_TIMEOUT=180          # seconds to wait for the standby to go healthy

DC=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml)

say() { echo "== $*"; }
die() { echo "!! $*" >&2; exit 1; }

proxy_block() {  # $1 = 8001|8002
    cat <<EOF
ProxyPreserveHost On
RequestHeader set X-Forwarded-Proto "https"
ProxyPass / http://127.0.0.1:$1/ retry=0 connectiontimeout=5 timeout=120
ProxyPassReverse / http://127.0.0.1:$1/
EOF
}

[ -f "$ENV_FILE" ] || die "$ENV_FILE missing — copy .env.production.example and fill it in"
[ -f "$ACTIVE_CONF" ] || proxy_block 8001 > "$ACTIVE_CONF"

# ---------------------------------------------------------------- 1. code ---
if [ "${ROLLBACK:-0}" != 1 ]; then
    say "Fetching latest code"
    git fetch origin
    git reset --hard origin/main
    # NOTE: git clean does NOT touch ignored files (.env.production,
    # active.conf, backups/) so secrets and runtime state survive deploys.
fi

# ------------------------------------------------------------- 2. safety ----
if [ -n "$(docker ps -q --filter name=lig-prod-db)" ]; then
    mkdir -p "$BACKUP_DIR"
    say "Backing up database -> $BACKUP_DIR/"
    $DC exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
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
    # Explicit buildx (--load): this server's Docker 29 `build` alias drops
    # the context argument. Services reference these exact tags.
    docker buildx build -t lig-app:latest --load .
    docker buildx build -t pp-app:latest --load ./pricepilot

    # ------------------------------------------------ 4. migrate ----
    # Migrations run ONCE here via PLAIN `docker run` (this server's compose
    # plugin mishandles both `build` and `run` service resolution). Old
    # containers keep serving throughout — migrations must stay additive.
    say "Ensuring db/redis are up"
    $DC up -d db redis
    DB_WAITED=0
    until [ "$(docker inspect -f '{{.State.Health.Status}}' lig-prod-db 2>/dev/null)" = healthy ]; do
        DB_WAITED=$((DB_WAITED + 2))
        [ "$DB_WAITED" -ge "$HEALTH_TIMEOUT" ] && die "db never became healthy — check: docker logs lig-prod-db"
        sleep 2
    done

    NET="lig-prod_default"
    say "Migrating LiG database"
    docker run --rm --network "$NET" --env-file "$ENV_FILE" \
        lig-app:latest python manage.py migrate --noinput

    say "Migrating PricePilot database"
    docker run --rm --network "$NET" --env-file "$ENV_FILE" \
        pp-app:latest python manage.py migrate --noinput
fi

# --------------------------------------------------- 5. blue-green switch ---
ACTIVE_PORT="$(grep -oE '127\.0\.0\.1:800[12]' "$ACTIVE_CONF" | head -1 | cut -d: -f2)"
case "$ACTIVE_PORT" in
    8001) ACTIVE_SVC=web-a; STANDBY_SVC=web-b; STANDBY_PORT=8002 ;;
    8002) ACTIVE_SVC=web-b; STANDBY_SVC=web-a; STANDBY_PORT=8001 ;;
    *)    ACTIVE_SVC="";    STANDBY_SVC=web-a; STANDBY_PORT=8001 ;;  # fresh
esac

A_RUNNING=$($DC ps -q web-a 2>/dev/null | wc -l)
B_RUNNING=$($DC ps -q web-b 2>/dev/null | wc -l)

reload_apache() {  # $1 = 8001|8002 — installs the block, TESTS it, reverts on failure
    local tmp
    tmp="$(mktemp)"
    proxy_block "$1" > "$tmp"
    cp "$ACTIVE_CONF" "${ACTIVE_CONF}.bak"
    sudo cp "$tmp" "$ACTIVE_CONF"
    rm -f "$tmp"
    if ! sudo apache2ctl configtest </dev/null; then
        sudo cp "${ACTIVE_CONF}.bak" "$ACTIVE_CONF"
        rm -f "${ACTIVE_CONF}.bak"
        return 1
    fi
    rm -f "${ACTIVE_CONF}.bak"
    sudo systemctl reload apache2      # graceful — no dropped connections
}

if [ -z "$ACTIVE_SVC" ] || { [ "$A_RUNNING" = 0 ] && [ "$B_RUNNING" = 0 ]; }; then
    # ---------------------------------------------------- cold bootstrap ---
    say "No web container up yet — starting the full stack (first deploy)"
    $DC up -d
    say "Waiting for web-a to become healthy"
    for _ in $(seq 1 $((HEALTH_TIMEOUT / 3))); do
        [ "$(docker inspect -f '{{.State.Health.Status}}' lig-web-a 2>/dev/null)" = healthy ] && break
        sleep 3
    done
    docker inspect -f '{{.State.Health.Status}}' lig-web-a | grep -q healthy \
        || die "web-a never went healthy — check: $DC logs web-a"
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
$DC up -d --no-deps "$STANDBY_SVC"

STANDBY_CNAME="lig-$STANDBY_SVC"
say "Waiting for $STANDBY_SVC to become healthy"
HEALTHY=0
for _ in $(seq 1 $((HEALTH_TIMEOUT / 3))); do
    if [ "$(docker inspect -f '{{.State.Health.Status}}' "$STANDBY_CNAME" 2>/dev/null)" = healthy ]; then
        HEALTHY=1; break
    fi
    sleep 3
done
if [ "$HEALTHY" != 1 ]; then
    $DC logs --tail 50 "$STANDBY_SVC" >&2 || true
    die "$STANDBY_SVC failed its health check — $ACTIVE_SVC still serving, NOTHING was switched"
fi

say "Flipping Apache -> $STANDBY_SVC (port $STANDBY_PORT, graceful reload)"
if ! reload_apache "$STANDBY_PORT"; then
    die "Apache config test/reload failed — reverted, $ACTIVE_SVC still serving"
fi

# ------------------------------------------------------- 6. old + workers ---
say "Stopping old $ACTIVE_SVC (drains in-flight requests)"
$DC stop "$ACTIVE_SVC"

say "Restarting PricePilot web/worker/beat on the new image"
$DC up -d --no-deps pp-web pp-worker pp-beat

say "Pruning dangling images"
docker image prune -f >/dev/null

say "Deployment complete — live on $STANDBY_SVC, rollback image: lig-app:previous"
