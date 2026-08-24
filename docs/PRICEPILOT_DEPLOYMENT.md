# PricePilot Embedded Deployment Guide

PricePilot (the price-monitoring app) now lives inside this repository at
`pricepilot/`. Pushing to `main` and running `./deploy.sh` on the server
deploys BOTH the LiG store site and PricePilot.

## Local full-stack testing (Docker)

The repo's `docker-compose.yml` runs everything in one stack: the LiG store,
PricePilot API + Celery worker/beat, its Postgres + Redis, and the React
frontend.

```bash
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8000 | LiG store |
| http://localhost:8001 | PricePilot API (schema at `/api/schema/`, admin at `/admin/`) |
| http://localhost:5173 | React frontend |

Useful commands:

```bash
docker compose up lig          # LiG store only
docker compose exec pp-web python manage.py sync_store     # push products to LiG
docker compose exec pp-web python manage.py categorize_products --sync
docker compose logs -f pp-worker pp-beat
```

Notes:

- The first build is slow (it downloads Chromium for the scrapers + Node
  packages); afterwards everything is cached.
- PricePilot scrapes suppliers and seeds products into **LiG's own
  `db.sqlite3`** (and `media/`) via the shared bind mounts — that's the
  production flow too, just against Postgres there.
- The migration of PricePilot's own database runs automatically inside the
  `pp-web` container; the `lig` container migrates the store.
- Playwright is pre-installed in the image, so scrapers run straight away.

```
/srv/lig/app
├── LiG/                      (this repo root)
│   ├── deploy.sh             # deploys LiG + PricePilot together
│   ├── deploy/               # systemd units + optional nginx config
│   ├── .env.production       # shared env: LiG + PricePilot variables
│   └── pricepilot/           # the PricePilot Django app (embedded)
└── venv/                     # LiG virtualenv (existing)
```

## What runs in production

| Service | Unit | What it does |
|---|---|---|
| LiG web | `lig` (existing) | Django/gunicorn on `127.0.0.1:8000` |
| PricePilot API | `pricepilot` | gunicorn on `127.0.0.1:8001` (optional for the UI) |
| PricePilot worker | `pricepilot-worker` | Celery worker: runs scrapers + LiG store sync |
| PricePilot beat | `pricepilot-beat` | Celery beat: schedules the monitor/sync jobs |

The two Celery services are the important live ones — they scrape supplier
prices and seed/store the products into LiG's own database.

## One-time server setup

Run these once (as `lig` or root, as noted). Prereqs: Ubuntu 22.04/24.04,
Postgres, Redis, nginx, and the existing LiG deployment from
`docs/SETUP_AND_DEPLOYMENT.md`.

### 1. Install Redis + Playwright system libraries

```bash
sudo apt install -y redis-server
sudo systemctl enable --now redis-server

# Playwright browsers for the scrapers (Chromium)
sudo -u lig /srv/lig/app/pricepilot/.venv/bin/playwright install --with-deps chromium
```

`--with-deps` needs sudo; if you prefer, run `playwright install chromium` as
`lig` after manually installing the OS deps listed by `playwright install-deps`.

### 2. Create PricePilot's own Postgres database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE pricepilot;
CREATE USER pricepilot WITH PASSWORD 'replace-with-pricepilot-db-password';
ALTER ROLE pricepilot SET client_encoding TO 'utf8';
ALTER ROLE pricepilot SET default_transaction_isolation TO 'read committed';
ALTER ROLE pricepilot SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE pricepilot TO pricepilot;
\q
```

### 3. Create the PricePilot virtualenv

```bash
sudo -u lig python3 -m venv /srv/lig/app/pricepilot/.venv
sudo -u lig /srv/lig/app/pricepilot/.venv/bin/pip install --upgrade pip
sudo -u lig /srv/lig/app/pricepilot/.venv/bin/pip install -r /srv/lig/app/pricepilot/requirements/prod.txt
```

### 4. Add the PricePilot variables to `.env.production`

Copy the block from `.env.production.example` into
`/srv/lig/app/.env.production` and fill in real values. Critical bits:

- `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DJANGO_SECRET_KEY`
- `DATABASE_URL` → the `pricepilot` DB from step 2
- `LIG_DATABASE_URL` → LiG's own database (same credentials as the existing
  `DB_NAME/DB_USER/DB_PASSWORD`)
- `LIG_MEDIA_ROOT=/srv/lig/app/media`
- `LIG_SYNC_ENABLED=True`

### 5. Install the systemd units

```bash
sudo cp /srv/lig/app/deploy/pricepilot.service      /etc/systemd/system/
sudo cp /srv/lig/app/deploy/pricepilot-worker.service /etc/systemd/system/
sudo cp /srv/lig/app/deploy/pricepilot-beat.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pricepilot pricepilot-worker pricepilot-beat
sudo systemctl status pricepilot pricepilot-worker pricepilot-beat
```

The `pricepilot.service` unit is only needed if you want the web UI/API;
the worker + beat units drive the actual monitoring and store sync.

### 6. (Optional) Expose the PricePilot UI on a subdomain

Requires a DNS `A` record for e.g. `pricepilot.example.com`:

```bash
sudo cp /srv/lig/app/deploy/nginx-pricepilot.conf /etc/nginx/sites-available/pricepilot
sudo ln -s /etc/nginx/sites-available/pricepilot /etc/nginx/sites-enabled/pricepilot
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d pricepilot.example.com
```

Build the frontend once (with Node 18+ on the server or locally and commit
`frontend/dist`):

```bash
cd /srv/lig/app/pricepilot/frontend
npm ci
VITE_API_BASE_URL=https://pricepilot.example.com/api npm run build
```

### 7. First run: create the admin + confirm the sync

```bash
sudo -u lig bash -lc 'cd /srv/lig/app/pricepilot && set -a && source /srv/lig/app/.env.production && set +a && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py createsuperuser'
sudo -u lig bash -lc 'cd /srv/lig/app/pricepilot && set -a && source /srv/lig/app/.env.production && set +a && .venv/bin/python manage.py check'
```

Log in to the PricePilot admin (`https://pricepilot.example.com/admin/` or
`/admin/`), add a supplier/product monitor, and watch the beat scheduler
pick it up. Products land in LiG's database in their matching fine-grained
category (Laptops, Desktops, Routers & Modems, Security Cameras, etc.); if a
product's category is unknown it goes to `uncategorized` rather than creating
a brand-new category.

## Deploying updates

On the server:

```bash
cd /srv/lig/app
./deploy.sh
```

`deploy.sh` does the existing LiG flow (`git fetch` → `git reset --hard
origin/main` → `git clean -fd` → pip → migrate → collectstatic → check) and
the same for PricePilot (migrating only its OWN database — LiG's tables are
managed by LiG), then restarts all four services.

Give the deploy user scoped sudo for the restarts:

```text
lig ALL=(ALL) NOPASSWD: /bin/systemctl restart lig, /bin/systemctl restart pricepilot, /bin/systemctl restart pricepilot-worker, /bin/systemctl restart pricepilot-beat
```

### Fixing categories on existing store products

PricePilot's auto-categorizer only classifies products going forward. If LiG
already holds products with wrong departments (e.g. jred imports where
switches landed in Desktops, routers in Networking, NVRs in Networking), run
the one-off re-categorizer against LiG's DB:

```bash
# Dry run first — prints every row it would move:
sudo -u lig /srv/lig/app/pricepilot/.venv/bin/python /srv/lig/app/pricepilot/manage.py recategorize_store

# Then apply:
sudo -u lig /srv/lig/app/pricepilot/.venv/bin/python /srv/lig/app/pricepilot/manage.py recategorize_store --apply
```

Products the categorizer can't confidently classify are left unchanged; pass
`--to-uncategorized` to sweep those into the default category instead.

## Troubleshooting

- **Celery tasks fail with a database error**: PricePilot opens two
  connections — its own `pricepilot` DB and LiG's `lig` DB via
  `LIG_DATABASE_URL`. Confirm both users/passwords in `.env.production` and
  never run `manage.py migrate --database lig` (LiG owns those tables).
- **Beat schedule empty**: jobs are stored in PricePilot's own DB; run
  `migrate` (step 7) so `django_celery_beat` tables exist.
- **PricePilot UI redirects in a loop**: `prod.py` expects the
  `X-Forwarded-Proto: https` header, which `deploy/nginx-pricepilot.conf`
  already sets. If you use a different reverse proxy, keep that header.
- **Playwright/browser errors in workers**: run
  `playwright install --with-deps chromium` (step 1).
