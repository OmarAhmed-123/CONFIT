"""
CONFIT Backend - Donation System Tests
======================================
Integration tests for donation processing, credit generation, and redemption.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.donation_models import (
    Donation,
    DonorCredit,
    DonorRedemption,
    DonationConfig,
    DonationStatus,
    DonorCreditStatus,
)
from database.models import User
from services.donation_service import (
    DonationService,
    DonationError,
    InvalidAmountError,
    CreditExhaustedError,
    DuplicateTransactionError,
)


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        id="test-user-123",
        name="Test User",
        email="test@example.com",
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def donation_service(db_session):
    """Create a donation service instance."""
    return DonationService(db_session)


@pytest.fixture
def donation_config(db_session):
    """Create default donation configuration."""
    config = DonationConfig(
        min_donation_amount=Decimal("1.00"),
        max_donation_amount=Decimal("10000.00"),
        preset_amounts=[10, 25, 50, 100],
        default_expiry_days=365,
        enable_custom_amounts=True,
    )
    db_session.add(config)
    db_session.commit()
    return config


# ============================================
# CONFIGURATION TESTS
# ============================================

class TestDonationConfig:
    """Tests for donation configuration."""

    def test_get_config_creates_default(self, db_session, donation_service):
        """Should create default config if none exists."""
        config = donation_service.get_config()
        
        assert config is not None
        assert config.min_donation_amount == Decimal("1.00")
        assert config.max_donation_amount == Decimal("10000.00")
        assert config.default_expiry_days == 365

    def test_get_config_returns_existing(self, db_session, donation_service, donation_config):
        """Should return existing config."""
        config = donation_service.get_config()
        
        assert config.id == donation_config.id


# ============================================
# AMOUNT VALIDATION TESTS
# ============================================

class TestAmountValidation:
    """Tests for donation amount validation."""

    def test_valid_amount(self, donation_service, donation_config):
        """Should accept valid amount."""
        is_valid, error = donation_service.validate_amount(Decimal("50.00"))
        
        assert is_valid is True
        assert error is None

    def test_amount_below_minimum(self, donation_service, donation_config):
        """Should reject amount below minimum."""
        is_valid, error = donation_service.validate_amount(Decimal("0.50"))
        
        assert is_valid is False
        assert "Minimum" in error

    def test_amount_above_maximum(self, donation_service, donation_config):
        """Should reject amount above maximum."""
        is_valid, error = donation_service.validate_amount(Decimal("15000.00"))
        
        assert is_valid is False
        assert "Maximum" in error

    def test_amount_at_minimum(self, donation_service, donation_config):
        """Should accept amount at minimum boundary."""
        is_valid, error = donation_service.validate_amount(Decimal("1.00"))
        
        assert is_valid is True

    def test_amount_at_maximum(self, donation_service, donation_config):
        """Should accept amount at maximum boundary."""
        is_valid, error = donation_service.validate_amount(Decimal("10000.00"))
        
        assert is_valid is True


# ============================================
# DONATION CREATION TESTS
# ============================================

class TestDonationCreation:
    """Tests for creating donations."""

    def test_create_pending_donation(self, donation_service, test_user, donation_config):
        """Should create a pending donation."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
            payment_method="card",
        )
        
        assert donation.id is not None
        assert donation.user_id == test_user.id
        assert donation.amount == Decimal("50.00")
        assert donation.status == DonationStatus.PENDING
        assert donation.payment_method == "card"

    def test_create_donation_with_metadata(self, donation_service, test_user, donation_config):
        """Should store IP address and user agent."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("25.00"),
            payment_method="card",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        
        assert donation.ip_address == "192.168.1.1"
        assert donation.user_agent == "Mozilla/5.0"

    def test_duplicate_pending_donation_prevented(self, donation_service, test_user, donation_config):
        """Should prevent duplicate pending donations within 5 minutes."""
        # Create first donation
        donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        
        # Try to create duplicate
        with pytest.raises(DuplicateTransactionError):
            donation_service.create_donation(
                user_id=test_user.id,
                amount=Decimal("50.00"),
            )

    def test_invalid_amount_raises_error(self, donation_service, test_user, donation_config):
        """Should raise InvalidAmountError for invalid amount."""
        with pytest.raises(InvalidAmountError):
            donation_service.create_donation(
                user_id=test_user.id,
                amount=Decimal("0.01"),
            )


# ============================================
# DONATION CONFIRMATION TESTS
# ============================================

class TestDonationConfirmation:
    """Tests for confirming donations."""

    def test_confirm_donation_generates_credit(self, donation_service, test_user, donation_config):
        """Should generate donor credit on confirmation."""
        # Create pending donation
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("100.00"),
        )
        
        # Confirm donation
        confirmed_donation, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123456",
            payment_intent_id="pi_123456",
        )
        
        assert confirmed_donation.status == DonationStatus.COMPLETED
        assert confirmed_donation.transaction_id == "txn_123456"
        assert confirmed_donation.completed_at is not None
        
        assert credit is not None
        assert credit.user_id == test_user.id
        assert credit.total_credit == Decimal("100.00")
        assert credit.remaining_credit == Decimal("100.00")
        assert credit.status == DonorCreditStatus.ACTIVE
        assert credit.coupon_code.startswith("DONOR-")

    def test_confirm_sets_expiration(self, donation_service, test_user, donation_config):
        """Should set expiration date based on config."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        assert credit.expires_at is not None
        # Should expire in ~365 days
        days_until_expiry = (credit.expires_at - datetime.now(timezone.utc)).days
        assert 364 <= days_until_expiry <= 366

    def test_confirm_already_completed_raises_error(self, donation_service, test_user, donation_config):
        """Should raise error if donation already completed."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        
        # Confirm once
        donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        # Try to confirm again
        with pytest.raises(DonationError):
            donation_service.confirm_donation(
                donation_id=donation.id,
                transaction_id="txn_456",
            )

    def test_duplicate_transaction_id_rejected(self, donation_service, test_user, donation_config):
        """Should reject duplicate transaction IDs."""
        # Create and confirm first donation
        donation1 = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        donation_service.confirm_donation(
            donation_id=donation1.id,
            transaction_id="txn_duplicate",
        )
        
        # Create second donation
        donation2 = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("75.00"),
        )
        
        # Try to use same transaction ID
        with pytest.raises(DuplicateTransactionError):
            donation_service.confirm_donation(
                donation_id=donation2.id,
                transaction_id="txn_duplicate",
            )


# ============================================
# COUPON CODE TESTS
# ============================================

class TestCouponCodes:
    """Tests for coupon code generation and validation."""

    def test_coupon_code_format(self, donation_service, test_user, donation_config):
        """Should generate coupon code in correct format."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        assert credit.coupon_code.startswith("DONOR-")
        assert len(credit.coupon_code) == 17  # DONOR-XXXXXX-XXXX

    def test_coupon_codes_are_unique(self, donation_service, test_user, donation_config):
        """Should generate unique coupon codes."""
        codes = set()
        
        for i in range(10):
            donation = donation_service.create_donation(
                user_id=test_user.id,
                amount=Decimal(f"{10 + i}.00"),
            )
            _, credit = donation_service.confirm_donation(
                donation_id=donation.id,
                transaction_id=f"txn_{i}",
            )
            codes.add(credit.coupon_code)
        
        assert len(codes) == 10

    def test_validate_valid_coupon(self, donation_service, test_user, donation_config):
        """Should validate a valid coupon code."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("100.00"),
        )
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        is_valid, returned_credit, error = donation_service.validate_coupon_code(
            code=credit.coupon_code,
            user_id=test_user.id,
        )
        
        assert is_valid is True
        assert returned_credit.id == credit.id
        assert error is None

    def test_validate_invalid_coupon(self, donation_service):
        """Should reject invalid coupon code."""
        is_valid, credit, error = donation_service.validate_coupon_code("INVALID-CODE")
        
        assert is_valid is False
        assert "Invalid" in error

    def test_validate_wrong_owner(self, donation_service, test_user, donation_config, db_session):
        """Should reject coupon belonging to another user."""
        # Create donation for test_user
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        # Try to validate with different user
        is_valid, _, error = donation_service.validate_coupon_code(
            code=credit.coupon_code,
            user_id="other-user-id",
        )
        
        assert is_valid is False
        assert "another account" in error.lower()


# ============================================
# CREDIT REDEMPTION TESTS
# ============================================

class TestCreditRedemption:
    """Tests for credit redemption."""

    def test_redeem_full_credit(self, donation_service, test_user, donation_config):
        """Should redeem full credit amount."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("100.00"),
        )
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        redemption, updated_credit = donation_service.redeem_credit(
            user_id=test_user.id,
            amount=Decimal("100.00"),
            order_id="order-123",
        )
        
        assert redemption.amount_used == Decimal("100.00")
        assert redemption.balance_before == Decimal("100.00")
        assert redemption.balance_after == Decimal("0.00")
        assert updated_credit.remaining_credit == Decimal("0.00")
        assert updated_credit.status == DonorCreditStatus.DEPLETED

    def test_redeem_partial_credit(self, donation_service, test_user, donation_config):
        """Should redeem partial credit amount."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("100.00"),
        )
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        redemption, updated_credit = donation_service.redeem_credit(
            user_id=test_user.id,
            amount=Decimal("30.00"),
        )
        
        assert redemption.amount_used == Decimal("30.00")
        assert updated_credit.remaining_credit == Decimal("70.00")
        assert updated_credit.status == DonorCreditStatus.ACTIVE

    def test_redeem_insufficient_credit(self, donation_service, test_user, donation_config):
        """Should raise error for insufficient credit."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        with pytest.raises(CreditExhaustedError):
            donation_service.redeem_credit(
                user_id=test_user.id,
                amount=Decimal("100.00"),
            )

    def test_redeem_from_multiple_credits(self, donation_service, test_user, donation_config):
        """Should redeem from multiple credits if needed."""
        # Create two donations
        donation1 = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        _, credit1 = donation_service.confirm_donation(
            donation_id=donation1.id,
            transaction_id="txn_1",
        )
        
        donation2 = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        _, credit2 = donation_service.confirm_donation(
            donation_id=donation2.id,
            transaction_id="txn_2",
        )
        
        # Redeem amount that requires both credits
        redemption, _ = donation_service.redeem_credit(
            user_id=test_user.id,
            amount=Decimal("75.00"),
        )
        
        # Check total redeemed
        assert redemption.amount_used == Decimal("75.00")
        
        # Check both credits were used
        db_session = donation_service._db
        credit1 = db_session.query(DonorCredit).filter_by(id=credit1.id).first()
        credit2 = db_session.query(DonorCredit).filter_by(id=credit2.id).first()
        
        assert credit1.remaining_credit == Decimal("0.00")
        assert credit2.remaining_credit == Decimal("25.00")


# ============================================
# EXPIRATION TESTS
# ============================================

class TestCreditExpiration:
    """Tests for credit expiration."""

    def test_expired_credit_rejected(self, donation_service, test_user, donation_config, db_session):
        """Should reject expired credit."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        # Manually expire the credit
        credit.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
        
        # Validate should fail
        is_valid, _, error = donation_service.validate_coupon_code(credit.coupon_code)
        
        assert is_valid is False
        assert "expired" in error.lower()

    def test_expired_status_updated(self, donation_service, test_user, donation_config, db_session):
        """Should update status to expired."""
        donation = donation_service.create_donation(
            user_id=test_user.id,
            amount=Decimal("50.00"),
        )
        _, credit = donation_service.confirm_donation(
            donation_id=donation.id,
            transaction_id="txn_123",
        )
        
        # Manually expire
        credit.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
        
        # Trigger expiration check
        donation_service._update_expired_credits()
        
        # Refresh from DB
        db_session.expire(credit)
        
        assert credit.status == DonorCreditStatus.EXPIRED


# ============================================
# STATISTICS TESTS
# ============================================

class TestDonationStats:
    """Tests for donation statistics."""

    def test_get_donation_stats(self, donation_service, test_user, donation_config):
        """Should return correct donation statistics."""
        # Create multiple donations
        for i, amount in enumerate([50, 100, 25]):
            donation = donation_service.create_donation(
                user_id=test_user.id,
                amount=Decimal(f"{amount}.00"),
            )
            donation_service.confirm_donation(
                donation_id=donation.id,
                transaction_id=f"txn_{i}",
            )
        
        # Redeem some credit
        donation_service.redeem_credit(
            user_id=test_user.id,
            amount=Decimal("75.00"),
        )
        
        stats = donation_service.get_donation_stats(test_user.id)
        
        assert stats["total_donations"] == 3
        assert stats["total_donated"] == 175.0
        assert stats["total_credit_earned"] == 175.0
        assert stats["total_credit_used"] == 75.0
        assert stats["total_credit_remaining"] == 100.0


# ============================================
# RUN TESTS
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
