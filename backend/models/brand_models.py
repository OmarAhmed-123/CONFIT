from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

class BrandBase(BaseModel):
    name: str = Field(..., description="Brand name")
    description: str = Field(..., description="Brand description")
    logo_url: Optional[str] = Field(None, description="URL of the brand logo")
    banner_url: Optional[str] = Field(None, description="URL of the brand banner")
    website: Optional[str] = Field(None, description="Brand's official website")

class BrandCreate(BrandBase):
    pass

class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    website: Optional[str] = None

class BrandResponse(BrandBase):
    id: str
    created_at: datetime
    updated_at: datetime
    product_count: int = 0
    
    class Config:
        from_attributes = True

class BrandMetrics(BaseModel):
    brand_id: str
    total_sales: float
    total_orders: int
    top_products: List[str]
    conversion_rate: float
    return_rate: float


class BrandDashboardMetrics(BaseModel):
    """Comprehensive brand dashboard metrics."""
    brand_id: str
    
    # Sales metrics
    total_revenue: float
    total_orders: int
    total_units_sold: int
    average_order_value: float
    
    # Performance metrics
    conversion_rate: float
    return_rate: float
    customer_satisfaction: float
    
    # Intelligence metrics
    demand_score: float
    trend_alignment: float
    quality_score: float
    trust_index: float
    trust_tier: str
    
    # Inventory metrics
    stock_health_score: float
    overstock_alerts: int
    understock_alerts: int
    
    # Top performers
    top_products: List[Dict[str, Any]]
    trending_items: List[str]
    
    # Period
    period: str
    last_updated: datetime


class BrandPerformanceSignal(BaseModel):
    """Signal to send to AI Central Brain."""
    brand_id: str
    signal_type: str
    entity_type: str
    entity_id: str
    value: float
    context: Dict[str, Any]
    timestamp: datetime


class BrandIntelligenceInsight(BaseModel):
    """AI-generated insight for brand."""
    insight_id: str
    brand_id: str
    insight_type: str  # opportunity, warning, recommendation
    title: str
    description: str
    impact_score: float
    action_items: List[str]
    created_at: datetime


class BrandTrustProfile(BaseModel):
    """Brand trust and governance profile."""
    brand_id: str
    trust_score: float
    trust_tier: str
    tier_benefits: List[str]
    is_verified: bool
    verification_level: str
    compliance_status: str
    compliance_score: float
    quality_score: float
    probation_risk: bool
    last_review_date: datetime
    next_review_date: datetime
