"""
CONFIT Backend - CARE Service Tests
====================================
Unit tests for the CARE service layer.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

from services.care_service import (
    CampaignService,
    BeneficiaryService,
    VoucherService,
    SessionService,
    CareOrderService,
    CareAnalyticsService,
    CareException,
    VoucherNotFoundException,
    VoucherExpiredException,
    BudgetExceededException,
    OTPInvalidException,
    SessionInvalidException,
)
from schemas.care_schemas import (
    CampaignCreate,
    CampaignUpdate,
    BeneficiaryCreate,
    VoucherValidate,
    SessionInitiate,
    OTPVerify,
    CareOrderCreate,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_campaign_repo():
    """Mock campaign repository."""
    return MagicMock()


@pytest.fixture
def mock_beneficiary_repo():
    """Mock beneficiary repository."""
    return MagicMock()


@pytest.fixture
def mock_voucher_repo():
    """Mock voucher repository."""
    return MagicMock()


@pytest.fixture
def mock_session_repo():
    """Mock session repository."""
    return MagicMock()


@pytest.fixture
def sample_campaign_data():
    """Sample campaign creation data."""
    return CampaignCreate(
        campaign_name="Test Campaign",
        campaign_type="individual",
        description="A test campaign",
        budget_per_person=1500.0,
        currency="EGP",
        voucher_expiry_days=30,
    )


@pytest.fixture
def sample_beneficiary_data():
    """Sample beneficiary creation data."""
    return BeneficiaryCreate(
        name="John Doe",
        email="john@example.com",
        phone="+201234567890",
        age_group="26-35",
    )


@pytest.fixture
def sample_campaign():
    """Sample campaign ORM object."""
    campaign = MagicMock()
    campaign.id = str(uuid4())
    campaign.donor_id = str(uuid4())
    campaign.campaign_name = "Test Campaign"
    campaign.campaign_type = "individual"
    campaign.status = "draft"
    campaign.total_beneficiaries = 0
    campaign.total_budget_allocated = 0.0
    campaign.total_budget_used = 0.0
    campaign.currency = "EGP"
    campaign.created_at = datetime.now(timezone.utc)
    return campaign


@pytest.fixture
def sample_beneficiary():
    """Sample beneficiary ORM object."""
    beneficiary = MagicMock()
    beneficiary.id = str(uuid4())
    beneficiary.campaign_id = str(uuid4())
    beneficiary.name = "John Doe"
    beneficiary.email = "john@example.com"
    beneficiary.phone = "+201234567890"
    beneficiary.budget_allocated = 1500.0
    beneficiary.budget_used = 0.0
    beneficiary.budget_remaining = 1500.0
    beneficiary.status = "pending"
    return beneficiary


@pytest.fixture
def sample_voucher():
    """Sample voucher ORM object."""
    voucher = MagicMock()
    voucher.id = str(uuid4())
    voucher.voucher_token = "CARE-TEST123456"
    voucher.campaign_id = str(uuid4())
    voucher.beneficiary_id = str(uuid4())
    voucher.budget_allocated = 1500.0
    voucher.budget_used = 0.0
    voucher.budget_remaining = 1500.0
    voucher.currency = "EGP"
    voucher.status = "active"
    voucher.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    return voucher


@pytest.fixture
def sample_session():
    """Sample session ORM object."""
    session = MagicMock()
    session.id = str(uuid4())
    session.session_token = "sess_test123456"
    session.voucher_id = str(uuid4())
    session.status = "pending"
    session.otp_verified = False
    session.otp_hash = "hashed_otp"
    session.otp_attempts = 0
    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    session.created_at = datetime.now(timezone.utc)
    return session


# ============================================
# Campaign Service Tests
# ============================================

class TestCampaignService:
    """Tests for CampaignService."""

    def test_create_campaign_success(self, mock_db, sample_campaign_data):
        """Test successful campaign creation."""
        service = CampaignService(mock_db)
        
        with patch.object(service, 'campaign_repo') as mock_repo:
            mock_campaign = MagicMock()
            mock_campaign.id = str(uuid4())
            mock_campaign.campaign_name = sample_campaign_data.campaign_name
            mock_repo.create.return_value = mock_campaign
            
            result = service.create_campaign(
                donor_id=str(uuid4()),
                campaign_data=sample_campaign_data
            )
            
            assert result is not None
            mock_repo.create.assert_called_once()

    def test_get_campaign_by_id(self, mock_db, sample_campaign):
        """Test retrieving campaign by ID."""
        service = CampaignService(mock_db)
        
        with patch.object(service, 'campaign_repo') as mock_repo:
            mock_repo.get_by_id.return_value = sample_campaign
            
            result = service.get_campaign_by_id(sample_campaign.id)
            
            assert result.id == sample_campaign.id
            mock_repo.get_by_id.assert_called_once_with(sample_campaign.id)

    def test_update_campaign_success(self, mock_db, sample_campaign):
        """Test successful campaign update."""
        service = CampaignService(mock_db)
        
        update_data = CampaignUpdate(
            campaign_name="Updated Name",
            description="Updated description"
        )
        
        with patch.object(service, 'campaign_repo') as mock_repo:
            mock_repo.get_by_id.return_value = sample_campaign
            mock_repo.update.return_value = sample_campaign
            
            result = service.update_campaign(
                campaign_id=sample_campaign.id,
                donor_id=sample_campaign.donor_id,
                update_data=update_data
            )
            
            mock_repo.update.assert_called_once()

    def test_activate_campaign_success(self, mock_db, sample_campaign, sample_beneficiary_data):
        """Test successful campaign activation."""
        service = CampaignService(mock_db)
        
        sample_campaign.status = "draft"
        
        activation_data = MagicMock()
        activation_data.beneficiaries = [sample_beneficiary_data]
        activation_data.send_invitations = True
        
        with patch.object(service, 'campaign_repo') as mock_repo:
            with patch.object(service, 'beneficiary_service') as mock_ben_service:
                mock_repo.get_by_id.return_value = sample_campaign
                mock_repo.update.return_value = sample_campaign
                mock_ben_service.add_beneficiary.return_value = MagicMock()
                
                result = service.activate_campaign(
                    campaign_id=sample_campaign.id,
                    donor_id=sample_campaign.donor_id,
                    activation_data=activation_data
                )
                
                assert result is not None

    def test_get_campaigns_by_donor(self, mock_db, sample_campaign):
        """Test retrieving campaigns by donor ID."""
        service = CampaignService(mock_db)
        
        with patch.object(service, 'campaign_repo') as mock_repo:
            mock_repo.get_by_donor.return_value = ([sample_campaign], 1)
            
            campaigns, total = service.get_campaigns_by_donor(
                donor_id=sample_campaign.donor_id
            )
            
            assert len(campaigns) == 1
            assert total == 1


# ============================================
# Beneficiary Service Tests
# ============================================

class TestBeneficiaryService:
    """Tests for BeneficiaryService."""

    def test_add_beneficiary_success(self, mock_db, sample_beneficiary_data, sample_campaign):
        """Test successful beneficiary addition."""
        service = BeneficiaryService(mock_db)
        
        with patch.object(service, 'beneficiary_repo') as mock_repo:
            with patch.object(service, 'voucher_service') as mock_voucher:
                mock_repo.get_by_contact.return_value = None
                mock_repo.create.return_value = MagicMock()
                mock_voucher.create_voucher.return_value = MagicMock()
                
                result = service.add_beneficiary(
                    campaign_id=sample_campaign.id,
                    beneficiary_data=sample_beneficiary_data,
                    create_voucher=True
                )
                
                assert result is not None

    def test_bulk_add_beneficiaries(self, mock_db, sample_beneficiary_data, sample_campaign):
        """Test bulk beneficiary addition."""
        service = BeneficiaryService(mock_db)
        
        beneficiaries = [sample_beneficiary_data for _ in range(3)]
        
        with patch.object(service, 'add_beneficiary') as mock_add:
            mock_add.return_value = MagicMock()
            
            result = service.bulk_add_beneficiaries(
                campaign_id=sample_campaign.id,
                beneficiaries=beneficiaries
            )
            
            assert result['total'] == 3
            assert result['succeeded'] == 3
            assert result['failed'] == 0


# ============================================
# Voucher Service Tests
# ============================================

class TestVoucherService:
    """Tests for VoucherService."""

    def test_create_voucher_success(self, mock_db, sample_campaign, sample_beneficiary):
        """Test successful voucher creation."""
        service = VoucherService(mock_db)
        
        with patch.object(service, 'voucher_repo') as mock_repo:
            mock_repo.create.return_value = MagicMock()
            
            result = service.create_voucher(
                campaign_id=sample_campaign.id,
                beneficiary_id=sample_beneficiary.id
            )
            
            assert result is not None

    def test_validate_voucher_success(self, mock_db, sample_voucher):
        """Test successful voucher validation."""
        service = VoucherService(mock_db)
        
        with patch.object(service, 'voucher_repo') as mock_repo:
            mock_repo.get_by_token.return_value = sample_voucher
            
            result = service.validate_voucher(sample_voucher.voucher_token)
            
            assert result is not None

    def test_validate_voucher_not_found(self, mock_db):
        """Test voucher validation with invalid token."""
        service = VoucherService(mock_db)
        
        with patch.object(service, 'voucher_repo') as mock_repo:
            mock_repo.get_by_token.return_value = None
            
            with pytest.raises(VoucherNotFoundException):
                service.validate_voucher("INVALID-TOKEN")

    def test_validate_voucher_expired(self, mock_db, sample_voucher):
        """Test voucher validation with expired voucher."""
        service = VoucherService(mock_db)
        
        # Make voucher expired
        sample_voucher.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        with patch.object(service, 'voucher_repo') as mock_repo:
            mock_repo.get_by_token.return_value = sample_voucher
            
            with pytest.raises(VoucherExpiredException):
                service.validate_voucher(sample_voucher.voucher_token)

    def test_record_voucher_usage(self, mock_db, sample_voucher):
        """Test recording voucher usage."""
        service = VoucherService(mock_db)
        
        sample_voucher.budget_remaining = 1500.0
        
        with patch.object(service, 'voucher_repo') as mock_repo:
            mock_repo.get_by_id.return_value = sample_voucher
            mock_repo.update.return_value = sample_voucher
            
            result = service.record_usage(
                voucher_id=sample_voucher.id,
                amount=500.0
            )
            
            assert result is not None


# ============================================
# Session Service Tests
# ============================================

class TestSessionService:
    """Tests for SessionService."""

    def test_initiate_session_success(self, mock_db, sample_voucher, sample_session):
        """Test successful session initiation."""
        service = SessionService(mock_db)
        
        with patch.object(service, 'session_repo') as mock_repo:
            with patch.object(service, 'voucher_service') as mock_voucher:
                mock_voucher.validate_voucher.return_value = sample_voucher
                mock_repo.create.return_value = sample_session
                
                result = service.initiate_session(
                    voucher_token=sample_voucher.voucher_token,
                    ip_address="127.0.0.1",
                    user_agent="Test Agent"
                )
                
                assert result is not None

    def test_send_otp_success(self, mock_db, sample_session):
        """Test successful OTP generation and sending."""
        service = SessionService(mock_db)
        
        with patch.object(service, 'session_repo') as mock_repo:
            mock_repo.get_by_id.return_value = sample_session
            mock_repo.update.return_value = sample_session
            
            otp = service.send_otp(sample_session.id)
            
            assert otp is not None
            assert len(otp) == 6
            assert otp.isdigit()

    def test_verify_otp_success(self, mock_db, sample_session):
        """Test successful OTP verification."""
        service = SessionService(mock_db)
        
        # Generate OTP
        otp = "123456"
        
        with patch.object(service, 'session_repo') as mock_repo:
            with patch.object(service, '_verify_otp_hash') as mock_verify:
                mock_repo.get_by_id.return_value = sample_session
                mock_repo.update.return_value = sample_session
                mock_verify.return_value = True
                
                result = service.verify_otp(
                    session_id=sample_session.id,
                    otp_code=otp
                )
                
                assert result.otp_verified is True

    def test_verify_otp_invalid(self, mock_db, sample_session):
        """Test OTP verification with invalid code."""
        service = SessionService(mock_db)
        
        with patch.object(service, 'session_repo') as mock_repo:
            with patch.object(service, '_verify_otp_hash') as mock_verify:
                mock_repo.get_by_id.return_value = sample_session
                mock_verify.return_value = False
                
                with pytest.raises(OTPInvalidException):
                    service.verify_otp(
                        session_id=sample_session.id,
                        otp_code="000000"
                    )

    def test_validate_session_success(self, mock_db, sample_session, sample_voucher):
        """Test successful session validation."""
        service = SessionService(mock_db)
        
        sample_session.otp_verified = True
        sample_session.status = "authenticated"
        
        with patch.object(service, 'session_repo') as mock_repo:
            mock_repo.get_by_token.return_value = sample_session
            
            result = service.validate_session(sample_session.session_token)
            
            assert result is not None

    def test_validate_session_not_verified(self, mock_db, sample_session):
        """Test session validation when OTP not verified."""
        service = SessionService(mock_db)
        
        sample_session.otp_verified = False
        
        with patch.object(service, 'session_repo') as mock_repo:
            mock_repo.get_by_token.return_value = sample_session
            
            with pytest.raises(SessionInvalidException):
                service.validate_session(sample_session.session_token)


# ============================================
# Order Service Tests
# ============================================

class TestCareOrderService:
    """Tests for CareOrderService."""

    def test_create_order_success(self, mock_db, sample_session, sample_voucher):
        """Test successful order creation."""
        service = CareOrderService(mock_db)
        
        order_data = MagicMock()
        order_data.items = [
            MagicMock(product_id="prod1", quantity=2, price=500.0)
        ]
        
        sample_session.otp_verified = True
        sample_voucher.budget_remaining = 1500.0
        
        with patch.object(service, 'session_service') as mock_session:
            with patch.object(service, 'order_repo') as mock_repo:
                mock_session.validate_session.return_value = {
                    'session': sample_session,
                    'voucher': sample_voucher,
                }
                mock_repo.create.return_value = MagicMock()
                
                result = service.create_order(
                    session_token=sample_session.session_token,
                    order_data=order_data,
                    order_id="CARE-TEST123"
                )
                
                assert result is not None

    def test_create_order_budget_exceeded(self, mock_db, sample_session, sample_voucher):
        """Test order creation when budget exceeded."""
        service = CareOrderService(mock_db)
        
        order_data = MagicMock()
        order_data.items = [
            MagicMock(product_id="prod1", quantity=2, price=2000.0)
        ]
        
        sample_session.otp_verified = True
        sample_voucher.budget_remaining = 1500.0
        
        with patch.object(service, 'session_service') as mock_session:
            mock_session.validate_session.return_value = {
                'session': sample_session,
                'voucher': sample_voucher,
            }
            
            with pytest.raises(BudgetExceededException):
                service.create_order(
                    session_token=sample_session.session_token,
                    order_data=order_data,
                    order_id="CARE-TEST123"
                )


# ============================================
# Analytics Service Tests
# ============================================

class TestCareAnalyticsService:
    """Tests for CareAnalyticsService."""

    def test_get_donor_dashboard(self, mock_db):
        """Test retrieving donor dashboard data."""
        service = CareAnalyticsService(mock_db)
        
        with patch.object(service, 'campaign_repo') as mock_campaign:
            with patch.object(service, 'analytics_repo') as mock_analytics:
                mock_campaign.get_by_donor.return_value = ([], 0)
                mock_analytics.get_donor_summary.return_value = {
                    'total_donated': 0,
                    'total_beneficiaries': 0,
                }
                
                result = service.get_donor_dashboard(str(uuid4()))
                
                assert result is not None

    def test_get_campaign_analytics(self, mock_db, sample_campaign):
        """Test retrieving campaign analytics."""
        service = CareAnalyticsService(mock_db)
        
        with patch.object(service, 'analytics_repo') as mock_repo:
            mock_repo.get_by_campaign.return_value = MagicMock()
            
            result = service.get_campaign_analytics(sample_campaign.id)
            
            assert result is not None


# ============================================
# Run Tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
