"""
Integration tests for Fawry provider.

Tests:
  - MD5 webhook signature verification
  - Charge creation (CARD, COD, WALLET, FAWRY_REF_NUMBER)
  - Refund processing
  - Currency handling (EGP/piastres)
"""

from __future__ import annotations

import hashlib
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any


# Mock environment before importing
os.environ.setdefault("FAWRY_ENVIRONMENT", "staging")
os.environ.setdefault("FAWRY_MERCHANT_CODE", "test_merchant")
os.environ.setdefault("FAWRY_SECURITY_KEY", "test_security_key")
os.environ.setdefault("FAWRY_CALLBACK_URL", "https://api.confit.app/webhooks/fawry")


class TestFawrySignatureVerification:
    """Test MD5 signature verification."""
    
    def test_signature_generation(self):
        """Test that signature is correctly generated."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        # Signature = MD5(merchantCode + orderRef + amount + securityKey)
        merchant_code = "test_merchant"
        order_ref = "ORDER123"
        amount = "100.00"
        
        expected = hashlib.md5(
            f"{merchant_code}{order_ref}{amount}{provider.security_key}".encode("utf-8")
        ).hexdigest()
        
        result = provider._build_signature(merchant_code, order_ref, amount)
        
        assert result == expected
    
    def test_webhook_signature_valid(self):
        """Test valid webhook signature verification."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        # Webhook signature format:
        # MD5(merchantCode + referenceNumber + paymentMethod + amount + status + securityKey)
        merchant_code = "test_merchant"
        reference_number = "REF123"
        payment_method = "CARD"
        amount = "100.00"
        status = "PAID"
        
        expected_sig = hashlib.md5(
            f"{merchant_code}{reference_number}{payment_method}{amount}{status}{provider.security_key}".encode("utf-8")
        ).hexdigest()
        
        payload_data = {
            "merchantCode": merchant_code,
            "referenceNumber": reference_number,
            "paymentMethod": payment_method,
            "amount": amount,
            "statusCode": status,
        }
        payload = json.dumps(payload_data).encode("utf-8")
        
        result = provider.verify_webhook(payload, expected_sig)
        assert result is True
    
    def test_webhook_signature_invalid(self):
        """Test invalid webhook signature is rejected."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        payload_data = {
            "merchantCode": "test_merchant",
            "referenceNumber": "REF123",
            "paymentMethod": "CARD",
            "amount": "100.00",
            "statusCode": "PAID",
        }
        payload = json.dumps(payload_data).encode("utf-8")
        
        result = provider.verify_webhook(payload, "invalid_signature")
        assert result is False
    
    def test_webhook_invalid_json(self):
        """Test that invalid JSON payload is rejected."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        result = provider.verify_webhook(b"not valid json", "any_signature")
        assert result is False


class TestFawryPaymentMethods:
    """Test different payment methods."""
    
    @pytest.mark.asyncio
    async def test_card_payment_method(self):
        """Test CARD payment method configuration."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        # Mock HTTP client
        with patch.object(provider, '_get_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "statusCode": "200",
                "referenceNumber": "FAWRY123",
                "redirectUrl": "https://pay.fawry.com/3ds/...",
            }
            mock_client.return_value.request = AsyncMock(return_value=mock_response)
            
            result = await provider.create_charge(
                amount_piastres=10000,  # 100 EGP
                customer={"email": "test@example.com", "phone": "+201234567890"},
                order_ref="ORDER123",
                payment_method="CARD",
                card_token="test_card_token",
            )
            
            assert result["payment_method"] == "CARD"
            assert result["provider"] == "fawry"
            assert "redirect_url" in result
    
    @pytest.mark.asyncio
    async def test_cod_payment_method(self):
        """Test CASH_ON_DELIVERY payment method."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        with patch.object(provider, '_get_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "statusCode": "200",
                "referenceNumber": "COD123",
            }
            mock_client.return_value.request = AsyncMock(return_value=mock_response)
            
            result = await provider.create_charge(
                amount_piastres=10000,
                customer={"email": "test@example.com", "phone": "+201234567890"},
                order_ref="ORDER123",
                payment_method="CASH_ON_DELIVERY",
                delivery_address={"city": "Cairo", "street": "Test Street"},
            )
            
            assert result["payment_method"] == "CASH_ON_DELIVERY"
            assert result["provider"] == "fawry"
    
    @pytest.mark.asyncio
    async def test_fawry_ref_number_payment(self):
        """Test FAWRY_REF_NUMBER payment method (pay at kiosk)."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        with patch.object(provider, '_get_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "statusCode": "200",
                "referenceNumber": "FAWRYREF123",
            }
            mock_client.return_value.request = AsyncMock(return_value=mock_response)
            
            result = await provider.create_charge(
                amount_piastres=10000,
                customer={"email": "test@example.com", "phone": "+201234567890"},
                order_ref="ORDER123",
                payment_method="FAWRY_REF_NUMBER",
            )
            
            assert result["payment_method"] == "FAWRY_REF_NUMBER"
            assert "fawry_reference" in result
            assert "instructions" in result
    
    @pytest.mark.asyncio
    async def test_wallet_payment_method(self):
        """Test WALLET payment method."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        with patch.object(provider, '_get_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "statusCode": "200",
                "referenceNumber": "WALLET123",
            }
            mock_client.return_value.request = AsyncMock(return_value=mock_response)
            
            result = await provider.create_charge(
                amount_piastres=10000,
                customer={"email": "test@example.com", "phone": "+201234567890"},
                order_ref="ORDER123",
                payment_method="WALLET",
                wallet_number="01012345678",
            )
            
            assert result["payment_method"] == "WALLET"


class TestFawryRefund:
    """Test refund processing."""
    
    @pytest.mark.asyncio
    async def test_refund_success(self):
        """Test successful refund."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        with patch.object(provider, '_get_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "statusCode": "200",
                "refundId": "REFUND123",
            }
            mock_client.return_value.request = AsyncMock(return_value=mock_response)
            
            result = await provider.refund(
                reference_number="FAWRY123",
                amount_piastres=5000,  # 50 EGP partial refund
                reason="Customer request",
            )
            
            assert result["provider"] == "fawry"
            assert result["reference_number"] == "FAWRY123"
            assert result["amount_refunded"] == 50.0


class TestFawryStatusMapping:
    """Test status code mapping."""
    
    def test_status_mapping(self):
        """Test Fawry status codes are mapped correctly."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        
        provider = FawryProvider()
        
        assert provider._map_status("UNPAID") == "pending"
        assert provider._map_status("PAID") == "succeeded"
        assert provider._map_status("FAILED") == "failed"
        assert provider._map_status("EXPIRED") == "expired"
        assert provider._map_status("REFUNDED") == "refunded"
        assert provider._map_status("CANCELED") == "canceled"
        assert provider._map_status("SUCCESS") == "succeeded"
        assert provider._map_status("DECLINED") == "failed"
        assert provider._map_status("unknown") == "unknown"


class TestFawryProviderErrors:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_missing_credentials(self):
        """Test that missing credentials raise error."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        from services.payment_platform.base import PaymentProviderError
        
        provider = FawryProvider()
        provider.merchant_code = ""
        provider.security_key = ""
        
        with pytest.raises(PaymentProviderError) as exc_info:
            await provider.create_charge(
                amount_piastres=10000,
                customer={"email": "test@example.com"},
                order_ref="ORDER123",
            )
        
        assert "credentials not configured" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test HTTP error handling."""
        from services.payment_platform.providers.fawry_provider import FawryProvider
        from services.payment_platform.base import PaymentProviderError
        import httpx
        
        provider = FawryProvider()
        
        with patch.object(provider, '_get_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad request", request=MagicMock(), response=mock_response
            )
            mock_client.return_value.request = AsyncMock(return_value=mock_response)
            
            with pytest.raises(PaymentProviderError):
                await provider.create_charge(
                    amount_piastres=10000,
                    customer={"email": "test@example.com"},
                    order_ref="ORDER123",
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
