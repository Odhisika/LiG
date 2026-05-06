# LiG Setup and Deployment Guide

This document covers two use cases:

1. Running the project locally for development.
2. Deploying the project on a production Linux server.

The local workflow uses the Docker setup already committed in this repository.
The production workflow uses `gunicorn` + `systemd` + `nginx` + `postgresql`, which is a safer fit for a real server than Django's development server.

## Important: Adding Docker Files Does Not Automatically Change Production

If your site is already live and your server currently deploys with a script such as `deploy.sh`, then committing these files:

- `Dockerfile`
- `docker-compose.yml`
- `docker/entrypoint.sh`

does not change production by itself.

That only changes if your server deployment process is updated to actually run Docker commands.

### What this means in practice

If your current `deploy.sh` still does something like:

- `git pull`
- activate virtualenv
- `pip install -r requirements.txt`
- `python manage.py migrate`
- `python manage.py collectstatic`
- restart `gunicorn` or `systemd`

then the server will keep deploying exactly the same way as before. The Docker files will just exist in the repository and be ignored by the running server.

### When Docker would affect production

Docker only becomes part of production if you change the deploy flow to do things like:

- `docker compose up --build -d`
- `docker build ...`
- `docker run ...`
- restart a container instead of restarting `gunicorn` or `systemd`

### Recommended approach for this project right now

Since your production site is already working, the conservative approach is:

1. keep production on the current non-Docker deploy flow
2. use Docker locally for development
3. only migrate production to Docker later if you intentionally want that change

That avoids mixing two infrastructure changes into one release.

## Current Production Reality For This Project

Based on the current deployment script, this project is already deployed in production with:

- Apache
- a Python virtual environment at `venv/`
- normal Django management commands
- a manual deployment script named `deploy.sh`

That means the current production server is not using Docker.

This deploy flow is currently:

```bash
git fetch origin
git reset --hard origin/main
git clean -fd
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check
sudo systemctl restart apache2
```

As long as `deploy.sh` stays like that, adding Docker files to the repository changes nothing about production behavior.

## 1. Local Development

### Prerequisites

- Docker
- Docker Compose
- A valid `.env` file in the project root

### Start locally

From the project root:

```bash
docker compose up --build
```

The container will:

- install Python dependencies
- read environment variables from `.env`
- run database migrations
- collect static files
- start Django on port `8000` inside the container

Open:

```text
http://localhost:8000
```

If port `8000` is already in use on your machine:

```bash
HOST_PORT=8001 docker compose up --build
```

Then open:

```text
http://localhost:8001
```

### Common local commands

Start in the background:

```bash
docker compose up --build -d
```

Stop containers:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f web
```

Run a Django management command:

```bash
docker compose exec web python manage.py createsuperuser
```

Open a shell inside the app container:

```bash
docker compose exec web sh
```

Rebuild after dependency changes:

```bash
docker compose up --build
```

### Local data and files

Because the local Compose setup bind-mounts the repository into the container, these files stay on your machine:

- `db.sqlite3`
- `media/`
- `logs/`
- `staticfiles/`

### Local environment variables

At minimum, the app expects values for:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `PAYSTACK_PUBLIC_KEY`
- `PAYSTACK_SECRET_KEY`
- `HUBTEL_CLIENT_ID`
- `HUBTEL_CLIENT_SECRET`
- `HUBTEL_MERCHANT_ACCOUNT_NUMBER`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`

Notes:

- The current project can use SQLite locally by leaving `USE_POSTGRES` unset or `False`.
- Use `django.core.mail.backends.smtp.EmailBackend` exactly for `EMAIL_BACKEND`. Do not include a trailing quote.

## 2. Production Deployment

### Production architecture

Recommended layout:

- `nginx` handles TLS and reverse proxying
- `gunicorn` serves the Django app
- `postgresql` stores application data
- `systemd` keeps the app running

Do not run `python manage.py runserver` in production.

### Server assumptions

This guide assumes:

- Ubuntu 22.04 or 24.04
- a domain name already pointing to the server
- a non-root deploy user

Example values used below:

- domain: `example.com`
- app user: `lig`
- app path: `/srv/lig`
- virtualenv path: `/srv/lig/venv`

### Step 1: Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx postgresql postgresql-contrib libpq-dev build-essential
```

### Step 2: Create a deploy user

```bash
sudo adduser --system --group --home /srv/lig lig
sudo mkdir -p /srv/lig
sudo chown -R lig:lig /srv/lig
```

If you prefer a normal shell user, that is also fine. The important part is consistent ownership of `/srv/lig`.

### Step 3: Clone the project

```bash
sudo -u lig git clone <your-repo-url> /srv/lig/app
cd /srv/lig/app
```

### Step 4: Create the Python virtual environment

```bash
sudo -u lig python3 -m venv /srv/lig/venv
sudo -u lig /srv/lig/venv/bin/pip install --upgrade pip
sudo -u lig /srv/lig/venv/bin/pip install -r /srv/lig/app/requirements.txt
sudo -u lig /srv/lig/venv/bin/pip install gunicorn
```

`gunicorn` is installed separately here because the committed Docker setup is meant for local development and starts Django with `runserver`.

### Step 5: Create PostgreSQL database and user

Open PostgreSQL:

```bash
sudo -u postgres psql
```

Then run:

```sql
CREATE DATABASE lig;
CREATE USER lig WITH PASSWORD 'replace-with-a-strong-password';
ALTER ROLE lig SET client_encoding TO 'utf8';
ALTER ROLE lig SET default_transaction_isolation TO 'read committed';
ALTER ROLE lig SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE lig TO lig;
\q
```

### Step 6: Create the production environment file

Copy the example:

```bash
sudo -u lig cp /srv/lig/app/.env.production.example /srv/lig/app/.env.production
```

Edit it:

```bash
sudo -u lig nano /srv/lig/app/.env.production
```

Minimum production expectations:

- `DEBUG=False`
- `USE_POSTGRES=True`
- `ALLOWED_HOSTS` contains your real domain names only
- `CSRF_TRUSTED_ORIGINS` uses real `https://` origins
- use real payment and email credentials
- generate a new strong `SECRET_KEY`

### Step 7: Prepare runtime directories

```bash
sudo -u lig mkdir -p /srv/lig/app/logs
sudo -u lig mkdir -p /srv/lig/app/media
sudo -u lig mkdir -p /srv/lig/app/staticfiles
```

### Step 8: Run migrations and collect static files

```bash
cd /srv/lig/app
sudo -u lig bash -lc 'cd /srv/lig/app && set -a && source .env.production && set +a && /srv/lig/venv/bin/python manage.py migrate --noinput'
sudo -u lig bash -lc 'cd /srv/lig/app && set -a && source .env.production && set +a && /srv/lig/venv/bin/python manage.py collectstatic --noinput'
sudo -u lig bash -lc 'cd /srv/lig/app && set -a && source .env.production && set +a && /srv/lig/venv/bin/python manage.py createsuperuser'
```

### Step 9: Create the `systemd` service

Create `/etc/systemd/system/lig.service`:

```ini
[Unit]
Description=LiG Django application
After=network.target

[Service]
User=lig
Group=lig
WorkingDirectory=/srv/lig/app
EnvironmentFile=/srv/lig/app/.env.production
ExecStart=/srv/lig/venv/bin/gunicorn LiG.wsgi:application --workers 3 --bind 127.0.0.1:8000 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lig
sudo systemctl start lig
sudo systemctl status lig
```

View app logs:

```bash
sudo journalctl -u lig -f
```

### Step 10: Configure nginx

Create `/etc/nginx/sites-available/lig`:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    client_max_body_size 25M;

    location /static/ {
        alias /srv/lig/app/staticfiles/;
    }

    location /media/ {
        alias /srv/lig/app/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/lig /etc/nginx/sites-enabled/lig
sudo nginx -t
sudo systemctl reload nginx
```

### Step 11: Enable HTTPS

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Issue the certificate:

```bash
sudo certbot --nginx -d example.com -d www.example.com
```

Test renewal:

```bash
sudo certbot renew --dry-run
```

## 3. Production Update Procedure

When deploying a new version:

```bash
cd /srv/lig/app
sudo -u lig git pull
sudo -u lig /srv/lig/venv/bin/pip install -r requirements.txt
sudo -u lig /srv/lig/venv/bin/pip install gunicorn
sudo -u lig bash -lc 'cd /srv/lig/app && set -a && source .env.production && set +a && /srv/lig/venv/bin/python manage.py migrate --noinput'
sudo -u lig bash -lc 'cd /srv/lig/app && set -a && source .env.production && set +a && /srv/lig/venv/bin/python manage.py collectstatic --noinput'
sudo systemctl restart lig
sudo systemctl status lig
```

If you deploy as root, switch the app commands back to the `lig` user instead of running them as root directly.

## 4. Production Checklist

Before calling the server done, confirm all of this:

- `DEBUG=False`
- PostgreSQL is in use
- the domain is correct in `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS` contains only real HTTPS origins
- nginx serves `/static/` and `/media/`
- `gunicorn` is running under `systemd`
- TLS is enabled
- database backups are configured
- `.env.production` is not committed to git

## 5. Troubleshooting

### App starts locally but not in production

Check:

- `sudo systemctl status lig`
- `sudo journalctl -u lig -f`
- `sudo nginx -t`

### Static files are missing

Run:

```bash
cd /srv/lig/app
sudo -u lig bash -lc 'cd /srv/lig/app && set -a && source .env.production && set +a && /srv/lig/venv/bin/python manage.py collectstatic --noinput'
sudo systemctl reload nginx
```

### Database connection errors

Check:

- `USE_POSTGRES=True`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

### 400 Bad Request or CSRF errors

Usually this means:

- `ALLOWED_HOSTS` is incomplete
- `CSRF_TRUSTED_ORIGINS` is missing the real `https://` domain
- the proxy headers are not being forwarded by nginx

## 6. Files Added for Reference

- `.env.production.example`: production environment variable template
- `docker-compose.yml`: local Docker workflow
- `Dockerfile`: local Docker image build
