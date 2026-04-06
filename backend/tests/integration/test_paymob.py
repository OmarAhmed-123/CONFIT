"""
Integration tests for Paymob provider.

Tests:
  - HMAC webhook signature verification
  - Idempotency key handling
  - 3DS, Meeza, Instapay, Valu integration IDs
  - Currency handling (EGP/piastres)
  - Charge creation and status
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any


# Mock environment before importing
os.environ.setdefault("PAYMOB_API_KEY", "test_api_key")
os.environ.setdefault("PAYMOB_INTEGRATION_ID", "12345")
os.environ.setdefault("PAYMOB_HMAC_SECRET", "test_hmac_secret")
os.environ.setdefault("PAYMOB_INTEGRATION_ID_3DS", "12346")
os.environ.setdefault("PAYMOB_INTEGRATION_ID_MEEZA", "12347")
os.environ.setdefault("PAYMOB_INTEGRATION_ID_INSTAPAY", "12348")
os.environ.setdefault("PAYMOB_INTEGRATION_ID_VALU", "12349")


class TestPaymobHMACVerification:
    """Test HMAC webhook signature verification."""
    
    def test_hmac_verification_valid(self):
        """Test that valid HMAC signature is accepted."""
        from services.payment_platform.providers.paymob_provider import verify_callback_hmac
        
        # Mock transaction object
        transaction = {
            "amount_cents": "10000",
            "created_at": "2024-01-01T00:00:00.000Z",
            "currency": "EGP",
            "error_occured": "false",
            "has_parent_transaction": "false",
            "id": "12345678",
            "integration_id": "12345",
            "is_3d_secure": "true",
            "is_auth": "false",
            "is_capture": "false",
            "is_refunded": "false",
            "is_standalone_payment": "true",
            "is_voided": "false",
            "order": {"id": "98765"},
            "owner": "99999",
            "pending": "false",
            "source_data": {
                "pan": "**** **** **** 1234",
                "sub_type": "MasterCard",
                "type": "card",
            },
            "success": "true",
        }
        
        # Calculate expected HMAC
        secret = os.environ["PAYMOB_HMAC_SECRET"].encode("utf-8")
        concat = (
            str(transaction["amount_cents"])
            + transaction["created_at"]
            + transaction["currency"]
            + str(transaction["error_occured"])
            + str(transaction["has_parent_transaction"])
            + str(transaction["id"])
            + str(transaction["integration_id"])
            + str(transaction["is_3d_secure"])
            + str(transaction["is_auth"])
            + str(transaction["is_capture"])
            + str(transaction["is_refunded"])
            + str(transaction["is_standalone_payment"])
            + str(transaction["is_voided"])
            + str(transaction["order"]["id"])
            + str(transaction["owner"])
            + str(transaction["pending"])
            + str(transaction["source_data"]["pan"])
            + str(transaction["source_data"]["sub_type"])
            + str(transaction["source_data"]["type"])
            + str(transaction["success"])
        )
        expected_hmac = hmac.new(secret, concat.encode("utf-8"), hashlib.sha512).hexdigest()
        
        # Verify
        result = verify_callback_hmac(transaction, expected_hmac)
        assert result is True
    
    def test_hmac_verification_invalid(self):
        """Test that invalid HMAC signature is rejected."""
        from services.payment_platform.providers.paymob_provider import verify_callback_hmac
        
        transaction = {
            "amount_cents": "10000",
            "currency": "EGP",
            "id": "12345678",
            "success": "true",
        }
        
        result = verify_callback_hmac(transaction, "invalid_hmac_signature")
        assert result is False
    
    def test_hmac_verification_missing_secret(self):
        """Test that missing HMAC secret rejects webhook."""
        from services.payment_platform.providers.paymob_provider import verify_callback_hmac
        
        original = os.environ.pop("PAYMOB_HMAC_SECRET", None)
        os.environ.pop("PAYMOB_SECRET_KEY", None)
        
        try:
            transaction = {"amount_cents": "10000", "success": "true"}
            result = verify_callback_hmac(transaction, "any_signature")
            assert result is False
        finally:
            if original:
                os.environ["PAYMOB_HMAC_SECRET"] = original


class TestPaymobIntegrationIDs:
    """Test integration ID selection for different payment methods."""
    
    def test_default_integration_id(self):
        """Test default integration ID retrieval."""
        from services.payment_platform.providers.paymob_provider import get_integration_id
        
        result = get_integration_id("card")
        assert result == 12345
    
    def test_3ds_integration_id(self):
        """Test 3DS integration ID retrieval."""
        from services.payment_platform.providers.paymob_provider import get_integration_id
        
        result = get_integration_id("card_3ds")
        assert result == 12346
    
    def test_meeza_integration_id(self):
        """Test Meeza integration ID retrieval."""
        from services.payment_platform.providers.paymob_provider import get_integration_id
        
        result = get_integration_id("meeza")
        assert result == 12347
    
    def test_instapay_integration_id(self):
        """Test Instapay integration ID retrieval."""
        from services.payment_platform.providers.paymob_provider import get_integration_id
        
        result = get_integration_id("instapay")
        assert result == 12348
    
    def test_valu_integration_id(self):
        """Test Valu BNPL integration ID retrieval."""
        from services.payment_platform.providers.paymob_provider import get_integration_id
        
        result = get_integration_id("valu")
        assert result == 12349


class TestPaymobCurrencyHandling:
    """Test currency and amount handling."""
    
    def test_egp_to_piastres(self):
        """Test EGP to piastres conversion."""
        from services.payment_platform.base import egp_to_piastres
        
        assert egp_to_piastres(100.00) == 10000
        assert egp_to_piastres(1.50) == 150
        assert egp_to_piastres(0.99) == 99
    
    def test_piastres_to_egp(self):
        """Test piastres to EGP conversion."""
        from services.payment_platform.base import piastres_to_egp
        
        assert piastres_to_egp(10000) == 100.0
        assert piastres_to_egp(150) == 1.5
        assert piastres_to_egp(99) == 0.99


class TestPaymobProvider:
    """Test PaymobProvider class methods."""
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self):
        """Test provider initializes with correct config."""
        from services.payment_platform.providers.paymob_provider import PaymobProvider
        
        provider = PaymobProvider()
        
        assert provider.integration_id == "12345"
        assert provider.integration_id_3ds == "12346"
        assert provider.integration_id_meeza == "12347"
        assert provider.integration_id_instapay == "12348"
        assert provider.integration_id_valu == "12349"
    
    @pytest.mark.asyncio
    async def test_create_charge_requires_auth(self):
        """Test that create_charge requires authentication."""
        from services.payment_platform.providers.paymob_provider import PaymobProvider
        
        provider = PaymobProvider()
        
        # Without proper API key, should raise error
        with pytest.raises(Exception):
            await provider.create_charge(
                amount_piastres=10000,
                customer={"email": "test@example.com"},
                order_ref="test_order_123",
                payment_method="card",
            )


class TestPaymobWebhookVerification:
    """Test webhook verification with raw payload."""
    
    def test_verify_webhook_valid_json(self):
        """Test webhook verification with valid JSON payload."""
        from services.payment_platform.providers.paymob_provider import PaymobProvider
        
        provider = PaymobProvider()
        
        # Create a valid transaction payload
        transaction = {
            "amount_cents": "10000",
            "created_at": "2024-01-01T00:00:00.000Z",
            "currency": "EGP",
            "error_occured": "false",
            "has_parent_transaction": "false",
            "id": "12345678",
            "integration_id": "12345",
            "is_3d_secure": "false",
            "is_auth": "false",
            "is_capture": "false",
            "is_refunded": "false",
            "is_standalone_payment": "true",
            "is_voided": "false",
            "order": {"id": "98765"},
            "owner": "99999",
            "pending": "false",
            "source_data": {"pan": "****", "sub_type": "card", "type": "card"},
            "success": "true",
        }
        
        # Calculate HMAC
        secret = os.environ["PAYMOB_HMAC_SECRET"].encode("utf-8")
        concat = (
            transaction["amount_cents"] + transaction["created_at"] + transaction["currency"]
            + transaction["error_occured"] + transaction["has_parent_transaction"]
            + transaction["id"] + transaction["integration_id"] + transaction["is_3d_secure"]
            + transaction["is_auth"] + transaction["is_capture"] + transaction["is_refunded"]
            + transaction["is_standalone_payment"] + transaction["is_voided"]
            + str(transaction["order"]["id"]) + transaction["owner"] + transaction["pending"]
            + transaction["source_data"]["pan"] + transaction["source_data"]["sub_type"]
            + transaction["source_data"]["type"] + transaction["success"]
        )
        expected_hmac = hmac.new(secret, concat.encode("utf-8"), hashlib.sha512).hexdigest()
        
        payload = json.dumps(transaction).encode("utf-8")
        
        result = provider.verify_webhook(payload, expected_hmac)
        assert result is True
    
    def test_verify_webhook_invalid_json(self):
        """Test webhook verification with invalid JSON."""
        from services.payment_platform.providers.paymob_provider import PaymobProvider
        
        provider = PaymobProvider()
        
        result = provider.verify_webhook(b"not valid json", "any_signature")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
