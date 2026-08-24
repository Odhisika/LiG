# PricePilot

Intelligent platform that monitors supplier websites and automatically
synchronizes pricing, stock, and product info with a merchant's store.

See `PricePilot_Implementation_Plan.md` for the full phased build plan
this repo follows.

## Status

**Phase 1 (Foundation) — complete. Phase 2 (Automation) — complete. Phase 3 (Intelligence) — complete.** All of the original four-phase plan's Phase 1–3 scope is built and tested, **plus two features beyond the original blueprint: automatic Product Discovery, and a React frontend** (see below and `frontend/README.md`). Only Phase 4 (Enterprise: multi-tenancy, billing, public API/webhooks, AI insights) remains, and the roadmap explicitly treats that as demand-driven, not calendar-driven.

- Custom email-based `User` model (`apps/accounts`)
- JWT register/login/refresh/me endpoints
- Supplier CRUD, scoped per owner, with soft-delete (`apps/suppliers`)
- Product CRUD, scoped per owner, FK to Supplier with cross-owner protection
  (`apps/products`)
- Scraper framework (`apps/scrapers`): `BaseScraper` interface,
  `ScraperRegistry`, and a working `CatlogScraper` targeting Catlog-hosted
  storefronts (like jredtechnologiesltd.com) — see "Scraper notes" below
- Dashboard summary endpoint (`apps/dashboard`)
- Scheduler (`apps/scheduler`): Celery Beat runs a scale-aware due-product
  query every 60s and enqueues checks, with a Redis-backed lock against
  double-enqueueing
- Price Monitor Engine + Sync Engine (`PriceMonitorService` in
  `apps/products/services.py`): scrapes, compares, and — only on an actual
  change — writes a `PriceHistory` row and updates the Product inside a
  transaction, with retry-then-mark-failed handling
- History (`apps/history`): immutable, append-only change log + read API
- Pricing Engine (`apps/pricing`): `PricingRule` as an ordered chain of
  typed steps (markup %, flat fee, shipping, tax, FX conversion);
  `PriceMonitorService` recomputes `selling_price` automatically whenever a
  scrape detects a price change on a product with a rule assigned
- Notifications (`apps/notifications`): a `NotificationChannel` abstraction
  with a working `EmailChannel`, batching events into one digest per owner
  every 15 minutes rather than firing per-change
- Analytics (`apps/analytics`): pure read-only aggregation over
  `PriceHistory`/`Product` — the blueprint's Module 11 questions, all in one
  `GET /api/analytics/summary/` call: most-active suppliers, most-volatile
  products, largest price increases/decreases, average daily changes, and
  current profit impact (total/average margin across products with both a
  supplier price and selling price set). Takes `?days=` and `?limit=` query
  params with validation (days must be positive, limit capped at 100). No
  new models — like Dashboard, it's a query layer over data other services
  already write, so there was nothing new to migrate.
- **Product Discovery (`apps/discovery`)**: detects new products on a
  supplier's storefront that aren't tracked yet, for one-click import — see
  "Discovery notes" below for the design and what's unverified.
- **Frontend (`frontend/`)**: a React (Vite) UI covering every page —
  login/register, dashboard, suppliers, products, discoveries (with the
  one-click import), pricing rules (with a dynamic ordered-step builder),
  history, notifications, and analytics. JWT auth with silent refresh-on-401.
  CORS configured on the backend (`django-cors-headers`) for the frontend's
  dev-server origin. See `frontend/README.md`.
- Service layer + domain exceptions + consistent API error envelope (`apps/common`)
- `USE_POSTGRES` and `USE_REDIS_CACHE` toggles: sqlite + in-process cache by
  default for local dev, Postgres + Redis when enabled (Docker Compose sets
  both automatically; set them explicitly in production)
- OpenAPI docs at `/api/docs/`
- 227 passing tests — **run against both sqlite and real Postgres**

## What "Sync Engine" means today

The blueprint's Module 8 (Synchronization Engine) diagram is "Update Store
Database → Clear Cache → Log History → Notify Merchant." Right now the
"store" being synced *is* PricePilot's own Product row — there's no external
merchant store integration yet (that's Phase 4 scope: pushing changes out to
Shopify/WooCommerce/etc.). "Notify Merchant" is Phase 3. So today's Sync
Engine is genuinely just the transactional Product update inside
`PriceMonitorService.check_product()` — it'll grow real external-sync and
notification steps as those phases land, without needing a redesign, since
the transaction boundary and the "only touch things when something actually
changed" logic are already in place.

## A real bug caught along the way

The scheduler's due-product query multiplies `check_frequency_minutes` by a
`timedelta` at the database level. On sqlite, Django's ORM rejects that
multiplication for a `PositiveIntegerField` specifically — its internal type
name isn't in the small set Django allows for temporal arithmetic — while
the same query works fine on Postgres. Fixed by casting the field to a plain
`IntegerField` before the multiplication (`apps/scheduler/tasks.py`). The
full suite (all 100 tests, including this one) is verified to pass against
both databases, not just whichever one happened to be configured locally.

## Scraper notes

`CatlogScraper` targets storefronts built on **Catlog**, a Nigerian
social-commerce platform — confirmed against a real product page from
jredtechnologiesltd.com. Key design decisions:

- **Playwright, not a plain HTTP GET.** Catlog pages are a client-rendered
  Next.js app — title/description/image are in server-rendered `og:*` meta
  tags, but price and stock are populated after JS hydration.
- **Price is parsed from the displayed price text**, not a scraped internal
  API number. Catlog integrates Paystack, whose APIs represent money in kobo
  (1/100 of the display unit) — trusting a raw API number risks a silent
  100x error. The rendered text is what the merchant and customer actually
  see.
- **Parsing logic (`CatlogScraper.parse()`) is fully unit-tested against
  fixtures** without needing a real browser. Only `fetch()` (the thin
  Playwright driver) needs live internet access.
- **Validate against the live site yourself**: this sandbox can't reach
  arbitrary external domains, so the browser-launch path is untested against
  the real site from here. Run:
  ```bash
  docker compose exec web python manage.py inspect_scrape \
    "https://www.jredtechnologiesltd.com/products/apc-easy-1000va-smv1000imsx-ups-1-ph-line-interactive-1783075304676-2r5"
  ```
  and compare the output to the real page. If price/stock aren't detected,
  the regex patterns in `apps/scrapers/catlog.py` (`_PRICE_PATTERNS`,
  `_STOCK_COUNT_RE`, etc.) are the place to tune — send me the command's
  output and I'll adjust them precisely.

## Discovery notes

`apps/discovery` scans a supplier's `catalog_url` (defaults to `website` —
for a Catlog store, the homepage usually *is* the catalog) for product URLs
not already tracked, and lets you one-click import them as real Products.

- **URL discovery, not grid scraping.** `CatlogScraper.discover_product_urls()`
  matches the `/products/` URL segment — confirmed structural, from two real
  pages of yours — rather than parsing a listing grid's CSS classes, which
  I've never been able to inspect directly (same sandbox limitation as the
  original scraper). This is deliberately the *only* thing extracted from
  the catalog page.
- **Preview data comes from the already-proven per-product `fetch()`**, not
  from parsing the grid. Once a new URL is found, PricePilot fetches that
  one product page the normal way to get title/price/image — reusing logic
  that's already validated, rather than adding a second, less-certain
  parsing path.
- **A failed preview fetch still records the URL** — with less information,
  but still reviewable — since the URL itself is real and useful even if a
  preview couldn't be generated.
- **Unverified from this sandbox**: whether `/products/` links actually
  appear in the rendered homepage HTML the way the design assumes. This has
  the same caveat as the original scraper — run it for real once you're in
  Docker:
  ```bash
  docker compose exec web python manage.py shell -c "
  from apps.suppliers.models import Supplier
  from apps.discovery.services import DiscoveryService
  supplier = Supplier.objects.get(name='<your supplier name>')
  print(DiscoveryService.scan_supplier(supplier))
  "
  ```
  then check `DiscoveredProduct.objects.all()` in the admin or via
  `GET /api/discoveries/`. If it finds zero URLs on a store you know has
  products, the homepage likely isn't the actual catalog page — set
  `catalog_url` on the Supplier explicitly, or send me what the rendered
  homepage HTML actually looks like and I'll adjust the matching logic.

## Quickstart (Docker — recommended)

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres, Redis, the Django app, a Celery worker, Celery beat,
and the React frontend.

- Frontend: http://localhost:5173/ ← **start here** if you just want to
  click around
- API: http://localhost:8000/api/
- Docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

Run migrations and create a superuser (once containers are up):

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Then open http://localhost:5173/ and either register a new account through
the UI or log in with the superuser you just created. See
`frontend/README.md` for more on the frontend specifically, including how
to run it standalone without Docker.

## Quickstart (local, no Docker)

Requires Python 3.12, Postgres, and Redis running locally.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt
playwright install --with-deps chromium

cp .env.example .env   # defaults to sqlite (USE_POSTGRES=False) — edit if you want Postgres locally
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

sqlite is the default in `.env.example`, so this path needs no Postgres/Redis
setup at all to explore the API. Set `USE_POSTGRES=True` plus `DATABASE_URL`
when you want to test against real Postgres locally.

## Running tests

```bash
pytest                 # all tests
pytest --cov=apps      # with coverage
ruff check .            # lint
black --check .         # format check
```

## API quick reference (current)

| Method | Path                  | Auth | Purpose                  |
|--------|-----------------------|------|---------------------------|
| POST   | `/api/auth/register/` | No   | Create a merchant account |
| POST   | `/api/auth/login/`    | No   | Get access/refresh tokens |
| POST   | `/api/auth/refresh/`  | No   | Refresh an access token   |
| GET    | `/api/auth/me/`       | Yes  | Current user profile      |
| GET    | `/api/suppliers/`     | Yes  | List your suppliers       |
| POST   | `/api/suppliers/`     | Yes  | Create a supplier         |
| GET    | `/api/suppliers/{id}/`| Yes  | Get one supplier          |
| PATCH  | `/api/suppliers/{id}/`| Yes  | Update a supplier         |
| DELETE | `/api/suppliers/{id}/`| Yes  | Soft-delete a supplier    |
| GET    | `/api/products/`      | Yes  | List your products (filter: `?status=`, `?supplier=`) |
| POST   | `/api/products/`      | Yes  | Create a product against your own supplier |
| GET    | `/api/products/{id}/` | Yes  | Get one product           |
| PATCH  | `/api/products/{id}/` | Yes  | Update a product          |
| DELETE | `/api/products/{id}/` | Yes  | Soft-delete a product     |
| GET    | `/api/dashboard/summary/` | Yes | Headline counts for the current user |
| GET    | `/api/history/`       | Yes  | List change history (filter: `?product=`, `?date_from=`, `?date_to=`) |
| GET    | `/api/history/{id}/`  | Yes  | Get one history entry     |
| GET    | `/api/pricing-rules/` | Yes  | List your pricing rules   |
| POST   | `/api/pricing-rules/` | Yes  | Create a rule with ordered steps |
| GET    | `/api/pricing-rules/{id}/` | Yes | Get one rule (includes `steps_display`) |
| PATCH  | `/api/pricing-rules/{id}/` | Yes | Update a rule; `steps` (if included) fully replaces the chain |
| DELETE | `/api/pricing-rules/{id}/` | Yes | Soft-delete a rule |
| GET    | `/api/notifications/` | Yes  | List your notification events (filter: `?event_type=`, `?sent=`) |
| GET    | `/api/analytics/summary/` | Yes | Aggregate stats (filter: `?days=`, `?limit=`) |
| GET    | `/api/discoveries/`   | Yes  | Your discovery review queue (filter: `?status=`) |
| POST   | `/api/discoveries/{id}/import/` | Yes | One-click import as a real Product (optional overrides in body) |
| POST   | `/api/discoveries/{id}/dismiss/` | Yes | Dismiss a discovered URL (won't resurface on future scans) |

Every response is shaped `{"data": ..., "error": ...}` — see
`apps/common/api.py`.

## Project layout

```
config/                 Django project (settings/, urls.py, celery.py)
apps/
  common/                Base model, exceptions, API envelope — shared by all apps
  accounts/               DONE — auth
  suppliers/               DONE — supplier CRUD
  products/                 DONE — product CRUD + Price Monitor/Sync Engine
  scrapers/                   DONE — scraper framework + CatlogScraper
  dashboard/                    DONE — summary endpoint
  scheduler/                      DONE — Celery Beat due-product scheduling
  history/                          DONE — immutable change log + read API
  pricing/                            DONE — ordered pricing rules + engine
  notifications/                        DONE — batched digests, email channel
  analytics/                              DONE — aggregate read-only stats
  discovery/                                DONE — new-product detection + import
requirements/            base.txt / dev.txt / prod.txt
docker-compose.yml       Postgres, Redis, web, worker, beat
```

## What's left — Phase 4 (Enterprise), plus one real to-do

Everything in the original four-phase plan's Phase 1–3 is built, plus
Product Discovery (beyond the original blueprint). What formally remains is
Phase 4, which the roadmap explicitly treats as demand-driven rather than
calendar-driven — build it when there's a real user/business need, not
speculatively:

- **Multi-tenancy**: shared-schema + `tenant_id` scoping is the recommended
  approach (see the implementation plan) — mechanical to retrofit since
  every model is already owner-scoped consistently.
- **Team accounts**: roles (owner/admin/member) per tenant.
- **Billing**: Stripe subscriptions tied to plan limits (product count,
  minimum check frequency, etc.).
- **Public API + webhooks**: API keys scoped per tenant, rate-limited;
  outbound webhooks reusing the same event types notifications already model.
- **AI insights**: the blueprint's own examples ("this supplier tends to
  raise prices on Fridays") are statistical patterns over `PriceHistory` —
  start as scheduled analytics jobs, not live LLM calls; reserve actual AI
  for genuinely unstructured tasks.
- **Multi-language / multi-currency** UI and formatting.

**More pressing than any of that**: two things have been flagged repeatedly
across this build and neither has actually been run against the live site
yet, since this sandbox has no access to arbitrary external domains —

1. `inspect_scrape` against a real product URL, to confirm `CatlogScraper`
   extracts the right price/stock from the live page (see "Scraper notes").
2. `DiscoveryService.scan_supplier()` against the real homepage, to confirm
   product links actually get found the way the design assumes (see
   "Discovery notes").

Both are five-minute checks once you're running this in Docker with real
internet access, and both are worth doing before trusting this to run
unattended — everything downstream of them has only ever been tested
against mocked scraper output, which proves the pipeline logic is correct
but not that the scraper itself matches today's live page.
