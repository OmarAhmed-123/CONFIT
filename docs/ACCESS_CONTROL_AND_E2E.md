# CONFIT Access Control, Roles, and E2E Guide

This guide explains:
- who uses the system,
- which permissions each role has,
- development test accounts,
- and how to run API/UI validation safely.

## 1) Roles in CONFIT

- `user` (Customer)
  - Can: browse products, use stylist/try-on, manage wishlist/wardrobe/profile, place orders.
  - Cannot: access owner dashboards, admin/debug pages, store analytics management.

- `brand_manager` (Store Owner)
  - Can: access store dashboard, sales analytics, owner notifications, operational insights.
  - Cannot: perform admin-only global/debug operations unless also admin.

- `admin` (Platform Admin)
  - Can: all owner features plus debug/admin monitoring endpoints.
  - Should be limited to trusted internal operators only.

## 2) Development Test Accounts (Local Only)

These are dev-only test identities used for E2E validation:

- Customer
  - Email: `customer.e2e@confit.com`
  - Password: `ConfitTest123`
  - Role: `user`

- Store Owner
  - Email: `owner.e2e@confit.com`
  - Password: `ConfitTest123`
  - Role: `brand_manager`

- Admin
  - Email: `admin.e2e@confit.com`
  - Password: `ConfitTest123`
  - Role: `admin`

Security note:
- Never use these credentials in production.
- Rotate/remove test users outside local/dev environments.

## 3) Frontend Role Detection (Professional Pattern)

Frontend reads role claims from authenticated profile (`/api/auth/me`) and applies centralized helpers:

- `frontend/src/lib/auth/roles.ts`
  - `isCustomer(user)`
  - `isStoreOwner(user)`
  - `isAdmin(user)`
  - `hasAnyRole(user, allowedRoles)`

Do not rely on ad-hoc `localStorage` role strings for authorization logic.

## 4) Backend Authorization Source of Truth

Backend validates JWT and user identity, then resolves roles from DB (`user_roles`).
Role-aware behavior must be enforced server-side for sensitive routes.

Key files:
- `backend/utils/auth_deps.py`
- `backend/services/auth_service.py`
- `backend/database/models.py` (`AppRole`, `UserRole`)

## 5) E2E Validation Coverage

Automated script:
- `backend/scripts/e2e_feature_audit.py`

Output:
- Console pass/fail summary
- JSON artifact: `backend/e2e_feature_audit_report.json`

Validated flows include:
- Customer: auth, products, orders, customer notifications, prefs, analytics overview, stylist, try-on.
- Owner: stores, sales analytics, owner notifications, preference updates, payment config/intent.
- Admin: debug health/alerts/scheduler/logs + analytics metrics.

## 6) UI Route Smoke Validation (Next.js)

For UI route checks in browser:
- Home and major feature pages must return and render without 404.
- Login/register/forgot-password pages must be reachable.
- Store dashboard must require owner/admin role.
- Social auth should request account selection and return to app home (`/`).

## 7) Recommended Permission Matrix

- Customer pages: `/`, `/discover`, `/wishlist`, `/wardrobe`, `/stylist`, `/try-on`, `/checkout`, `/orders`, `/profile`
- Owner pages: `/store-dashboard`, owner notifications, sales analytics routes
- Admin pages: debug/admin operational views and logs

Server still enforces final permission checks even if frontend hides links.
