# PricePilot Frontend

A React (Vite) UI for the PricePilot API — login/register, and a page for
every domain: Dashboard, Suppliers, Products, Discoveries, Pricing Rules,
History, Notifications, Analytics.

## Quickstart (Docker — recommended)

From the repo root, this is already wired into the main `docker-compose.yml`:

```bash
docker compose up --build
```

Then open http://localhost:5173/. Register a new account, then start
adding suppliers and products.

## Quickstart (local, no Docker)

Requires Node 18+.

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173/. The backend must already be running and
reachable at the URL in `.env` (`VITE_API_BASE_URL`, defaults to
`http://localhost:8000/api`) — see the main README for backend setup. The
quickest path: run the backend with sqlite (`USE_POSTGRES=False`) in one
terminal, this frontend in another.

## What each page does

- **Dashboard** — headline counts (products monitored, suppliers, average
  profit, today's activity).
- **Suppliers** — add/edit/delete suppliers, set the scraper and catalog URL.
- **Products** — add/edit/delete tracked products, assign a pricing rule.
- **Discoveries** — review new products found automatically on a supplier's
  catalog page; one-click import (with optional overrides) or dismiss.
- **Pricing Rules** — build an ordered chain of pricing steps (markup %,
  flat fee, shipping, tax, FX conversion) and assign it to products.
- **History** — the immutable price/stock change log, filterable by product.
- **Notifications** — the event log that feeds the batched digest emails.
- **Analytics** — most-active suppliers, most-volatile products, largest
  price swings, and profit impact, over a selectable time window.

## How auth works

JWT access/refresh tokens, stored in `localStorage`. The API client
(`src/api/client.js`) attaches the access token to every request and
automatically does one silent refresh-and-retry on a 401 before giving up
and sending you back to `/login`.

## Build for production

```bash
npm run build
```

Outputs static files to `dist/` — serve these with any static file host or
behind the same reverse proxy as the backend. Set `VITE_API_BASE_URL` to
your real API's URL before building (Vite bakes env vars in at build time).

## Notes

- No UI kit — hand-rolled CSS (`src/index.css`) to keep the dependency list
  small. Dark theme by default.
- No client-side state management library — plain `useState`/`useEffect`
  per page. Straightforward at this size; worth reconsidering if the app
  grows substantially.
- Forms are deliberately plain (no form library) for the same reason.
