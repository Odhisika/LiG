#!/bin/bash
# Runs ONCE, on the first boot of an empty pgdata volume, by the official
# postgres image entrypoint. Creates PricePilot's database next to LiG's
# (POSTGRES_DB from the compose environment) inside the same cluster.
set -e

pp_db="${PRICEPILOT_DB_NAME:-pricepilot}"
pp_user="${PRICEPILOT_DB_USER:-pricepilot}"
pp_pass="${PRICEPILOT_DB_PASSWORD:?set PRICEPILOT_DB_PASSWORD in .env.production}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-SQL
    CREATE DATABASE ${pp_db};
    CREATE USER ${pp_user} WITH PASSWORD '${pp_pass}';
    GRANT ALL PRIVILEGES ON DATABASE ${pp_db} TO ${pp_user};
    ALTER DATABASE ${pp_db} OWNER TO ${pp_user};
SQL
