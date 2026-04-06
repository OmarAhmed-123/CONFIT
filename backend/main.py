"""
CONFIT Backend - Main Application Entry Point
================================================
FastAPI server that hosts the Virtual Try-On and Virtual Stylist APIs.
Designed to be extensible — add new routers in the routers/ folder.

Usage:
    python main.py
    # or
    uvicorn main:app --reload --host 127.0.0.1 --port 8001

Production Docker images run: uvicorn main:app (see Dockerfile).
For the alternate app stack (app.py, /api/v1), see ARCHITECTURE.md at repo root.
"""

import errno
import os
import socket
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Callable, Awaitable

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import inspect

from core.config import settings
from core.exceptions import register_exception_handlers
from core.slowapi_limiter import limiter
from core.api_response import ok, fail

try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    HAS_SLOWAPI = True
except ImportError:
    HAS_SLOWAPI = False

# Load environment variables from backend/.env (explicit path; not dependent on CWD)
load_dotenv(dotenv_path=str(Path(__file__).resolve().parent / ".env"))

# ── Logging Configuration ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("confit-backend")


# ── App Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("  CONFIT Backend Starting...")
    logger.info("=" * 60)

    # Log configuration status (read from environment only — never embed secrets in source)
    hf_token = os.getenv("HF_TOKEN")
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    lovable_key = os.getenv("LOVABLE_API_KEY")
    fashn_key = os.getenv("FASHN_API_KEY")

    logger.info(f"  HuggingFace Token: {'Configured' if hf_token else 'Not set (optional)'}")
    try:
        import mediapipe as _mp  # noqa: F401

        _sol = hasattr(_mp, "solutions") and hasattr(_mp.solutions, "pose")
        try:
            from mediapipe.tasks.python import vision as _mpv  # noqa: F401

            _tasks = True
        except Exception:
            _tasks = False
        if _sol:
            logger.info("  MediaPipe:         ready (solutions pose + legacy selfie)")
        elif _tasks:
            logger.info(
                "  MediaPipe:         Tasks API (PoseLandmarker + ImageSegmenter); "
                "first run downloads models to ~/.cache/confit_mediapipe"
            )
        else:
            logger.warning("  MediaPipe:         package incomplete — install mediapipe")
    except ImportError:
        logger.warning(
            "  MediaPipe:         NOT installed — classical try-on uses CPU GrabCut fallback; "
            "install with: pip install mediapipe"
        )
    logger.info(f"  Groq API Key:      {'Configured' if groq_key else 'Not set (rule-based fallback)'}")
    if fashn_key or gemini_key or lovable_key:
        _tryon_providers = "+".join(
            p
            for p, ok in (
                ("FASHN", fashn_key),
                ("Gemini", gemini_key),
                ("Lovable", lovable_key),
            )
            if ok
        )
        logger.info(f"  Try-on cloud:      {_tryon_providers}")
    else:
        logger.info(
            "  Try-on cloud:      not set (set FASHN_API_KEY or GEMINI_API_KEY for neural try-on)"
        )
    _oai = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
    _ds = os.getenv("DEEPSEEK_API_KEY")
    _anth = os.getenv("ANTHROPIC_API_KEY")
    _goo = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    logger.info(f"  OpenAI:            {'Configured' if _oai else 'Not set (optional)'}")
    logger.info(f"  DeepSeek:          {'Configured' if _ds else 'Not set (optional)'}")
    logger.info(f"  Anthropic:         {'Configured' if _anth else 'Not set (optional)'}")
    logger.info(f"  Google/Gemini:     {'Configured' if _goo else 'Not set (optional)'}")
    logger.info(f"  Frontend URL:      {os.getenv('FRONTEND_URL', 'http://localhost:5173')}")
    logger.info("")
    try:
        from database.session import init_db, SessionLocal
        from database.seed import seed_brands_and_stores
        from services.auth_service import seed_auth_users

        init_db()
        db = SessionLocal()
        try:
            seed_brands_and_stores(db)
            seed_auth_users(db)
        finally:
            db.close()
        logger.info("  Database .................... Ready")
    except Exception as e:
        logger.warning("  Database init: %s", e)

    logger.info("  Services:")
    logger.info("    - Virtual Try-On ........... Ready")
    logger.info("    - Virtual Stylist .......... Ready")
    logger.info("    - Authentication ........... Ready")
    logger.info("    - Products Catalog ......... Ready")
    logger.info("    - Orders & Checkout ........ Ready")
    logger.info("    - Newsletter & Contact ..... Ready")
    logger.info("    - Wardrobe Auto-Tagging .... Ready")
    logger.info("    - 360° Rotation Viewer ..... Ready")
    logger.info("    - Growth Engine (/api/growth) ... Ready")
    
    # Start health check scheduler (only in dev/staging)
    try:
        from services.debug.health_scheduler import start_scheduler
        scheduler = start_scheduler()
        if scheduler:
            logger.info("    - Health Check Scheduler ... Started")
        else:
            logger.info("    - Health Check Scheduler ... Disabled (production or APScheduler not installed)")
    except Exception as e:
        logger.warning("    - Health Check Scheduler ... Failed: %s", e)
    
    # Initialize payment log store and structured logging (dev/staging only)
    app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if app_env in ("development", "dev", "staging", "stage", "test"):
        try:
            from services.debug.payment_log_store import init_payment_log_store
            from services.debug.structured_logging import configure_structured_logging
            
            # Configure structured JSON logging
            configure_structured_logging()
            
            # Initialize payment log store (async)
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule initialization for after startup
                async def _init_store():
                    try:
                        await init_payment_log_store()
                        logger.info("    - Payment Log Store ...... Initialized")
                    except Exception as ex:
                        logger.warning("    - Payment Log Store ...... Failed: %s", ex)
                asyncio.create_task(_init_store())
            else:
                loop.run_until_complete(init_payment_log_store())
                logger.info("    - Payment Log Store ...... Initialized")
            
            logger.info("    - Structured Logging ...... Enabled (JSON)")
        except Exception as e:
            logger.warning("    - Payment Debug Init ...... Failed: %s", e)
    else:
        logger.info("    - Payment Debug ........... Disabled (production)")

    # Start sales analytics materialized view scheduler
    try:
        from services.analytics.sales_mv_scheduler import start_sales_mv_scheduler

        mv_scheduler = start_sales_mv_scheduler()
        if mv_scheduler:
            logger.info("    - Sales MV Scheduler ...... Started")
        else:
            logger.info("    - Sales MV Scheduler ...... Disabled")
    except Exception as e:
        logger.warning("    - Sales MV Scheduler ...... Failed: %s", e)

    # Start notification ML weekly retraining scheduler
    try:
        from services.notification_ml_scheduler import start_notification_ml_scheduler

        ml_scheduler = start_notification_ml_scheduler()
        if ml_scheduler:
            logger.info("    - Notification ML Scheduler Started")
        else:
            logger.info("    - Notification ML Scheduler Disabled")
    except Exception as e:
        logger.warning("    - Notification ML Scheduler Failed: %s", e)
    
    logger.info("=" * 60)

    yield  # App is running

    # Stop health check scheduler
    try:
        from services.debug.health_scheduler import stop_scheduler
        stop_scheduler()
        logger.info("Health check scheduler stopped")
    except Exception:
        pass

    # Stop sales materialized view scheduler
    try:
        from services.analytics.sales_mv_scheduler import stop_sales_mv_scheduler

        stop_sales_mv_scheduler()
    except Exception:
        pass

    # Stop notification ML scheduler
    try:
        from services.notification_ml_scheduler import stop_notification_ml_scheduler

        stop_notification_ml_scheduler()
    except Exception:
        pass
    
    # Close payment log store and interceptor clients
    try:
        from services.debug.payment_log_store import close_payment_log_store
        from middleware.payment_interceptor import close_interceptor_clients
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            async def _cleanup():
                try:
                    await close_payment_log_store()
                    await close_interceptor_clients()
                except Exception:
                    pass
            asyncio.create_task(_cleanup())
        else:
            loop.run_until_complete(close_payment_log_store())
            loop.run_until_complete(close_interceptor_clients())
        logger.info("Payment debug resources closed")
    except Exception:
        pass

    logger.info("CONFIT Backend shutting down...")


# ── FastAPI App ────────────────────────────────────────────────────

app = FastAPI(
    title="CONFIT Backend",
    description="Full-stack fashion platform backend with AI-powered features",
    version="1.0.0",
    lifespan=lifespan,
)

# Register centralized exception handlers
register_exception_handlers(app)

import re

class DevPreflightMiddleware:
    """
    Always-OK OPTIONS responder (dev).

    MUST be outermost (added after CORSMiddleware), otherwise CORSMiddleware may
    respond with 400 for Private Network Access (PNA) preflights.
    """

    # Pattern for link-local IPs (169.254.x.x) - Windows Mobile Hotspot/VPN
    LINK_LOCAL_PATTERN = re.compile(r"^https?://169\.254\.\d{1,3}\.\d{1,3}(:\d+)?$")

    def __init__(self, app: Callable, allowed_origins: set[str] = None, is_production: bool = False):
        self.app = app
        self.allowed_origins = allowed_origins  # None means allow all origins
        self.is_production = is_production

    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed, including dynamic link-local IPs in dev."""
        if self.allowed_origins is None:
            return True
        if origin in self.allowed_origins:
            return True
        # In development, allow link-local IPs dynamically
        if not self.is_production and self.LINK_LOCAL_PATTERN.match(origin):
            return True
        return False

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Pull headers (lowercase bytes pairs)
        raw_headers = dict(scope.get("headers") or [])
        origin = raw_headers.get(b"origin", b"").decode("utf-8")
        acr_method = raw_headers.get(b"access-control-request-method", b"GET").decode("utf-8")
        acr_headers = raw_headers.get(b"access-control-request-headers", b"").decode("utf-8")

        headers = [
            (b"content-type", b"text/plain; charset=utf-8"),
            (b"vary", b"Origin, Access-Control-Request-Method, Access-Control-Request-Headers"),
            (b"access-control-allow-credentials", b"true"),
            (b"access-control-allow-methods", (acr_method or "*").encode("utf-8")),
            (b"access-control-allow-headers", (acr_headers or "*").encode("utf-8")),
            (b"access-control-max-age", b"600"),
            (b"access-control-allow-private-network", b"true"),
        ]
        # Allow all origins if allowed_origins is None, or if origin is allowed
        if origin and self._is_allowed_origin(origin):
            headers.append((b"access-control-allow-origin", origin.encode("utf-8")))

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": headers,
            }
        )
        await send({"type": "http.response.body", "body": b"OK"})

# ── Rate Limiting ──────────────────────────────────────────────────

if HAS_SLOWAPI:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled (30/min anonymous, 120/min authenticated)")
else:
    logger.warning("slowapi not installed — rate limiting disabled")

# ── CORS Middleware ────────────────────────────────────────────────

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

# In development, allow all origins. In production, restrict to specific domains.
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# In development, allow dynamic origins including link-local IPs (169.254.x.x)
# These are used by Windows for network hotspot/tethering
def _get_allowed_origins():
    origins = [
        # Production domains
        "https://confit.app",
        "https://admin.confit.app",
        "https://staging.confit.app",
        "https://admin-staging.confit.app",
        # Frontend URL from env (may be production or dev)
        frontend_url,
    ]
    if not IS_PRODUCTION:
        origins.extend([
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            # Link-local IPs for Windows Mobile Hotspot / VPN
            "http://169.254.157.9:3000",
            "http://169.254.157.9:5173",
            "http://169.254.157.9:5174",
            "http://169.254.157.9:8080",
        ])
    return origins

ALLOWED_ORIGINS = _get_allowed_origins()

# Development mode: enumerate localhost origins (never use "*" with allow_credentials=True —
# browsers reject it and it constitutes a security misconfiguration).
if not IS_PRODUCTION:
    CORS_ALLOW_ORIGINS = ALLOWED_ORIGINS
else:
    CORS_ALLOW_ORIGINS = ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Idempotency-Key",
        "X-Internal-API-Key",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    **(
        {"allow_private_network": True}
        if "allow_private_network" in inspect.signature(CORSMiddleware.__init__).parameters
        else {}
    ),
)

# Add AFTER CORSMiddleware so this wraps it (outermost).
# In development, allow all origins for DevPreflightMiddleware
app.add_middleware(
    DevPreflightMiddleware,
    allowed_origins=set(ALLOWED_ORIGINS),  # Always enforce origin whitelist
    is_production=IS_PRODUCTION,
)

# ── Request Logging Middleware ──────────────────────────────────────
import time
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "INCOMING: %s %s from %s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            "RESPONSE: %s %s -> %s (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        
        return response

app.add_middleware(RequestLoggingMiddleware)

# ── Security Headers Middleware ──────────────────────────────────────
from core.middleware.security import SecurityHeadersMiddleware, InputValidationMiddleware, CSRFMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware, allowed_origins=set(ALLOWED_ORIGINS))
logger.info("Security headers + CSRF middleware enabled")

# ── Register Routers ──────────────────────────────────────────────────

from routers.virtual_tryon import router as tryon_router
from routers.virtual_stylist import router as stylist_router
from routers.ai_stylist import router as ai_stylist_router
from routers.rotation import router as rotation_router
from routers.auth import router as auth_router
from routers.products import router as products_router
from routers.orders import router as orders_router
from routers.commerce import router as commerce_router
from routers.fashion_os import router as fashion_os_router
from routers.newsletter import router as newsletter_router
from routers.wardrobe import router as wardrobe_router
from routers.brands import router as brands_router
from routers.stores import router as stores_router
from routers.promo_codes import router as promo_router
from routers.visual_search import router as visual_search_router
from routers.wishlist import router as wishlist_router
from routers.outfits import router as outfits_router
from routers.payments import router as payments_router
from routers.payment_platform import router as payment_platform_router
from routers.analytics import router as analytics_router
from routers.digital_twin import router as digital_twin_router
from routers.social import router as social_router
from routers.resale import router as resale_router
from routers.omni import router as omni_router
from routers.challenges import router as challenges_router
from routers.chatbot import router as chatbot_router
from routers.profile import router as profile_router
from routers.onboarding import router as onboarding_router
from routers.signals import router as signals_router
from routers.privacy import router as privacy_router
from routers.identity_intelligence import router as identity_router
from routers.outfit_ratings import router as outfit_ratings_router
from api.style_dna import router as style_dna_router
from api.body_dna import router as body_dna_router
from api.closet_planner import router as closet_planner_router
from routers.influencer import router as influencer_router
from api.sustainability import router as sustainability_router
from routers.security import router as security_router
from routers.growth_engine import router as growth_engine_router
from routers.tryon_runtime import router as tryon_runtime_router
from routers.experiments import router as experiments_router
from routers.pitch_deck import router as pitch_deck_router
from routers.dataset_export import router as dataset_export_router
from routers.training_pipeline import router as training_pipeline_router
from routers.notifications import router as notifications_router
from routers.customer_notifications import router as customer_notifications_router
from routers.notification_preferences import router as notification_preferences_router
from routers.ecosystem import router as ecosystem_router
from routers.debug_logs import router as debug_logs_router
from routers.debug_payments import router as debug_payments_router
from routers.sales_analytics import router as sales_analytics_router
from api.notification_analytics import router as notification_analytics_router
from api.notification_ml import router as notification_ml_router
from api.alert_rules import router as alert_rules_router
from routers.oauth import router as oauth_router
from routers.stripe_checkout import router as stripe_checkout_router
from routers.care import router as care_router
from routers.donations import router as donations_router
from routers.analytics_store import router as analytics_store_router
from routers.analytics_factory import router as analytics_factory_router
from routers.analytics_user import router as analytics_user_router
from routers.analytics_admin import router as analytics_admin_router
from routers.v1_muse import router as v1_muse_router
from routers.v1_mirror import router as v1_mirror_router
from routers.v1_visual_search import router as v1_visual_search_router
from routers.v1_closet import router as v1_closet_router
from routers.v1_ai_admin import router as v1_ai_admin_router

app.include_router(tryon_router)
app.include_router(body_dna_router)
app.include_router(stylist_router)
app.include_router(ai_stylist_router)
app.include_router(rotation_router)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(commerce_router)
app.include_router(fashion_os_router)
app.include_router(newsletter_router)
app.include_router(wardrobe_router)
app.include_router(brands_router)
app.include_router(stores_router)
app.include_router(promo_router)
app.include_router(visual_search_router)
app.include_router(wishlist_router)
app.include_router(outfits_router)
app.include_router(payments_router)
app.include_router(payment_platform_router)
app.include_router(analytics_router)
app.include_router(digital_twin_router)
app.include_router(social_router)
app.include_router(resale_router)
app.include_router(omni_router)
app.include_router(challenges_router)
app.include_router(chatbot_router)
app.include_router(profile_router)
app.include_router(onboarding_router)
app.include_router(signals_router)
app.include_router(privacy_router)
app.include_router(identity_router)
app.include_router(outfit_ratings_router)
app.include_router(style_dna_router)
app.include_router(closet_planner_router)
app.include_router(influencer_router)
app.include_router(sustainability_router)
app.include_router(security_router)
app.include_router(growth_engine_router)
app.include_router(tryon_runtime_router)
app.include_router(experiments_router)
app.include_router(pitch_deck_router)
app.include_router(dataset_export_router)
app.include_router(training_pipeline_router)
app.include_router(notifications_router)
app.include_router(customer_notifications_router)
app.include_router(notification_preferences_router)
app.include_router(ecosystem_router)
app.include_router(debug_logs_router)
app.include_router(debug_payments_router)
app.include_router(sales_analytics_router)
app.include_router(notification_analytics_router)
app.include_router(notification_ml_router)
app.include_router(alert_rules_router)
app.include_router(oauth_router)
app.include_router(stripe_checkout_router)
app.include_router(care_router)
app.include_router(donations_router)
app.include_router(analytics_store_router)
app.include_router(analytics_factory_router)
app.include_router(analytics_user_router)
app.include_router(analytics_admin_router)
app.include_router(v1_muse_router)
app.include_router(v1_mirror_router)
app.include_router(v1_visual_search_router)
app.include_router(v1_closet_router)
app.include_router(v1_ai_admin_router)

# ── Domain Event Handlers ───────────────────────────────────────────
try:
    from services.notificationService.bootstrap import register_notification_handlers

    register_notification_handlers()
    logger.info("Notification handlers registered")
except Exception as e:
    logger.warning("Notification handlers not registered: %s", e)

# ── Batch Notification Scheduler ─────────────────────────────────────
try:
    from services.notificationService.batch_scheduler import start_batch_scheduler
    scheduler = start_batch_scheduler()
    if scheduler:
        logger.info("    - Batch Notification Scheduler ... Started")
    else:
        logger.info("    - Batch Notification Scheduler ... Disabled (APScheduler not installed)")
except Exception as e:
    logger.warning("    - Batch Notification Scheduler ... Failed: %s", e)


# ── Frontend-compatible alias (/api/tryon → /api/virtual-tryon) ────

@app.post("/api/tryon", tags=["Virtual Try-On"], response_model=None)
async def tryon_alias(request: Request):
    """
    Legacy compatibility endpoint.
    Internally redirects to runtime final-render flow (/api/tryon/render contract)
    so old clients cannot accidentally hit deprecated MCP/HF behavior.
    """
    from services.tryon_runtime import TryOnRuntimeManager

    body = await request.json()
    try:
        manager = TryOnRuntimeManager.get_instance()
        result = manager.enqueue_final_render(
            user_image_base64=body.get("userImageBase64", ""),
            garment_image_url=body.get("garmentImageUrl", ""),
            garment_name=body.get("garmentName", "garment"),
            garment_category=body.get("garmentCategory"),
        )
        if not result.get("success"):
            return JSONResponse(
                status_code=503,
                content=fail(
                    result.get("message") or "Final render unavailable.",
                    data={
                        "error_code": result.get("error_code") or "FINAL_RENDER_UNAVAILABLE",
                        "details": result.get("details") or {},
                    },
                ),
            )
        payload = {
            "success": True,
            "mode": "final",
            "job_id": result.get("job_id"),
            "status": result.get("status"),
            "message": "Legacy endpoint routed to /api/tryon/render",
        }
        return JSONResponse(content=ok(payload))
    except ValueError as exc:
        return JSONResponse(status_code=400, content=fail(str(exc)))
    except Exception as exc:
        logger.error("tryon alias error: %s", exc)
        return JSONResponse(status_code=500, content=fail("Try-on processing failed."))


@app.post("/api/tryon/preview", tags=["Virtual Try-On"], response_model=None)
async def tryon_preview_alias(request: Request):
    """
    Legacy compatibility endpoint.
    Internally redirects to runtime preview flow (/api/tryon/preview/live contract)
    so old clients cannot hit deprecated MCP route.
    """
    from services.tryon_runtime import TryOnRuntimeManager

    body = await request.json()
    try:
        manager = TryOnRuntimeManager.get_instance()
        result = await manager.generate_preview(
            user_image_base64=body.get("userImageBase64", ""),
            garment_image_url=body.get("garmentImageUrl", ""),
            garment_name=body.get("garmentName", "garment"),
            garment_category=body.get("garmentCategory"),
        )
        if not result.get("success"):
            return JSONResponse(
                status_code=422,
                content=fail(
                    result.get("error_message") or "Try-on preview failed.",
                    data={
                        "error_code": result.get("failure_kind") or "PREVIEW_FAILED",
                        "warnings": result.get("warnings") or [],
                    },
                ),
            )
        payload = {
            "success": True,
            "mode": "preview",
            "resultImage": result.get("result_image"),
            "timingMs": result.get("timing_ms"),
            "cacheHit": bool(result.get("cache_hit")),
            "warnings": result.get("warnings") or [],
            "message": "Legacy endpoint routed to /api/tryon/preview/live",
        }
        return JSONResponse(content=ok(payload))
    except ValueError as exc:
        return JSONResponse(status_code=400, content=fail(str(exc)))
    except Exception as exc:
        logger.error("tryon preview alias error: %s", exc)
        return JSONResponse(status_code=500, content=fail("Try-on preview failed."))


# ── Health Check ───────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """Global health check endpoint."""
    return ok({
        "status": "ok",
        "service": "confit-backend",
        "version": "1.0.0",
        "activeHost": os.getenv("CONFIT_ACTIVE_HOST"),
        "activePort": os.getenv("CONFIT_ACTIVE_PORT"),
    })


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API documentation link."""
    return {
        "message": "CONFIT Backend API",
        "docs": "/docs",
        "health": "/api/health",
    }


# ── Run Server ─────────────────────────────────────────────────────

def _winerror(exc: BaseException) -> Optional[int]:
    return getattr(exc, "winerror", None)


def _log_port_bind_failure(host: str, port: int, exc: BaseException) -> None:
    """Human-readable bind errors (Windows + POSIX)."""
    we = _winerror(exc)
    en = getattr(exc, "errno", None)
    if we == 10048 or en == errno.EADDRINUSE:
        logger.error(
            "Cannot bind %s:%s — port already in use (Windows: WinError 10048 / EADDRINUSE).\n"
            "  Another backend or app may be using this port.\n"
            "  PowerShell:  Get-NetTCPConnection -LocalPort %s -State Listen\n"
            "  Then:        Stop-Process -Id <PID> -Force\n"
            "  Or:          .\\scripts\\stop-listener-on-port.ps1 -Port %s\n"
            "  Or set in .env:  PORT=8001",
            host,
            port,
            port,
            port,
        )
        return
    if we == 10013 or en == errno.EACCES:
        logger.error(
            "Cannot bind %s:%s — permission denied (Windows: WinError 10013 / EACCES).\n"
            "  Common fixes:\n"
            "  • Use another port:  PORT=8001  (or 8010) in backend/.env\n"
            "  • For local dev only:  HOST=127.0.0.1\n"
            "  • Check Windows excluded port ranges:  "
            "netsh interface ipv4 show excludedportrange protocol=tcp\n"
            "  • Run terminal as Administrator only if policy requires it.",
            host,
            port,
        )
        return
    logger.error("Cannot bind %s:%s: %s", host, port, exc)


def _preflight_bind(host: str, port: int) -> None:
    """
    Fail fast if the TCP port is already in use.

    Note: A test bind to 0.0.0.0 can raise WinError 10013 on some Windows setups, so we
    probe 127.0.0.1 for 0.0.0.0/:: — port-in-use state matches for typical dev use.
    """
    if os.getenv("SKIP_PORT_PREFLIGHT", "").strip().lower() in ("1", "true", "yes"):
        return

    check_host = host.strip()
    if check_host in ("0.0.0.0", "", "::", "[::]"):
        check_host = "127.0.0.1"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((check_host, port))
    except OSError as e:
        we = _winerror(e)
        if we == 10048 or e.errno == errno.EADDRINUSE:
            _log_port_bind_failure(host, port, e)
            # Do not hard-exit here; let the main section attempt an automatic PORT fallback.
            return
        if we == 10013 or e.errno == errno.EACCES:
            logger.warning(
                "Port preflight skipped: cannot probe %s:%s (%s). "
                "Uvicorn will still try %s:%s — if that fails, set PORT=8001 or HOST=127.0.0.1.",
                check_host,
                port,
                e,
                host,
                port,
            )
            return
        raise


def _is_port_in_use(host: str, port: int) -> bool:
    """Best-effort check whether a TCP port is already bound."""
    check_host = host.strip()
    if check_host in ("0.0.0.0", "", "::", "[::]"):
        check_host = "127.0.0.1"
    # Prefer a connect probe (more reliable than bind with SO_REUSEADDR on Windows).
    try:
        with socket.create_connection((check_host, port), timeout=0.6):
            return True
    except OSError:
        # Connection refused / timed out => might not be listening; continue with bind probe.
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((check_host, port))
            return False
    except OSError as e:
        we = _winerror(e)
        if we == 10048 or getattr(e, "errno", None) == errno.EADDRINUSE:
            return True
    return False


def _acquire_single_instance_lock(lock_path: Path) -> Optional[int]:
    """
    Prevents multiple backend instances from starting concurrently.

    We use an exclusive file-creation lock. If the lock exists but the PID is
    no longer alive, we remove the stale lock and acquire again.

    Returns:
      lock file descriptor (to keep until release) or None if another instance exists.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Try create new lock file
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        return fd
    except FileExistsError:
        # Stale lock cleanup best-effort
        try:
            raw = lock_path.read_text(encoding="utf-8").strip()
            pid = int(raw) if raw else None
        except Exception:
            pid = None

        if pid is not None:
            try:
                # os.kill(pid, 0) checks liveness
                os.kill(pid, 0)
                # Still alive => do not start another instance
                return None
            except OSError:
                # Not alive -> remove stale lock
                try:
                    lock_path.unlink(missing_ok=True)  # py>=3.8
                except Exception:
                    pass

        # Retry once after cleanup
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            return fd
        except FileExistsError:
            return None


def _health_probe(host: str, port: int, timeout_sec: float = 1.5) -> bool:
    """
    Best-effort check whether our backend is already serving on this host/port.

    Prevents "port already in use" errors when the user starts multiple instances
    accidentally while the backend is already running.
    """
    try:
        import http.client

        conn = http.client.HTTPConnection(host, port, timeout=timeout_sec)
        conn.request("GET", "/api/health", headers={"Connection": "close"})
        resp = conn.getresponse()
        status = int(getattr(resp, "status", 0))
        return 200 <= status < 300
    except Exception:
        return False


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    # Default to OFF to avoid the backend silently switching ports while the
    # frontend still points at the original PORT.
    auto_port_fallback = os.getenv("PORT_AUTO_FALLBACK", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    ) and is_dev
    max_fallback_tries = int(os.getenv("PORT_AUTO_FALLBACK_MAX_TRIES", "8"))
    enable_reload = os.getenv("BACKEND_RELOAD", "false").lower() == "true" and is_dev

    current_host = host
    current_port = port

    # Port preflight: use connect probe (avoids WinError 10013 from bind probes).
    # If auto-fallback is OFF, fail fast instead of letting uvicorn crash after startup.
    if not auto_port_fallback:
        # If the port is already open, avoid starting a second uvicorn instance.
        # This prevents "helper terminals" where nothing happens.
        if _is_port_in_use("127.0.0.1", current_port):
            # Best-effort confirm (do not block on this decision).
            already_running = _health_probe("127.0.0.1", current_port, timeout_sec=2.0)
            if already_running:
                logger.info(
                    "Backend is already running on 127.0.0.1:%s (health probe OK). Exiting this helper.",
                    current_port,
                )
                sys.exit(0)
            else:
                logger.error(
                    "Port 127.0.0.1:%s is already in use, but /api/health did not respond.\n"
                    "This likely means another process is using the port (not CONFIT backend), or the running backend is unhealthy.\n"
                    "Fix: stop the process on this port, or set PORT in backend/.env to a free port.",
                    current_port,
                )
                sys.exit(1)

    # Try bind with optional auto-increment on EADDRINUSE.
    tries_left = max_fallback_tries if auto_port_fallback else 1
    while tries_left > 0:
        try:
            # Expose the actually-bound host/port for clients + health checks.
            os.environ["CONFIT_ACTIVE_HOST"] = str(current_host)
            os.environ["CONFIT_ACTIVE_PORT"] = str(current_port)

            # Guard against multiple instances starting concurrently.
            safe_host = current_host.replace(":", "_").replace("\\", "_").replace("/", "_")
            lock_path = Path(__file__).resolve().parent / f".server_lock_{safe_host}_{current_port}"
            lock_fd: Optional[int] = None
            try:
                lock_fd = _acquire_single_instance_lock(lock_path)
                if lock_fd is None:
                    logger.error(
                        "Another backend instance is already running (lock: %s).\n"
                        "Stop the existing backend process and restart, or set PORT_AUTO_FALLBACK=1 if you intentionally run multiple instances.",
                        str(lock_path),
                    )
                    sys.exit(1)

                # Use Server/Config instead of uvicorn.run() so bind errors raise
                # and we can implement PORT fallbacks reliably.
                config = uvicorn.Config(
                    "main:app" if enable_reload else app,
                    host=current_host,
                    port=current_port,
                    reload=enable_reload,
                    log_level="info",
                    access_log=True,
                )
                server = uvicorn.Server(config)
                server.run()
                sys.exit(0)
            finally:
                if lock_fd is not None:
                    try:
                        os.close(lock_fd)
                    except Exception:
                        pass
                try:
                    lock_path.unlink(missing_ok=True)
                except Exception:
                    pass
        except SystemExit as e:
            if auto_port_fallback and tries_left > 1:
                # When uvicorn fails to bind, it can call sys.exit(1).
                # Probe the port to decide whether we should try PORT+1.
                if _is_port_in_use("127.0.0.1", current_port):
                    logger.error(
                        "Bind failed for 127.0.0.1:%s (SystemExit). Auto-fallback: trying %s.",
                        current_port,
                        current_port + 1,
                    )
                    current_port += 1
                    tries_left -= 1
                    continue
            raise
        except (OSError, PermissionError) as e:
            we = _winerror(e)
            en = getattr(e, "errno", None)
            if (we == 10048 or en == errno.EADDRINUSE) and auto_port_fallback and tries_left > 1:
                logger.error(
                    "Port %s is already in use. Auto-fallback: trying %s instead.",
                    current_port,
                    current_port + 1,
                )
                current_port += 1
                tries_left -= 1
                continue

            if (we == 10013 or en == errno.EACCES) and auto_port_fallback and tries_left > 1:
                # If binding fails due to permissions, try local loopback.
                if current_host not in ("127.0.0.1", "localhost"):
                    logger.error(
                        "Bind permission denied for %s:%s. Auto-fallback: switching host to 127.0.0.1.",
                        current_host,
                        current_port,
                    )
                    current_host = "127.0.0.1"
                    tries_left -= 1
                    continue

                # Otherwise fall back to another port.
                logger.error(
                    "Bind permission denied for %s:%s. Auto-fallback: trying %s.",
                    current_host,
                    current_port,
                    current_port + 1,
                )
                current_port += 1
                tries_left -= 1
                continue

            _log_port_bind_failure(current_host, current_port, e)
            sys.exit(1)
