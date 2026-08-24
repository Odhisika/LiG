"""Test bootstrap for PricePilot.

Registers the merchant-store (`lig`) database alias for the whole test
session so the store-sync tests can use pytest-django's database isolation
(`django_db(databases=["default", "lig"])`) instead of fighting Django's
cached connection settings.

The alias is a throwaway sqlite file; nothing migrates into it (TEST
MIGRATE=False). The three LiG tables the sync engine touches are created
once per session by the `lig_schema` fixture.
"""

import os
import tempfile

import pytest

LIG_TEST_DB = os.path.join(tempfile.gettempdir(), "pricepilot_lig_test.sqlite3")

LIG_SCHEMA = """
CREATE TABLE IF NOT EXISTS category_category (
    id integer PRIMARY KEY,
    category_name varchar(50) NOT NULL UNIQUE,
    slug varchar(100) NOT NULL UNIQUE,
    description text NOT NULL DEFAULT '',
    cat_image varchar(100),
    is_active bool NOT NULL DEFAULT true,
    sort_order integer NOT NULL DEFAULT 0,
    is_featured bool NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS store_product (
    id integer PRIMARY KEY,
    product_name varchar(500) NOT NULL,
    slug varchar(500) NOT NULL UNIQUE,
    description text NOT NULL DEFAULT '',
    short_description varchar(500) NOT NULL DEFAULT '',
    price numeric(10, 2) NOT NULL,
    compare_price numeric(10, 2),
    cost_price numeric(10, 2),
    sku varchar(50) NOT NULL UNIQUE,
    barcode varchar(50) UNIQUE,
    stock integer NOT NULL,
    low_stock_threshold integer NOT NULL DEFAULT 5,
    track_inventory bool NOT NULL DEFAULT true,
    allow_backorders bool NOT NULL DEFAULT false,
    is_available bool NOT NULL DEFAULT true,
    is_featured bool NOT NULL DEFAULT false,
    is_sold bool NOT NULL DEFAULT false,
    requires_shipping bool NOT NULL DEFAULT true,
    is_digital bool NOT NULL DEFAULT false,
    condition varchar(20) NOT NULL DEFAULT 'new',
    meta_title varchar(60) NOT NULL DEFAULT '',
    meta_description varchar(160) NOT NULL DEFAULT '',
    category_id integer NOT NULL REFERENCES category_category(id),
    tags varchar(500) NOT NULL DEFAULT '',
    weight numeric(8, 3),
    dimensions_length numeric(8, 2),
    dimensions_width numeric(8, 2),
    dimensions_height numeric(8, 2),
    images varchar(100),
    created_date datetime NOT NULL,
    modified_date datetime NOT NULL
);
CREATE TABLE IF NOT EXISTS store_productgallery (
    id integer PRIMARY KEY,
    product_id integer NOT NULL REFERENCES store_product(id),
    image varchar(255) NOT NULL,
    alt_text varchar(255) NOT NULL DEFAULT '',
    image_type varchar(20) NOT NULL DEFAULT 'gallery',
    "order" integer NOT NULL DEFAULT 0,
    is_active bool NOT NULL DEFAULT true
);
"""


def _ensure_lig_alias() -> None:
    """Make the `lig` alias exist in settings before pytest-django sets up
    its test databases, so it can create/roll back a test DB for it. The
    store-sync services stay gated by LIG_SYNC_ENABLED, which remains off
    everywhere except the sync tests themselves.
    """
    from django.conf import settings
    from django.db import connections

    if "lig" in settings.DATABASES:
        return
    settings.DATABASES["lig"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": LIG_TEST_DB,
        "TEST": {"NAME": LIG_TEST_DB, "MIGRATE": False},
    }
    # ConnectionHandler caches the normalized DATABASES dict the first time
    # it's accessed. If that cache was already built (e.g. during plugin
    # setup), drop it so the new alias is picked up and its TEST defaults
    # (MIRROR, etc.) get filled in by configure_settings().
    connections.__dict__.pop("settings", None)


_ensure_lig_alias()


@pytest.fixture(scope="session")
def lig_schema(django_db_setup, django_db_blocker):
    """Creates the LiG tables once per session, after pytest-django has
    created the test databases. DDL here happens outside any test's
    transaction, so the tables survive the per-test rollback of their rows.
    """
    from django.db import connections

    with django_db_blocker.unblock():
        conn = connections["lig"]
        with conn.cursor() as cur:
            cur.executescript(LIG_SCHEMA)
    yield
