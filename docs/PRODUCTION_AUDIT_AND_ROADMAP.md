# CONFIT — Production audit & implementation roadmap

**Date:** 2026-03-28  
**Scope:** Honest assessment of the repository vs. a full Paymob/PayPal/Lottie/event-bus refactor.

---

## 1. Audit report (what actually exists)

### Architecture reality (not the aspirational stack only)

| Layer | Location | Role |
|--------|-----------|------|
| **Vite + React** | `src/` | Main storefront UI (Discover, Product, Cart, Checkout, Stripe modal). |
| **Next.js App Router** | `apps/web/` | Auth shell, `/login`, `/callback`, `/app`, BFF-style proxy to upstream API. |
| **Node (Fastify)** | `services/api/` | Commerce, Stripe `PaymentService`, orders, Redis idempotency, JWT auth. |
| **Python (FastAPI)** | `backend/` | Large app (`core/`, `infrastructure/`), Stripe in `routers/payments.py`, orders, catalog API. |
| **Contracts** | `packages/contracts/` | Shared Zod/TS types; must be built (`npm run build:contracts`). |

**Root cause of “two backends”:** The product has **both** FastAPI and Fastify paths. The Vite app proxies `/api` to **Python** (`vite.config.ts` → port `8001` by default). Next.js talks to **Node** (`4000`) for OAuth/session. This is **not** a single unified API — integration work must pick a **source of truth** per domain (catalog vs. auth vs. payments) or add a gateway.

### Payments

- **Implemented:** **Stripe** (PaymentIntent, webhooks-style flows in Python; Stripe in `services/api` `PaymentService`).
- **Not found in repo:** **Paymob**, **PayPal** (no imports/routes). Delivering those requires new provider modules, env keys, HMAC/signature verification, and idempotent webhook handlers — **not** a rename of Stripe.

### OAuth

- Node/Fastify + Next proxy: Google / TikTok / Instagram patterns exist in the auth module; **X (Twitter)** and **Meta** breadth must be verified per provider app registration and callback URLs.
- **Root issue for “real” OAuth:** Misconfigured `AUTH_UPSTREAM_ORIGIN`, provider downtime, or API not running → upstream errors (partially mitigated in `upstream.ts`).

### PDF invoices & event bus

- **No** unified `payment_events` / `invoice_created` dispatcher was located in a quick pass; Python backend may have partial order/payment models — **full event bus + email + PDF** is a **greenfield** subsystem relative to “wire everything.”

### Database

- PostgreSQL vs SQLite: config lives under `backend/core` / `infrastructure` — **must** be validated per environment; mixing ORM models without migrations audit is a deployment risk.

### Frontend “Order Confirmed” / screenshots

- Order UI can show confirmation while **catalog** hits FastAPI with IDs that **do not exist** in the DB → “Product Not Found” if the client treats API 404 as fatal even when **mock catalog** has the product.

---

## 2. Root causes (not symptoms)

| Symptom | Root cause |
|---------|------------|
| Product detail “Not Found” while Discover works | **Logic bug:** API 404 overwrote successful mock product and `selectedColor` in `useEffect` deps refetched unnecessarily. **Fixed** in `useProductViewModel.ts` (prefer mock when API 404; effect depends only on `productId`). |
| `@confit/contracts` missing | **`dist/` not built** — use `npm run build:contracts` / `prepare` script. |
| Dual payment stacks | **Stripe** chosen in both Python and Node; **no** Paymob/PayPal implementation. |
| Complexity | **Three** frontends (Vite, Next, marketing) and **two** API styles without a documented boundary. |

---

## 3. Refactor strategy (recommended order)

1. **Freeze boundaries:** Document which client calls which API (table in README). Point all checkout/payment either to Fastify **or** FastAPI, not both.
2. **Payments:** Add `PaymobProvider` / `PayPalProvider` behind a shared interface on the **chosen** backend only; shared DB tables `payments`, `payment_events` with idempotency keys.
3. **Webhooks:** Signature verification + replay table before order transition.
4. **Invoices:** After `payment_success`, enqueue job (Celery/RQ/BullMQ) → PDF → store path → `invoice_created` event → email template.
5. **OAuth:** One token/session issuer; validate redirect URIs against allowlist env.
6. **Next.js:** Lottie wrapper components for loading/success/error; reuse design tokens from Vite where possible.

---

## 4. Fix applied in this pass (code)

- **`src/viewmodels/useProductViewModel.ts`:** API **404** no longer clears a valid **mock** product; **removed `selectedColor` from effect deps** to avoid spurious reloads; loading state ends in `finally` only.

---

## 5. Verification checklist (short)

- [ ] `npm run build:contracts` succeeds; API starts without `ERR_MODULE_NOT_FOUND` for contracts.
- [ ] Open `/product/<id>` for an id that exists in mock but not in Python DB → page still shows product.
- [ ] Stripe keys set → checkout completes; webhook/order row matches.
- [ ] Decide Paymob vs PayPal API version + sandbox; implement providers + env (future PR).

---

## 6. Production readiness

**Status: NEEDS ATTENTION** — Stripe paths exist; Paymob/PayPal/event bus/PDF/OAuth breadth are **not** fully implemented as specified. Use this doc as the sprint backlog for remaining work.
