# CONFIT Backend — Architecture and Conventions

## Stack: FastAPI + SQLAlchemy

The backend uses **FastAPI** with **SQLAlchemy** and a relational database (SQLite by default, PostgreSQL in production). This choice is kept instead of Django for the following reasons:

- **Existing surface**: The API is already implemented in FastAPI (routers, auth, try-on, orders, wardrobe, outfits, brands, stores). Migrating to Django would require a full rewrite of routes, middleware, and dependency injection.
- **Performance and async**: FastAPI is async-native and suits I/O-bound workloads (try-on calls, DB, external APIs). Django’s ASGI support is strong but the codebase was not built with it.
- **Explicit contracts**: Pydantic request/response models and OpenAPI are first-class. This improves maintainability and frontend/backend contracts.
- **Scalability**: FastAPI + SQLAlchemy scales horizontally; the database remains the single source of truth. For very large teams or heavy admin needs, Django’s admin can be added later behind the same DB.

**When to reconsider Django**: If the product later needs built-in admin UI, Django REST Framework–style serializers, or a team that is Django-only, a separate Django app can be introduced that shares the same database and migrations.

---

## Structure (MVC)

- **Routers** (`routers/`): HTTP layer; define endpoints and depend on controllers or services.
- **Controllers** (`controllers/`): Orchestrate use cases; depend on services and translate exceptions to HTTP.
- **Services** (`services/`): Business logic and persistence; receive a DB session via dependency injection and must not hold global mutable state.
- **Models** (`models/`): Pydantic schemas for API request/response. ORM entities live in `database/models.py`.

The database is the single source of truth. All client, brand, and store data is persisted (users, brands, stores, orders, wardrobe, outfits). In-memory caches (e.g. brand metrics) are optional and can be replaced by real aggregates.

---

## Database

- **Config**: `database/config.py` reads `DATABASE_URL` (default: SQLite at `./confit.db`). For production, set `DATABASE_URL` to a PostgreSQL connection string.
- **Session**: Use `get_db()` as a FastAPI dependency. Do not store sessions in globals; pass the session into services.
- **Seed**: `database/seed.py` creates default brands and stores when the DB is empty. It runs automatically after `init_db()` in the app lifespan.
- **Migrations**: Tables are created via `Base.metadata.create_all` on startup. For production, add Alembic and run migrations instead of `create_all`.

---

## Authentication and Registration

- **Registration**: `POST /api/auth/register` creates a user in the database (bcrypt-hashed password). Optional fields (phone, address, style preferences, consent) are stored and returned in the profile.
- **Login**: `POST /api/auth/login` validates credentials against the DB and returns a JWT. Use the `Authorization: Bearer <token>` header for protected routes.
- **Profile**: `GET /api/auth/me` and `PATCH /api/auth/me` read and update the authenticated user. All updates are persisted.
- **Data persistence**: Orders, wardrobe items, outfits, and (for authenticated brand flows) brands and stores are stored in the database and scoped by user or brand.

---

## Try-On

- Virtual try-on calls the IDM-VTON HuggingFace Space via the Gradio client. The client is constructed with `token=...` (HuggingFace token from `HF_TOKEN`). If the Space is down or rate-limited, the API returns 503; the client does not use the deprecated `hf_token` argument.
- Image size limits and processing are defined in `utils/image_utils.py` and `services/tryon_service.py`.

---

## Security

- **Secrets**: Use environment variables (`JWT_SECRET`, `DATABASE_URL`, `HF_TOKEN`, `GROQ_API_KEY`). Never commit secrets.
- **Passwords**: Bcrypt with a salt; no plain-text storage.
- **Authorization**: Protected routes use `require_auth` (JWT). Order, wardrobe, and outfit access are scoped by user id.

---

## Frontend / Backend Separation

The frontend (MVVM) and backend (MVC) live in separate top-level folders (`src/` and `backend/`). The frontend calls the backend over HTTP using the base URL from configuration. No backend code is imported by the frontend build.
