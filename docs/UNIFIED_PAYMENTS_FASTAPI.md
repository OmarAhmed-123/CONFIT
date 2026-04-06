# Unified payments (FastAPI) — Paymob, PayPal, Stripe

**Source of truth:** `backend/routers/payment_platform.py` + `backend/services/payment_platform/`.

Legacy **unchanged:** `POST /api/payments/intent`, `POST /api/payments/confirm` (Stripe).

## New endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/payments/unified/session` | Create ledger row + provider session (`stripe` \| `paymob` \| `paypal`) |
| POST | `/api/payments/unified/webhooks/paymob` | Paymob transaction callback (HMAC verified) |
| POST | `/api/payments/unified/webhooks/paypal` | PayPal webhook (signature verify API) |
| POST | `/api/payments/unified/paypal/capture` | Capture after buyer returns from PayPal |
| GET | `/api/invoices/{invoice_id}` | PDF download (auth required when invoice has `user_id`) |

**Headers:** `X-Idempotency-Key` optional on `session` (deduplicates provider calls).

## Environment variables

### Stripe (existing)

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`

### Paymob

| Dashboard / email | Environment variable |
|-------------------|----------------------|
| **API Key** (long JWT under Authentication) | `PAYMOB_API_KEY` |
| **Integration ID** (e.g. `5592981` on the integration) | `PAYMOB_INTEGRATION_ID` |
| **HMAC** (hex or string from Developers / integration security) | `PAYMOB_HMAC_SECRET` |
| **Secret key** (`egy_sk_test_…` / `egy_sk_live_…`) if HMAC field is not used alone | `PAYMOB_SECRET_KEY` (optional fallback for webhook HMAC verification) |
| **Public key** (`egy_pk_test_…`) | `PAYMOB_PUBLIC_KEY` (optional; echoed in session JSON for client/SDK) |
| **Iframe ID** (number in the hosted iframe URL path) | `PAYMOB_IFRAME_ID` |

Also:

- `PAYMOB_IFRAME_URL` (optional, default `https://accept.paymob.com/api/acceptance/iframes`)
- `PAYMOB_BASE_URL` (optional, default `https://accept.paymob.com/api`)

**Where custom HTML/CSS lives:** The “Installment / Discount Iframe” and “My new card Iframe” templates are **only** edited in the Paymob dashboard (integration → iframe customization). They are not copied into this repository.

**Webhooks:** In the Paymob integration, set **Transaction response callback** (or equivalent) to your **public HTTPS** backend URL, for example:

`https://api.yourdomain.com/api/payments/unified/webhooks/paymob`

The default URLs under `accept.paymobsolutions.com` shown in the dashboard are Paymob’s processors; your **merchant** callback must still point to the route above so FastAPI can verify HMAC and update orders.

**Other credentials (Client ID / “Secret key 1” under an app name):** Those belong to **other Paymob products** (e.g. OAuth / mobile). The Accept **server** flow only needs the variables in the table above.

**Security:** Store all secrets in `.env` or a secrets manager. Never commit real keys. If keys were shared in chat or tickets, **rotate** them in the Paymob dashboard.

Session body includes `billing` dict; use `currency` (e.g. `EGP`) inside `billing` for Paymob.

### PayPal

| PayPal Developer Dashboard | Environment variable |
|---------------------------|----------------------|
| **Client ID** (Sandbox or Live app) | `PAYPAL_CLIENT_ID` |
| **Secret** (same application) | `PAYPAL_CLIENT_SECRET` |
| Use **Sandbox** credentials → `PAYPAL_MODE=sandbox`; **Live** → `PAYPAL_MODE=live` | `PAYPAL_MODE` |
| **Webhooks** → create listener URL `https://YOUR_HOST/api/payments/unified/webhooks/paypal` → **Webhook ID** | `PAYPAL_WEBHOOK_ID` |

**Code paths:** `paypal_provider.py` reads these env vars only. They are **not** shared with Paymob — use the PayPal Developer portal (`developer.paypal.com`), not Paymob.

**Unified session (`provider: "paypal"`):** requires `paypal_return_url` and `paypal_cancel_url` in the JSON body. After the buyer approves on PayPal, call `POST /api/payments/unified/paypal/capture` with the PayPal order id. `PAYPAL_WEBHOOK_ID` is required for **incoming webhooks** (signature verification); capture can still complete the order if your frontend calls the capture endpoint after redirect.

### Invoices

- `INVOICE_STORAGE_DIR` (optional; default `backend/storage/invoices`)

## Database

Run Alembic from `backend/`:

```bash
alembic upgrade head
```

Adds tables: `payments`, `payment_transactions`, `payment_events`, `invoices`.

## Node / Next.js

Fastify Stripe routes remain for existing clients; **new** providers should call **Python** unified API only. See comment in `services/api/src/modules/commerce/routes.ts`.

## Events (in-process)

`payment_success`, `payment_failed`, `invoice_created` are published on the internal bus (`event_bus.py`). For heavy load, replace dispatch with Celery/Redis using the same event names.
