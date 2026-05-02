"""
CONFIT Backend - CONFIT CARE Pydantic Schemas
==============================================
Request and response schemas for the charitable giving feature.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator, root_validator, EmailStr
from pydantic.types import constr


# =============================================================================
# Enums (re-exported from models for schema use)
# =============================================================================

class CampaignType(str, Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    SEASONAL = "seasonal"
    CORPORATE = "corporate"
    EMERGENCY = "emergency"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class VoucherStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACCESSED = "accessed"
    ACTIVE = "active"
    COMPLETED = "completed"
    PARTIALLY_USED = "partially_used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SessionStatus(str, Enum):
    PENDING = "pending"
    OTP_SENT = "otp_sent"
    OTP_VERIFIED = "otp_verified"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    LOCKED = "locked"


# =============================================================================
# Base Schemas
# =============================================================================

class BaseResponseModel(BaseModel):
    """Base model for all response schemas."""
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else None,
            UUID: lambda v: str(v) if v else None,
        }


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseResponseModel):
    """Generic paginated response."""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# =============================================================================
# Beneficiary Schemas
# =============================================================================

class BeneficiaryCreate(BaseModel):
    """Schema for creating a beneficiary."""
    name: str = Field(..., min_length=2, max_length=255, description="Beneficiary name")
    email: Optional[EmailStr] = Field(None, description="Beneficiary email")
    phone: Optional[str] = Field(None, max_length=32, description="Beneficiary phone number")
    age_group: Optional[str] = Field(None, description="Age group (e.g., '18-25')")
    size_preference: Optional[str] = Field(None, max_length=20, description="Preferred size")
    style_preference: Optional[List[str]] = Field(None, description="Style preferences")
    occasion_needs: Optional[List[str]] = Field(None, description="Occasion needs")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v:
            # Remove spaces and dashes
            v = v.replace(' ', '').replace('-', '')
            if not v.startswith('+') and not v.isdigit():
                raise ValueError('Phone must be a valid number')
        return v


class BeneficiaryUpdate(BaseModel):
    """Schema for updating a beneficiary."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=32)
    age_group: Optional[str] = None
    size_preference: Optional[str] = None
    style_preference: Optional[List[str]] = None
    occasion_needs: Optional[List[str]] = None
    is_active: Optional[bool] = None


class BeneficiaryBulkUpload(BaseModel):
    """Schema for bulk uploading beneficiaries."""
    beneficiaries: List[BeneficiaryCreate] = Field(..., min_items=1, max_items=100)


class BeneficiaryResponse(BaseResponseModel):
    """Schema for beneficiary response."""
    id: str
    campaign_id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    age_group: Optional[str]
    size_preference: Optional[str]
    style_preference: Optional[List[str]]
    occasion_needs: Optional[List[str]]
    budget_allocated: float
    budget_used: float
    budget_remaining: float
    currency: str
    is_active: bool
    invitation_sent_at: Optional[datetime]
    first_access_at: Optional[datetime]
    last_access_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class BeneficiaryListResponse(PaginatedResponse):
    """Paginated list of beneficiaries."""
    beneficiaries: List[BeneficiaryResponse]


# =============================================================================
# Campaign Schemas
# =============================================================================

class CampaignCreate(BaseModel):
    """Schema for creating a campaign."""
    campaign_name: str = Field(..., min_length=3, max_length=255, description="Campaign name")
    campaign_type: CampaignType = Field(default=CampaignType.INDIVIDUAL, description="Campaign type")
    description: Optional[str] = Field(None, max_length=2000, description="Campaign description")
    
    # Budget configuration
    budget_per_person: float = Field(..., gt=0, le=5000, description="Budget per beneficiary in EGP")
    currency: str = Field(default="EGP", max_length=10)
    
    # Restrictions
    allowed_categories: Optional[List[str]] = Field(None, description="Allowed product categories")
    excluded_brands: Optional[List[str]] = Field(None, description="Excluded brands")
    occasion_filter: Optional[str] = Field(None, description="Occasion filter")
    
    # Dates
    end_date: Optional[datetime] = Field(None, description="Campaign end date")
    voucher_expiry_days: int = Field(default=30, ge=1, le=365, description="Voucher expiry in days")
    
    # Messaging
    invitation_message: Optional[str] = Field(None, max_length=500, description="Custom invitation message")
    confirmation_message: Optional[str] = Field(None, max_length=500, description="Order confirmation message")
    
    @validator('budget_per_person')
    def validate_budget(cls, v):
        if v < 500:
            raise ValueError('Minimum budget per person is 500 EGP')
        if v > 5000:
            raise ValueError('Maximum budget per person is 5000 EGP')
        return v


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""
    campaign_name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    budget_per_person: Optional[float] = Field(None, gt=0, le=5000)
    allowed_categories: Optional[List[str]] = None
    excluded_brands: Optional[List[str]] = None
    occasion_filter: Optional[str] = None
    end_date: Optional[datetime] = None
    voucher_expiry_days: Optional[int] = Field(None, ge=1, le=365)
    invitation_message: Optional[str] = None
    confirmation_message: Optional[str] = None
    status: Optional[CampaignStatus] = None


class CampaignActivate(BaseModel):
    """Schema for activating a campaign with beneficiaries."""
    beneficiaries: List[BeneficiaryCreate] = Field(..., min_items=1, max_items=100)
    send_invitations: bool = Field(default=True, description="Send invitations immediately")


class CampaignResponse(BaseResponseModel):
    """Schema for campaign response."""
    id: str
    donor_id: str
    campaign_name: str
    campaign_type: CampaignType
    description: Optional[str]
    
    budget_per_person: float
    total_beneficiaries: int
    total_budget_allocated: float
    total_budget_used: float
    currency: str
    
    allowed_categories: Optional[List[str]]
    excluded_brands: Optional[List[str]]
    occasion_filter: Optional[str]
    
    status: CampaignStatus
    
    start_date: datetime
    end_date: Optional[datetime]
    voucher_expiry_days: int
    
    invitation_message: Optional[str]
    confirmation_message: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime]


class CampaignListResponse(PaginatedResponse):
    """Paginated list of campaigns."""
    campaigns: List[CampaignResponse]


class CampaignSummary(BaseResponseModel):
    """Summary statistics for a campaign."""
    campaign_id: str
    campaign_name: str
    status: CampaignStatus
    
    # Beneficiary stats
    total_beneficiaries: int
    active_beneficiaries: int
    completed_beneficiaries: int
    
    # Financial stats
    total_budget_allocated: float
    total_budget_used: float
    budget_utilization_rate: float
    
    # Engagement stats
    engagement_rate: float
    completion_rate: float
    
    # Time stats
    days_remaining: Optional[int]
    average_time_to_completion_hours: Optional[float]


# =============================================================================
# Voucher Schemas
# =============================================================================

class VoucherCreate(BaseModel):
    """Schema for creating a voucher manually."""
    beneficiary_id: str = Field(..., description="Beneficiary ID")
    budget_override: Optional[float] = Field(None, gt=0, description="Override campaign budget")
    expires_at: Optional[datetime] = Field(None, description="Custom expiry date")


class VoucherValidate(BaseModel):
    """Schema for validating a voucher token."""
    voucher_token: str = Field(..., min_length=12, max_length=32, description="Voucher token")


class VoucherResponse(BaseModel):
    """Response when creating or retrieving a voucher."""
    id: str
    campaign_id: str
    beneficiary_id: str
    voucher_token: str = Field(alias="code")
    budget_allocated: float = Field(alias="amount")
    budget_used: float = Field(alias="used")
    budget_remaining: float = Field(alias="balance")
    currency: str
    status: VoucherStatus
    issued_at: Optional[datetime]
    sent_at: Optional[datetime]
    accessed_at: Optional[datetime]
    expires_at: Optional[datetime] = Field(default=None, alias="expiresAt")
    is_active: bool = Field(alias="isActive")
    used_at: Optional[datetime] = Field(default=None, alias="usedAt")
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        populate_by_name = True


class VoucherListResponse(PaginatedResponse):
    """Paginated list of vouchers."""
    vouchers: List[VoucherResponse]


# =============================================================================
# Session Schemas (Beneficiary Access)
# =============================================================================

class SessionInitiate(BaseModel):
    """Schema for initiating a beneficiary session."""
    voucher_token: str = Field(..., min_length=12, max_length=32, description="Voucher token")


class OTPRequest(BaseModel):
    """Schema for requesting OTP."""
    voucher_token: str = Field(..., description="Voucher token")
    session_id: str = Field(..., description="Session ID")


class OTPVerify(BaseModel):
    """Schema for verifying OTP."""
    session_id: str = Field(..., description="Session ID")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class SessionResponse(BaseResponseModel):
    """Schema for session response."""
    id: str
    voucher_id: str
    session_token: str
    status: SessionStatus
    expires_at: datetime
    otp_verified: bool
    created_at: datetime


class BeneficiarySessionContext(BaseResponseModel):
    """Full context for an authenticated beneficiary session."""
    session: SessionResponse
    voucher: VoucherResponse
    beneficiary: BeneficiaryResponse
    campaign: CampaignResponse
    
    # Shopping context
    budget_remaining: float
    allowed_categories: Optional[List[str]]
    excluded_brands: Optional[List[str]]
    occasion_filter: Optional[str]
    
    # UI hints
    show_prices: bool = Field(default=True, description="Whether to show prices (hidden when over budget)")
    budget_warning_threshold: float = Field(default=0.2, description="Warn when budget below this ratio")


# =============================================================================
# Order Schemas (CARE-specific)
# =============================================================================

class CareOrderCreate(BaseModel):
    """Schema for creating a care order."""
    session_id: str = Field(..., description="Session ID")
    items: List[Dict[str, Any]] = Field(..., min_items=1, description="Order items")
    delivery_method: str = Field(..., description="Delivery method")
    shipping_address: Optional[Dict[str, str]] = Field(None, description="Shipping address")
    pickup_store_id: Optional[str] = Field(None, description="Store ID for pickup")


class CareOrderResponse(BaseResponseModel):
    """Schema for care order response."""
    id: str
    voucher_id: str
    beneficiary_id: str
    order_id: str
    subtotal: float
    shipping_cost: float
    total_amount: float
    amount_from_voucher: float
    currency: str
    status: str
    delivery_method: Optional[str]
    items_count: int
    items_summary: List[Dict[str, Any]]
    created_at: datetime
    confirmed_at: Optional[datetime]
    delivered_at: Optional[datetime]


class CareOrderConfirmation(BaseResponseModel):
    """Confirmation response after order placement."""
    order: CareOrderResponse
    message: str
    budget_remaining: float
    estimated_delivery: Optional[str]


# =============================================================================
# Analytics Schemas
# =============================================================================

class CareAnalyticsResponse(BaseResponseModel):
    """Schema for campaign analytics response."""
    campaign_id: str
    
    # Voucher metrics
    total_vouchers_created: int
    vouchers_sent: int
    vouchers_accessed: int
    vouchers_completed: int
    vouchers_expired: int
    
    # Financial metrics
    total_budget_allocated: float
    total_budget_used: float
    average_order_value: Optional[float]
    average_spend_per_beneficiary: Optional[float]
    
    # Product metrics
    total_products_purchased: int
    most_purchased_categories: List[Dict[str, Any]]
    most_purchased_brands: List[Dict[str, Any]]
    category_distribution: Dict[str, int]
    
    # Engagement metrics
    engagement_rate: float
    completion_rate: float
    average_session_duration_minutes: Optional[float]
    total_sessions: int
    
    # Time metrics
    average_time_to_first_access_hours: Optional[float]
    average_time_to_completion_hours: Optional[float]
    
    updated_at: datetime


class DonorDashboardResponse(BaseResponseModel):
    """Complete donor dashboard data."""
    # Summary stats
    total_campaigns: int
    active_campaigns: int
    total_beneficiaries_supported: int
    total_donated: float
    total_impact_value: float
    currency: str
    
    # Recent activity
    recent_campaigns: List[CampaignSummary]
    recent_orders: List[CareOrderResponse]
    
    # Charts data
    spending_by_category: Dict[str, float]
    spending_by_date: List[Dict[str, Any]]
    engagement_trend: List[Dict[str, Any]]


class CareReportRequest(BaseModel):
    """Schema for requesting a report."""
    campaign_id: str
    report_type: str = Field(default="summary", description="Report type: summary, detailed, csr")
    format: str = Field(default="pdf", description="Output format: pdf, csv")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class CareReportResponse(BaseResponseModel):
    """Response after report generation."""
    report_id: str
    campaign_id: str
    report_type: str
    format: str
    download_url: str
    generated_at: datetime
    expires_at: datetime


# =============================================================================
# Audit Log Schemas
# =============================================================================

class AuditLogResponse(BaseResponseModel):
    """Schema for audit log entry."""
    id: str
    campaign_id: Optional[str]
    voucher_id: Optional[str]
    session_id: Optional[str]
    beneficiary_id: Optional[str]
    order_id: Optional[str]
    
    action: str
    action_category: str
    description: Optional[str]
    
    actor_type: str
    actor_id: Optional[str]
    
    previous_state: Optional[Dict[str, Any]]
    new_state: Optional[Dict[str, Any]]
    details: Optional[Dict[str, Any]]
    
    timestamp: datetime


class AuditLogListResponse(PaginatedResponse):
    """Paginated list of audit logs."""
    logs: List[AuditLogResponse]


# =============================================================================
# Error Schemas
# =============================================================================

class CareError(BaseModel):
    """Error response for CARE endpoints."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "CARE_002",
                "message": "Invalid voucher token",
                "details": {"voucher_token": "Token not found or expired"}
            }
        }


# =============================================================================
# CSV Upload Schemas
# =============================================================================

class CSVUploadResponse(BaseResponseModel):
    """Response after CSV upload."""
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: List[Dict[str, Any]]
    beneficiaries: List[BeneficiaryCreate]


class CSVValidationError(BaseModel):
    """Single CSV validation error."""
    row_number: int
    field: str
    value: str
    error: str
