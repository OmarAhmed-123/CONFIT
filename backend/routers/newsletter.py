"""
CONFIT Backend — Newsletter & Contact Router
===============================================
Endpoints for newsletter subscription and contact form.
"""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Newsletter & Contact"])

# In-memory storage
_subscribers: list[dict] = []
_contact_messages: list[dict] = []


# ── Request / Response Models ──────────────────────────────────────

class SubscribeRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    subject: str = Field(default="General Inquiry", max_length=200)
    message: str = Field(..., min_length=10, max_length=2000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/newsletter/subscribe")
async def subscribe_newsletter(request: SubscribeRequest):
    """Subscribe to the CONFIT newsletter."""
    # Check if already subscribed
    existing = any(s["email"] == request.email for s in _subscribers)
    if existing:
        return {
            "success": True,
            "message": "You're already subscribed! We'll keep you updated.",
            "already_subscribed": True,
        }

    _subscribers.append({
        "email": request.email,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(f"Newsletter subscription: {request.email}")
    return {
        "success": True,
        "message": "Welcome! You've been subscribed to our newsletter.",
        "already_subscribed": False,
    }


@router.post("/contact")
async def submit_contact(request: ContactRequest):
    """Submit a contact form message."""
    _contact_messages.append({
        "name": request.name,
        "email": request.email,
        "subject": request.subject,
        "message": request.message,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(f"Contact form submitted by {request.name} ({request.email})")
    return {
        "success": True,
        "message": "Thank you for reaching out! We'll get back to you within 24 hours.",
    }
