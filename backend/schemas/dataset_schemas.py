"""
CONFIT Backend — Ecosystem Dataset Schemas
============================================
Backend-ready JSON structures for recommendation models and analytics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class UserRecord(BaseModel):
    id: str
    style_preferences: Dict[str, Any] = Field(default_factory=dict)
    budget_range: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


class ProductRecord(BaseModel):
    id: str
    category: Optional[str] = None
    color: Optional[str] = None
    style: List[str] = Field(default_factory=list)
    price: Optional[float] = None
    brand: Optional[str] = None


class OutfitRecord(BaseModel):
    id: str
    combination_rules: Dict[str, Any] = Field(default_factory=dict)
    compatibility_scores: Dict[str, float] = Field(default_factory=dict)


class EventRecord(BaseModel):
    user_id: str
    product_id: Optional[str] = None
    outfit_id: Optional[str] = None
    event_type: Literal["click", "purchase", "save"]
    ts_ms: int
    context: Dict[str, Any] = Field(default_factory=dict)


class EcosystemDataset(BaseModel):
    users: List[UserRecord] = Field(default_factory=list)
    products: List[ProductRecord] = Field(default_factory=list)
    outfits: List[OutfitRecord] = Field(default_factory=list)
    events: List[EventRecord] = Field(default_factory=list)

