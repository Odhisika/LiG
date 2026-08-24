# PricePilot — Step-by-Step Implementation Plan

## Build Philosophy

Build a **walking skeleton first**: one supplier, one product, one full
pass through scrape → detect → sync → notify. Prove the pipeline before
generalizing it. Every phase below is ordered so that each step produces
something runnable and testable — never a half-finished abstraction.

Within each phase: **models → services → tasks → API → tests → docs**.
Views/serializers stay thin; business logic lives in `services.py` per the
blueprint's own coding standards.

---

## Milestone 0 — Repo & Infrastructure (Day 1)

1. **Django project skeleton**
   - `django-admin startproject pricepilot`
   - Create apps: `accounts, dashboard, suppliers, products, pricing, scrapers, scheduler, notifications, analytics, history, common`
   - Split settings: `settings/base.py`, `dev.py`, `prod.py`
2. **Docker Compose**: Postgres, Redis, Django, Celery worker, Celery beat — even before you deploy anywhere, this keeps dev/prod parity.
3. **Tooling**: `black`, `ruff`/`flake8`, `mypy` (type hints are a stated standard), `pytest-django`, `drf-spectacular` for OpenAPI docs.
4. **CI skeleton**: GitHub Actions running lint + tests on every push. Cheap to add now, expensive to retrofit later.
5. **`common` app**: base model (`created_at`, `updated_at`, soft-delete if you want "never delete important data"), base service class, custom exceptions, standard API response/error envelope.

**Definition of done:** `docker compose up` gives you a working Django app hitting Postgres, with one passing dummy test and CI green.

---

## Phase 1 — Foundation

### Step 1.1 — Authentication (`accounts`)
- Custom user model (email-based login is friendlier for a SaaS than username).
- Register / login / logout / password reset via DRF + JWT (`djangorestframework-simplejwt`).
- Email verification can be a stub (flag on user) until Phase 4 hardening.
- Tests: registration flow, login, token refresh, permission denial on protected routes.

### Step 1.2 — Suppliers (`suppliers`)
- Model: `name, website, country, currency, default_scraper, rate_limit_per_minute, is_active`.
- CRUD API + serializers.
- Service layer: `SupplierService.create()`, validation (unique per merchant, valid URL).
- Tests: CRUD, validation errors.

### Step 1.3 — Products (`products`)
- Model: `name, supplier (FK), supplier_url, sku, supplier_price, selling_price, currency, stock, status, images (JSON or related model), description, category, check_frequency_minutes, last_checked_at`.
- CRUD API scoped to the owning merchant (row-level ownership check now — it pays off in Phase 4 multi-tenancy).
- Tests: CRUD, ownership isolation (user A can't see user B's products).

### Step 1.4 — Minimal Scraper (`scrapers`) — walking-skeleton core
- `scrapers/base.py`: abstract `BaseScraper` with `fetch(url) -> ScrapedProduct` returning `{price, stock, title, images, description, currency}` as a typed dataclass/Pydantic model — **not** a raw dict, so downstream code gets type safety.
- Write **one concrete scraper** against a real target site using Playwright (headless).
  - Check that site's robots.txt / ToS before building against it — pick a target you're legally comfortable scraping, or one with an official API instead.
- `ScraperRegistry` mapping `default_scraper` string → class, so Product Management can select a scraper without hardcoding imports.
- Tests: scraper against a saved HTML fixture (never hit the live site in CI — flaky and possibly against ToS).

### Step 1.5 — Dashboard (skeleton only)
- One endpoint returning counts (`products_monitored`, `changes_today`, `failed_scrapes_today`) — real numbers will populate once Phase 2 tasks are running. Don't build the chart endpoints yet; there's no history data to chart.

**Phase 1 exit criteria:** you can create a supplier, add a product against it, manually trigger the scraper via a management command, and see a `ScrapedProduct` result printed. Nothing automatic yet — that's Phase 2.

---

## Phase 2 — Automation

### Step 2.1 — Scheduler (`scheduler`)
- Celery + Celery Beat wired up.
- `DynamicPeriodicTask` per product (using `django-celery-beat`) driven by each product's `check_frequency_minutes`, OR a single beat task every N minutes that enqueues "due" products (simpler to start, scales fine to Version 1/2 targets in the blueprint).
- Idempotency: task keyed so a re-run for the same product+timestamp doesn't double-write history (blueprint explicitly requires idempotent jobs).

### Step 2.2 — Price Monitor Engine (`products` + `scrapers` + `history`)
- `PriceMonitorService.check_product(product_id)`:
  1. Load product, resolve its scraper via registry.
  2. Call scraper, get `ScrapedProduct`.
  3. Compare price/stock/description against stored values.
  4. If changed → write `PriceHistory` row (old, new, diff, timestamp, reason="scrape") and call `SyncService`.
  5. Always log the run (`ScrapeLog`: started_at, finished_at, duration, result, failure_reason, retry_count) — "nothing should fail silently."
- Retry policy: Celery autoretry with backoff on scrape failure; after N failures mark product `status=scrape_failed` and let notifications pick it up.

### Step 2.3 — Stock Monitoring
- Same pipeline as price, just another compared field — implement inside the same `check_product` pass rather than a separate job (one scrape, multiple comparisons).

### Step 2.4 — Synchronization Engine (`history` triggers this via `products`)
- `SyncService.apply_change(product, changes)`:
  1. Update Product row inside a DB transaction (blueprint requires transactions for critical updates).
  2. Clear any relevant cache keys.
  3. Confirm history row exists.
  4. Enqueue notification event (don't send inline — decouple via a task/event so a slow email provider never blocks the sync).

### Step 2.5 — History (`history`)
- Already partially built in 2.2 — now add the read API: list/filter by product, date range, and a diff view (old vs new).

**Phase 2 exit criteria:** leave the system running for an hour against a couple of real products; verify PriceHistory fills in, dashboard counts move, and a forced scrape failure shows up in ScrapeLog without crashing the worker.

---

## Phase 3 — Intelligence

### Step 3.1 — Pricing Engine (`pricing`)
- Model a `PricingRule` as a small rule chain rather than free-text formula, e.g. ordered `PricingRuleStep(type: markup_pct | flat_fee | shipping | tax | fx_convert, value)`. This maps directly to the three examples in the blueprint (simple markup, cost-plus, FX-adjusted) without needing a formula parser.
- `PricingService.compute_selling_price(product, rule)` — pure function, easy to unit test with table-driven tests covering each rule type.
- Wire into `SyncService`: when supplier price changes, recompute selling price via the product's assigned rule before updating the store.

### Step 3.2 — Notifications (`notifications`)
- Channel abstraction (`NotificationChannel.send(event)`), concrete channels: Email first (simplest), then Telegram/Slack/WhatsApp as separate adapters — same plugin pattern as scrapers.
- Event types from the blueprint: products updated (batch digest, not one email per product), out-of-stock, supplier unavailable, scraper failed.
- Batch digests via a periodic task (e.g. every 15 min, summarize pending events) rather than firing one notification per change — this avoids inbox spam once you're past a handful of products.

### Step 3.3 — Analytics (`analytics`)
- Now that history has real volume, build the read-model queries: most-volatile supplier, average daily changes, largest increase/decrease, profit impact (selling price vs supplier price trend).
- These can be plain aggregate queries first; only add a materialized/summary table if query performance becomes a real issue at your actual data volume.

**Phase 3 exit criteria:** a price change flows all the way through: scrape → pricing rule recompute → sync → batched notification → visible in analytics.

---

## Phase 4 — Enterprise

### Step 4.1 — Multi-tenancy
- Decide the model early: shared schema with `tenant_id` FK on every row (simpler, matches your Version 1–3 scaling goals) vs schema-per-tenant (more isolation, more ops overhead). For a dropshipper SaaS, shared schema + row-level scoping is almost certainly the right call.
- Retrofit tenant scoping into a `TenantScopedManager` used by all Phase 1–3 models — the ownership checks you added in Step 1.3 make this a mechanical change, not a rewrite.

### Step 4.2 — Team accounts & Billing
- Roles: owner/admin/member per tenant.
- Billing via Stripe (subscriptions tied to plan limits — product count, check frequency floor, etc.).

### Step 4.3 — Public API & Webhooks
- API keys scoped per tenant, rate-limited.
- Outbound webhooks for the same event types notifications already model (products_updated, out_of_stock, etc.) — reuse the event bus from Step 3.2.

### Step 4.4 — AI Insights
- Start with the two examples in the blueprint as scheduled analytics jobs, not live LLM calls: "this supplier tends to raise prices on Fridays" is a statistical pattern over `PriceHistory`, not something that needs a model. Reserve actual AI/LLM calls for genuinely unstructured tasks (e.g. summarizing why a scrape keeps failing) once the deterministic version is live.

---

## Cross-Cutting, Applied Continuously (Not a Separate Phase)

- **Testing**: unit tests per service method, integration tests per API endpoint, one end-to-end test per phase's "exit criteria" scenario.
- **Security**: rate limiting on scrape triggers and public API, secrets via env vars from day one, audit log on every Product/PricingRule change (who/when/what).
- **Logging**: structured logs (JSON) from the start — much easier to wire into a log aggregator later than to retrofit.
- **Docs**: `drf-spectacular` OpenAPI schema kept current every phase, not bolted on at the end.

---

## Suggested Milestone Order (if you want a timeline)

| Milestone | Scope | Rough effort |
|---|---|---|
| M0 | Infra + skeleton | 2–3 days |
| M1 | Phase 1 complete, walking skeleton working | 1–2 weeks |
| M2 | Phase 2 complete, running unattended | 1–2 weeks |
| M3 | Phase 3 complete | 1–2 weeks |
| M4 | Phase 4 (start once you have real paying users, not before) | ongoing |

Treat M4 as demand-driven, not calendar-driven — multi-tenancy and billing are expensive to build speculatively and cheap to retrofit onto a shared-schema design if Step 4.1's advice is followed.







 Email: demo@pricepilot.test
- Password: DemoPass!2026
- Name: Demo User