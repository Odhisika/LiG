from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "django_celery_beat",
    # PricePilot apps
    "apps.common",
    "apps.accounts",
    "apps.dashboard",
    "apps.suppliers",
    "apps.products",
    "apps.pricing",
    "apps.scrapers",
    "apps.scheduler",
    "apps.notifications",
    "apps.analytics",
    "apps.history",
    "apps.discovery",
    "apps.sync",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

USE_POSTGRES = env.bool("USE_POSTGRES", default=False)

if USE_POSTGRES:
    DATABASES = {
        "default": env.db(
            "DATABASE_URL",
            default="postgres://pricepilot:pricepilot@localhost:5432/pricepilot",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Store Sync (apps.sync) ------------------------------------------------
# The merchant's own store (LiG) is a separate Django app with its own
# Postgres. When LIG_DATABASE_URL is set, a second `lig` alias is added and
# the sync engine pushes scraped/computed values into its store_product rows.
# Everything stays off (and harmless) until both LIG_DATABASE_URL and
# LIG_SYNC_ENABLED are set.
if env("LIG_DATABASE_URL", default=""):
    DATABASES["lig"] = env.db("LIG_DATABASE_URL")

DATABASE_ROUTERS = ["apps.sync.router.LigRouter"]

LIG_SYNC_ENABLED = env.bool("LIG_SYNC_ENABLED", default=False)
# Category used when seeding a product whose free-text `category` doesn't
# match an existing LiG category_name/slug. Leave blank to require a match.
LIG_DEFAULT_CATEGORY_SLUG = env("LIG_DEFAULT_CATEGORY_SLUG", default="")
# Default ON: updates push scraped stock into the store. Flip to False if the
# store's own order flow decrements stock and must stay authoritative.
LIG_SYNC_STOCK = env.bool("LIG_SYNC_STOCK", default=True)
# Default ON: download supplier images into MEDIA_ROOT when seeding.
LIG_SYNC_IMAGES = env.bool("LIG_SYNC_IMAGES", default=True)

# Where synced product images land. Point this at the merchant site's media
# directory (e.g. /var/www/LiG/media) when the two apps don't share one.
MEDIA_URL = "media/"
MEDIA_ROOT = env("LIG_MEDIA_ROOT", default=BASE_DIR / "mediafiles")

AUTH_USER_MODEL = "accounts.User"

# --- Cache (used for the scheduler's per-product check lock) -----------
# locmem for zero-setup local dev; Redis when explicitly enabled (Docker
# Compose sets this automatically — see docker-compose.yml). Redis is
# required in production since locmem isn't shared across processes.
USE_REDIS_CACHE = env.bool("USE_REDIS_CACHE", default=False)

if USE_REDIS_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("REDIS_CACHE_URL", default="redis://localhost:6379/1"),
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- REST Framework ---------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.common.api.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "PricePilot API",
    "DESCRIPTION": "Supplier price/stock monitoring and store synchronization.",
    "VERSION": "0.1.0",
}

# --- Celery -------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_ACKS_LATE = True  # re-deliver on worker crash; tasks must be idempotent

CELERY_BEAT_SCHEDULE = {
    "enqueue-due-product-checks": {
        "task": "apps.scheduler.tasks.enqueue_due_product_checks",
        "schedule": 60.0,  # seconds — safe to tighten once product volume is known
    },
    "send-notification-digests": {
        "task": "apps.notifications.tasks.send_pending_digests",
        "schedule": 900.0,  # 15 minutes — batched, not per-event, per the blueprint
    },
    "scan-suppliers-for-new-products": {
        "task": "apps.discovery.tasks.scan_all_suppliers",
        "schedule": 86400.0,  # once a day — new products appear far less often than prices change
    },
    "sync-products-to-store": {
        "task": "apps.sync.tasks.sync_all_to_store",
        "schedule": 86400.0,  # once a day — per-change pushes already keep the store fresh
    },
    "sync-jred-catalog": {
        "task": "apps.scheduler.tasks.sync_jred_catalog_pipeline",
        "schedule": 21600.0,  # every 6 hours — keeps catalog fresh without hammering the API
    },
}

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="notifications@pricepilot.app")

# Owner account used by the automated Jred Catlog import. If unset, the
# importer falls back to the first PricePilot user for backward compatibility.
JRED_CATALOG_OWNER_EMAIL = env("JRED_CATALOG_OWNER_EMAIL", default="")

# --- CORS -----------------------------------------------------------------
# The frontend (frontend/) runs on its own dev server (Vite, default
# port 5173) and talks to this API cross-origin using a JWT in the
# Authorization header — no cookies involved, so CORS_ALLOW_CREDENTIALS
# is deliberately left False.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

# --- Logging --------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
