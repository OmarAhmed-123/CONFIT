"""
CONFIT Backend - Application Entry Point
=========================================
FastAPI application with all middleware and routes.

NOT the default container entrypoint — Docker uses uvicorn main:app.
This file exposes a smaller /api/v1 surface and different health paths; see ARCHITECTURE.md.
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.errors import AppError, error_handler
from core.middleware.logging import LoggingMiddleware, RequestIDMiddleware
from core.middleware.error_handler import register_exception_handlers
from core.middleware.rate_limit import RateLimitMiddleware, RateLimitConfig
from core.middleware.security_headers import SecurityHeadersMiddleware
from core.middleware.monitoring import (
    MetricsMiddleware, metrics_endpoint, health_endpoint,
    readiness_endpoint, liveness_endpoint
)
from core.security.secrets_manager import init_secrets
from infrastructure.database import init_db, close_db
from infrastructure.redis_client import init_redis, close_redis
from infrastructure.elasticsearch import init_elasticsearch, close_elasticsearch


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging():
    """Configure structured logging."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}")


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    
    # Startup
    logger.info("=" * 60)
    logger.info("CONFIT Backend Starting Up")
    logger.info("=" * 60)
    
    # Initialize secrets and validate
    logger.info("Initializing secrets...")
    secrets_valid = init_secrets(settings.ENVIRONMENT)
    if not secrets_valid and settings.is_production:
        logger.critical("Secrets validation failed! Some required secrets are missing.")
    logger.info("Secrets initialized")
    
    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis
    logger.info("Initializing Redis...")
    await init_redis()
    logger.info("Redis initialized")
    
    # Initialize Elasticsearch
    logger.info("Initializing Elasticsearch...")
    await init_elasticsearch()
    logger.info("Elasticsearch initialized")
    
    logger.info("=" * 60)
    logger.info("CONFIT Backend Ready")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("CONFIT Backend Shutting Down")
    logger.info("=" * 60)
    
    # Close connections
    await close_db()
    logger.info("Database connections closed")
    
    await close_redis()
    logger.info("Redis connections closed")
    
    await close_elasticsearch()
    logger.info("Elasticsearch connections closed")
    
    logger.info("=" * 60)
    logger.info("Shutdown Complete")
    logger.info("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# CREATE APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CONFIT API",
    description="""
    AI-Powered Fashion Intelligence Platform
    
    ## Features
    
    * **Authentication** - JWT, OAuth (Google, Facebook, Apple), RBAC
    * **Products** - Catalog, search, inventory management
    * **Virtual Try-On** - AI-powered outfit visualization
    * **Visual Search** - Search by image with attribute detection
    * **Wardrobe** - Personal wardrobe management
    * **Recommendations** - AI-powered product suggestions
    * **Brands** - Brand management and analytics
    * **Checkout** - Cart, payments (Stripe, BNPL)
    
    ## Authentication
    
    Most endpoints require authentication. Use the `/auth/login` endpoint to obtain
    an access token, then include it in the `Authorization` header as a Bearer token.
    """,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Trusted Host
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# GZIP Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request ID
app.add_middleware(RequestIDMiddleware)

# Logging
app.add_middleware(LoggingMiddleware)

# Rate Limiting
app.add_middleware(
    RateLimitMiddleware,
    config=RateLimitConfig(),
)

# Security Headers (OWASP recommended)
app.add_middleware(SecurityHeadersMiddleware)

# Metrics
app.add_middleware(MetricsMiddleware)


# ─────────────────────────────────────────────────────────────────────────────
# EXCEPTION HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

register_exception_handlers(app)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

# Health & Monitoring
app.add_route("/health", health_endpoint, methods=["GET"])
app.add_route("/readiness", readiness_endpoint, methods=["GET"])
app.add_route("/liveness", liveness_endpoint, methods=["GET"])
app.add_route("/metrics", metrics_endpoint, methods=["GET"])


# API Routes
from api.auth import router as auth_router
from api.products import router as products_router
from api.checkout import router as checkout_router
from api.recommendations import router as recommendations_router
from api.brands import router as brands_router
from api.ai_endpoints import include_ai_routers

app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(checkout_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(brands_router, prefix="/api/v1")

# AI Services (MUSE, MIRROR, Visual Search, Wardrobe, Admin)
include_ai_routers(app)

# Debug Routes (only accessible in development/staging)
from routers.debug_payments import router as debug_router
app.include_router(debug_router)


# ─────────────────────────────────────────────────────────────────────────────
# ROOT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "CONFIT API",
        "version": "1.0.0",
        "description": "AI-Powered Fashion Intelligence Platform",
        "documentation": "/docs" if settings.DEBUG else "Disabled in production",
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events with signature verification."""
    from application.services.checkout_service import CheckoutService
    from infrastructure.database import async_session_factory
    from core.security.secrets_manager import secrets_manager
    import stripe
    import hmac
    import hashlib
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    # Get webhook secret from secrets manager
    webhook_secret = secrets_manager.get("STRIPE_WEBHOOK_SECRET")
    
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return JSONResponse(
            status_code=500,
            content={"error": "Webhook not configured"},
        )
    
    # Verify webhook signature
    if not sig_header:
        logger.warning("Stripe webhook missing signature header")
        return JSONResponse(
            status_code=400,
            content={"error": "Missing signature"},
        )
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        # Log event for audit
        logger.info(f"Stripe webhook received: {event['type']}")
        
        # Handle event
        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            order_id = payment_intent.get("metadata", {}).get("order_id")
            
            # Validate order_id format
            if order_id:
                try:
                    from uuid import UUID
                    UUID(order_id)  # Validate UUID format
                except ValueError:
                    logger.warning(f"Invalid order_id in webhook: {order_id}")
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid order ID"},
                    )
                
                async with async_session_factory() as session:
                    checkout = CheckoutService(session)
                    await checkout.confirm_payment(
                        order_id=order_id,
                        payment_intent_id=payment_intent["id"],
                    )
                    await session.commit()
        
        
        elif event["type"] == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            logger.warning(f"Payment failed: {payment_intent.get('id')}")
        
        
        return {"status": "success"}
        
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"Stripe webhook signature verification failed: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid signature"},
        )
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": "Webhook processing failed"},
        )


# ─────────────────────────────────────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    setup_logging()
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level="debug" if settings.DEBUG else "info",
        access_log=True,
    )
