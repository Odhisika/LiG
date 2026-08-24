FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt.utf16

RUN python - <<'PY'
from pathlib import Path

source = Path("/tmp/requirements.txt.utf16")
for encoding in ("utf-8", "utf-16"):
    try:
        text = source.read_text(encoding=encoding)
        break
    except (UnicodeDecodeError, UnicodeError):
        continue
else:
    raise SystemExit("requirements.txt is neither utf-8 nor utf-16")
Path("/tmp/requirements.txt").write_text(text, encoding="utf-8")
PY

RUN pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt /tmp/requirements.txt.utf16

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . /app

RUN mkdir -p /app/logs /app/media /app/staticfiles

EXPOSE 8000

# Production WSGI server. Dev compose overrides this with runserver.
# GUNICORN_WORKERS can be tuned via environment (default 3).
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --threads 2 --timeout 120 --access-logfile - --error-logfile - LiG.wsgi:application"]

