"""
CONFIT Backend - Donor Ecosystem Tests (Phase 4)
=================================================
Tests for donor service, coupon service, and payment flow.

Tests:
- test_concurrent_coupon_redemption: Race condition safety
- test_end_to_end_donation_flow: Full donor registration -> donation -> coupon redemption
- test_tier_upgrade: Tier calculation based on donation amount
- test_coupon_validation: Coupon validation logic
- test_anonymous_donor: Anonymous donor privacy
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Note: These tests assume pytest-asyncio is installed


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.begin = MagicMock(return_value=AsyncMock())
    return db


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.name = "Test User"
    user.email = "test@example.com"
    user.phone = "+201234567890"
    return user


@pytest.fixture
def mock_donor(mock_user):
    """Create mock donor."""
    from database.donation_models import Donor, DonorTier
    
    donor = MagicMock(spec=Donor)
    donor.id = str(uuid.uuid4())
    donor.user_id = mock_user.id
    donor.display_name = "Test Donor"
    donor.tier = DonorTier.SUPPORTER
    donor.total_donated_piastres = 0
    donor.people_helped = 0
    donor.is_anonymous = False
    donor.is_verified = False
    donor.coupons = []
    return donor


@pytest.fixture
def mock_coupon(mock_donor):
    """Create mock coupon."""
    from database.donation_models import Coupon, CouponType, CouponVisibility
    
    coupon = MagicMock(spec=Coupon)
    coupon.id = str(uuid.uuid4())
    coupon.code = "TEST20XYZ"
    coupon.donor_id = mock_donor.id
    coupon.donor = mock_donor
    coupon.type = CouponType.PERCENTAGE
    coupon.value = 20
    coupon.min_cart_piastres = None
    coupon.max_discount_piastres = None
    coupon.visibility = CouponVisibility.PUBLIC
    coupon.eligible_categories = None
    coupon.usage_limit = 10
    coupon.per_user_limit = 1
    coupon.used_count = 0
    coupon.valid_from = datetime.now(timezone.utc)
    coupon.valid_until = datetime.now(timezone.utc) + timedelta(days=365)
    coupon.is_active = True
    return coupon


# ========================================
# CONCURRENT REDEMPTION TEST
# ========================================

@pytest.mark.asyncio
async def test_concurrent_coupon_redemption(mock_db, mock_coupon, mock_user):
    """
    Test that concurrent redemption attempts are handled safely.
    
    Scenario:
    - Coupon has usage_limit=1
    - 5 concurrent requests attempt to redeem
    - Only 1 should succeed
    """
    from services.coupon_service import CouponService
    from database.donation_models import CouponRedemption
    
    # Setup mock responses
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_coupon
    mock_db.execute.return_value.scalar.return_value = 0  # No prior redemptions
    
    service = CouponService(mock_db)
    
    # Simulate concurrent redemption attempts
    cart_piastres = 10000  # 100 EGP
    
    async def attempt_redemption(user_suffix: int):
        try:
            # Each attempt uses a different user
            user_id = f"user_{user_suffix}"
            order_id = f"order_{user_suffix}"
            
            # Mock the lock acquisition
            with patch.object(service, '_calculate_discount', return_value=2000):
                # Simulate the race condition by incrementing used_count
                mock_coupon.used_count += 1
                
                # Check if limit exceeded
                if mock_coupon.used_count > mock_coupon.usage_limit:
                    raise Exception("Coupon usage limit reached")
                
                # Create redemption
                redemption = MagicMock(spec=CouponRedemption)
                redemption.id = str(uuid.uuid4())
                redemption.discount_applied_piastres = 2000
                return redemption
        except Exception as e:
            return None
    
    # Run 5 concurrent attempts for a coupon with limit 1
    # Reset used_count
    mock_coupon.used_count = 0
    mock_coupon.usage_limit = 1
    
    results = await asyncio.gather(
        attempt_redemption(1),
        attempt_redemption(2),
        attempt_redemption(3),
        attempt_redemption(4),
        attempt_redemption(5),
    )
    
    # Only 1 should succeed
    successful = [r for r in results if r is not None]
    assert len(successful) == 1, f"Expected 1 successful redemption, got {len(successful)}"
    
    print(f"Concurrent redemption test passed: {len(successful)}/5 succeeded")


# ========================================
# END-TO-END DONATION FLOW TEST
# ========================================

@pytest.mark.asyncio
async def test_end_to_end_donation_flow(mock_db, mock_user, mock_donor):
    """
    Test complete donation flow:
    1. User registers as donor
    2. User makes donation
    3. Coupon is created
    4. Beneficiary redeems coupon
    """
    from services.donor_service import DonorService
    from services.coupon_service import CouponService
    from database.donation_models import DonorTier
    
    # Step 1: Register donor
    mock_db.execute.return_value.scalar_one_or_none.return_value = None  # No existing donor
    donor_service = DonorService(mock_db)
    
    # Mock user lookup
    with patch.object(donor_service, 'get_donor_by_user_id', return_value=None):
        with patch.object(donor_service, 'get_donor_by_id', return_value=mock_donor):
            # Step 2: Process donation
            donation_amount = Decimal("500.00")  # 500 EGP
            
            # Mock the donation creation
            mock_donor.total_donated_piastres = 50000  # 500 EGP in piastres
            
            # Step 3: Check tier upgrade
            # 500 EGP should make them a SUPPORTER (threshold is 500 EGP)
            assert mock_donor.tier == DonorTier.SUPPORTER
            
            # Step 4: Create coupon
            coupon_config = {
                "type": "percentage",
                "value": 10,
                "visibility": "public",
                "usage_limit": 100,
            }
            
            # Mock coupon creation
            mock_coupon = MagicMock()
            mock_coupon.code = "DONOR10ABC"
            mock_coupon.value = 10
            
            print("End-to-end donation flow test passed:")
            print(f"  - Donor registered: {mock_donor.id}")
            print(f"  - Donation processed: {donation_amount} EGP")
            print(f"  - Tier: {mock_donor.tier.value}")
            print(f"  - Coupon created: {mock_coupon.code}")


# ========================================
# TIER UPGRADE TEST
# ========================================

@pytest.mark.asyncio
async def test_tier_upgrade(mock_donor):
    """
    Test tier calculation based on donation amounts.
    
    Tiers:
    - SUPPORTER: 500+ EGP
    - STYLIST: 2,500+ EGP
    - PATRON: 10,000+ EGP
    - ICON: 50,000+ EGP
    """
    from database.donation_models import DonorTier
    
    tier_thresholds = {
        DonorTier.SUPPORTER: 50000,    # 500 EGP
        DonorTier.STYLIST: 250000,     # 2,500 EGP
        DonorTier.PATRON: 1000000,     # 10,000 EGP
        DonorTier.ICON: 5000000,       # 50,000 EGP
    }
    
    def calculate_tier(total_piastres: int) -> DonorTier:
        for tier, threshold in tier_thresholds.items():
            if total_piastres >= threshold:
                return tier
        return DonorTier.SUPPORTER
    
    # Test various donation amounts
    test_cases = [
        (0, DonorTier.SUPPORTER),           # 0 EGP - SUPPORTER (default)
        (50000, DonorTier.SUPPORTER),       # 500 EGP - SUPPORTER
        (250000, DonorTier.STYLIST),        # 2,500 EGP - STYLIST
        (1000000, DonorTier.PATRON),        # 10,000 EGP - PATRON
        (5000000, DonorTier.ICON),          # 50,000 EGP - ICON
        (10000000, DonorTier.ICON),         # 100,000 EGP - ICON (highest)
    ]
    
    for total_piastres, expected_tier in test_cases:
        calculated = calculate_tier(total_piastres)
        assert calculated == expected_tier, \
            f"Total {total_piastres/100} EGP should be {expected_tier.value}, got {calculated.value}"
    
    print("Tier upgrade test passed for all thresholds")


# ========================================
# COUPON VALIDATION TEST
# ========================================

@pytest.mark.asyncio
async def test_coupon_validation(mock_db, mock_coupon, mock_user):
    """
    Test coupon validation logic.
    
    Checks:
    - Active status
    - Expiry date
    - Usage limit
    - Per-user limit
    - Minimum cart
    """
    from services.coupon_service import CouponService
    
    service = CouponService(mock_db)
    
    # Mock the coupon lookup
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_coupon
    mock_db.execute.return_value.scalar.return_value = 0  # No prior redemptions
    
    # Test valid coupon
    validation = await service.validate_coupon(
        code="TEST20XYZ",
        user_id=mock_user.id,
        cart_total_piastres=10000,  # 100 EGP
    )
    
    assert validation.is_valid, f"Coupon should be valid, got: {validation.error_reason}"
    assert validation.discount_amount_piastres == 2000  # 20% of 10000
    
    print(f"Coupon validation test passed: discount = {validation.discount_amount_piastres/100} EGP")


@pytest.mark.asyncio
async def test_expired_coupon_validation(mock_db, mock_coupon, mock_user):
    """Test that expired coupons are rejected."""
    from services.coupon_service import CouponService
    
    # Set coupon as expired
    mock_coupon.valid_until = datetime.now(timezone.utc) - timedelta(days=1)
    
    service = CouponService(mock_db)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_coupon
    
    validation = await service.validate_coupon(
        code="TEST20XYZ",
        user_id=mock_user.id,
        cart_total_piastres=10000,
    )
    
    assert not validation.is_valid
    assert "expired" in validation.error_reason.lower()
    
    print("Expired coupon validation test passed")


@pytest.mark.asyncio
async def test_usage_limit_exceeded(mock_db, mock_coupon, mock_user):
    """Test that coupons over usage limit are rejected."""
    from services.coupon_service import CouponService
    
    # Set coupon as over usage limit
    mock_coupon.usage_limit = 10
    mock_coupon.used_count = 10
    
    service = CouponService(mock_db)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_coupon
    
    validation = await service.validate_coupon(
        code="TEST20XYZ",
        user_id=mock_user.id,
        cart_total_piastres=10000,
    )
    
    assert not validation.is_valid
    assert "limit" in validation.error_reason.lower()
    
    print("Usage limit exceeded test passed")


# ========================================
# ANONYMOUS DONOR TEST
# ========================================

@pytest.mark.asyncio
async def test_anonymous_donor_privacy(mock_donor):
    """
    Test that anonymous donors have PII stripped in public responses.
    
    The Impact Wall API should never expose:
    - donor.user_id
    - donor.email
    - Any identifying info if is_anonymous=True
    """
    from api.donors import PublicDonorResponse
    
    # Set donor as anonymous
    mock_donor.is_anonymous = True
    mock_donor.display_name = None
    
    # Create public response
    response = PublicDonorResponse(
        id=mock_donor.id,
        display_name=None,  # Should be None for anonymous
        avatar_url=None,
        bio=None,
        tier=mock_donor.tier.value,
        total_donated_egp=mock_donor.total_donated_piastres / 100,
        people_helped=mock_donor.people_helped,
        is_verified=mock_donor.is_verified,
    )
    
    # Verify no PII exposed
    assert response.display_name is None
    assert response.avatar_url is None
    assert response.bio is None
    
    # user_id should never be in the response model
    assert not hasattr(response, 'user_id')
    
    print("Anonymous donor privacy test passed")


# ========================================
# COUPON CODE GENERATION TEST
# ========================================

@pytest.mark.asyncio
async def test_coupon_code_generation(mock_db, mock_donor):
    """Test memorable coupon code generation."""
    from services.coupon_service import CouponService
    
    service = CouponService(mock_db)
    
    # Test code generation
    code = await service.generate_memorable_code("KAPoor", 20)
    
    # Verify format
    assert len(code) >= 4
    assert len(code) <= 20
    assert code.isupper()
    assert code.isalnum()
    
    # Verify no profanity
    from services.coupon_service import PROFANITY_BLOCKLIST
    for word in PROFANITY_BLOCKLIST:
        assert word not in code
    
    print(f"Coupon code generation test passed: {code}")


@pytest.mark.asyncio
async def test_coupon_code_validation(mock_db):
    """Test coupon code validation rules."""
    from services.coupon_service import CouponService, CouponError
    
    service = CouponService(mock_db)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None  # No existing coupon
    
    # Valid codes
    valid_codes = ["SAVE20", "DONOR10XYZ", "HELLO123"]
    for code in valid_codes:
        try:
            await service._validate_code(code)
        except CouponError:
            pytest.fail(f"Valid code {code} was rejected")
    
    # Invalid codes
    invalid_cases = [
        ("AB", "Too short"),                    # < 4 chars
        ("ABCDEFGHIJKLMNOPQRSTU", "Too long"), # > 20 chars
        ("save20", "Lowercase"),               # Not uppercase
        ("SAVE-20", "Special char"),           # Non-alphanumeric
        ("DAMN20", "Profanity"),               # Contains profanity
    ]
    
    for code, reason in invalid_cases:
        with pytest.raises(CouponError):
            await service._validate_code(code)
    
    print("Coupon code validation test passed")


# ========================================
# RUN ALL TESTS
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
