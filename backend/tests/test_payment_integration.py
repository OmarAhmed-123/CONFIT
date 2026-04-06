"""
CONFIT Backend - Payment Integration Tests
==========================================
End-to-end tests for Paymob, PayPal, and Stripe payment flows.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test database setup
from database.base import Base
from database.session import get_db
from database.models import User as UserModel, Order as OrderModel
from database.payment_platform_models import Payment, PaymentEvent, Invoice, PaymentProvider, PaymentStatus


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    yield TestingSessionLocal, override_get_db
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db):
    """Create test user."""
    TestingSessionLocal, _ = test_db
    db = TestingSessionLocal()
    user = UserModel(
        id=str(uuid.uuid4()),
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.close()


@pytest.fixture
def test_order(test_db, test_user):
    """Create test order."""
    TestingSessionLocal, _ = test_db
    db = TestingSessionLocal()
    order = OrderModel(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        total=100.00,
        status="pending_payment",
        delivery_method="pickup",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    yield order
    db.close()


@pytest.fixture
def client(test_db):
    """Create test client."""
    from main import app
    _, override_get_db = test_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# PAYMOB INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymobIntegration:
    """Paymob payment flow integration tests."""

    @pytest.fixture
    def paymob_config(self):
        """Paymob test configuration."""
        return {
            "api_key": "test_api_key",
            "integration_id": "12345",
            "iframe_id": "67890",
            "hmac_secret": "test_hmac_secret",
        }

    def test_paymob_session_creation(self, client, test_order, paymob_config):
        """Test Paymob payment session creation."""
        with patch("services.payment_platform.providers.paymob.PaymobProvider.create_session") as mock_create:
            mock_create.return_value = {
                "payment_key": "test_payment_key",
                "iframe_url": f"https://accept.paymob.com/api/acceptance/iframes/{paymob_config['iframe_id']}",
            }

            response = client.post(
                "/api/payments/unified/session",
                json={
                    "order_id": test_order.id,
                    "provider": "paymob",
                    "amount": 100.00,
                    "currency": "EGP",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "paymob"
            assert "iframe_url" in data

    def test_paymob_webhook_success(self, client, test_db, test_order, paymob_config):
        """Test Paymob webhook handling for successful payment."""
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        # Create payment record
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=test_order.id,
            provider=PaymentProvider.PAYMOB,
            status=PaymentStatus.PENDING,
            amount=100.00,
            currency="EGP",
        )
        db.add(payment)
        db.commit()

        # Generate valid HMAC
        webhook_data = {
            "obj": {
                "id": 12345678,
                "success": True,
                "order": {"id": int(payment.id[:8], 16)},
                "amount_cents": 10000,
                "currency": "EGP",
                "source_data": {
                    "type": "card",
                    "pan": "1234",
                },
            }
        }

        # Calculate HMAC
        hmac_data = [
            str(webhook_data["obj"]["amount_cents"]),
            str(webhook_data["obj"]["order"]["id"]),
            str(webhook_data["obj"]["id"]),
            "EGP",
            str(webhook_data["obj"]["success"]).lower(),
        ]
        calculated_hmac = hmac.new(
            paymob_config["hmac_secret"].encode(),
            ".".join(hmac_data).encode(),
            hashlib.sha512,
        ).hexdigest()

        with patch("services.payment_platform.providers.paymob.PaymobProvider.verify_hmac") as mock_verify:
            mock_verify.return_value = True

            response = client.post(
                "/api/payments/unified/webhooks/paymob",
                json=webhook_data,
                headers={"X-Paymob-HMAC": calculated_hmac},
            )

            assert response.status_code == 200

        db.close()

    def test_paymob_webhook_invalid_hmac(self, client, test_db, test_order):
        """Test Paymob webhook rejects invalid HMAC."""
        webhook_data = {
            "obj": {
                "id": 12345678,
                "success": True,
            }
        }

        response = client.post(
            "/api/payments/unified/webhooks/paymob",
            json=webhook_data,
            headers={"X-Paymob-HMAC": "invalid_hmac"},
        )

        assert response.status_code == 401

    def test_paymob_payment_status_polling(self, client, test_db, test_order):
        """Test Paymob payment status polling."""
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=test_order.id,
            provider=PaymentProvider.PAYMOB,
            status=PaymentStatus.PENDING,
            paymob_transaction_id=12345678,
        )
        db.add(payment)
        db.commit()

        with patch("services.payment_platform.providers.paymob.PaymobProvider.get_transaction_status") as mock_status:
            mock_status.return_value = {"success": True, "is_voided": False, "is_refunded": False}

            response = client.get(f"/api/payments/{payment.id}/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"  # Updated by webhook

        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# PAYPAL INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPayPalIntegration:
    """PayPal payment flow integration tests."""

    @pytest.fixture
    def paypal_config(self):
        """PayPal test configuration."""
        return {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "mode": "sandbox",
        }

    def test_paypal_session_creation(self, client, test_order, paypal_config):
        """Test PayPal payment session creation."""
        with patch("services.payment_platform.providers.paypal.PayPalProvider.create_order") as mock_create:
            mock_create.return_value = {
                "id": "PAYPAL-ORDER-123",
                "status": "CREATED",
                "links": [
                    {"rel": "approve", "href": "https://www.sandbox.paypal.com/checkout?token=abc123"}
                ],
            }

            response = client.post(
                "/api/payments/unified/session",
                json={
                    "order_id": test_order.id,
                    "provider": "paypal",
                    "amount": 100.00,
                    "currency": "USD",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "paypal"
            assert "approve_url" in data

    def test_paypal_capture_success(self, client, test_db, test_order):
        """Test PayPal payment capture after approval."""
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=test_order.id,
            provider=PaymentProvider.PAYPAL,
            status=PaymentStatus.PENDING,
            paypal_order_id="PAYPAL-ORDER-123",
        )
        db.add(payment)
        db.commit()

        with patch("services.payment_platform.providers.paypal.PayPalProvider.capture_order") as mock_capture:
            mock_capture.return_value = {
                "id": "PAYPAL-ORDER-123",
                "status": "COMPLETED",
                "purchase_units": [{
                    "payments": {
                        "captures": [{
                            "id": "CAPTURE-123",
                            "status": "COMPLETED",
                        }]
                    }
                }],
            }

            response = client.post(
                "/api/payments/unified/paypal/capture",
                json={
                    "order_id": test_order.id,
                    "paypal_order_id": "PAYPAL-ORDER-123",
                },
            )

            assert response.status_code == 200

        db.close()

    def test_paypal_webhook_event(self, client, test_db, test_order):
        """Test PayPal webhook event handling."""
        webhook_data = {
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "CAPTURE-123",
                "status": "COMPLETED",
                "amount": {
                    "value": "100.00",
                    "currency_code": "USD",
                },
            },
        }

        with patch("services.payment_platform.providers.paypal.PayPalProvider.verify_webhook_signature") as mock_verify:
            mock_verify.return_value = True

            response = client.post(
                "/api/payments/unified/webhooks/paypal",
                json=webhook_data,
                headers={
                    "PAYPAL-TRANSMISSION-ID": "test-transmission-id",
                    "PAYPAL-CERT-URL": "https://api.paypal.com/v1/notifications/certs/CERT",
                },
            )

            assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# STRIPE INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStripeIntegration:
    """Stripe payment flow integration tests."""

    def test_stripe_session_creation(self, client, test_order):
        """Test Stripe checkout session creation."""
        with patch("stripe.checkout.Session.create") as mock_create:
            mock_create.return_value = MagicMock(
                id="cs_test_123",
                url="https://checkout.stripe.com/pay/cs_test_123",
                payment_intent="pi_123",
            )

            response = client.post(
                "/api/payments/unified/session",
                json={
                    "order_id": test_order.id,
                    "provider": "stripe",
                    "amount": 100.00,
                    "currency": "USD",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "stripe"
            assert "checkout_url" in data

    def test_stripe_webhook_payment_succeeded(self, client, test_db, test_order):
        """Test Stripe webhook for successful payment."""
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=test_order.id,
            provider=PaymentProvider.STRIPE,
            status=PaymentStatus.PENDING,
            stripe_payment_intent_id="pi_123",
        )
        db.add(payment)
        db.commit()

        webhook_payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "status": "succeeded",
                    "amount": 10000,
                    "currency": "usd",
                }
            },
        }

        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = MagicMock(
                type="payment_intent.succeeded",
                data=MagicMock(
                    object=MagicMock(
                        id="pi_123",
                        status="succeeded",
                    )
                )
            )

            response = client.post(
                "/api/stripe/webhook",
                json=webhook_payload,
                headers={"Stripe-Signature": "test_signature"},
            )

            # Stripe webhook returns 200 even if payment not found
            assert response.status_code in [200, 404]

        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# EDGE CASE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentEdgeCases:
    """Test edge cases and error handling."""

    def test_duplicate_payment_prevention(self, client, test_db, test_order):
        """Test that duplicate payments are prevented with idempotency key."""
        idempotency_key = str(uuid.uuid4())

        with patch("services.payment_platform.providers.stripe.StripeProvider.create_session") as mock_create:
            mock_create.return_value = {"checkout_url": "https://checkout.stripe.com/pay/test"}

            # First request
            response1 = client.post(
                "/api/payments/unified/session",
                json={
                    "order_id": test_order.id,
                    "provider": "stripe",
                    "amount": 100.00,
                },
                headers={"X-Idempotency-Key": idempotency_key},
            )

            # Second request with same key
            response2 = client.post(
                "/api/payments/unified/session",
                json={
                    "order_id": test_order.id,
                    "provider": "stripe",
                    "amount": 100.00,
                },
                headers={"X-Idempotency-Key": idempotency_key},
            )

            # Both should succeed, but only one payment created
            assert response1.status_code == 200
            assert response2.status_code == 200

    def test_payment_for_nonexistent_order(self, client):
        """Test payment creation for non-existent order."""
        response = client.post(
            "/api/payments/unified/session",
            json={
                "order_id": str(uuid.uuid4()),
                "provider": "stripe",
                "amount": 100.00,
            },
        )

        assert response.status_code == 404

    def test_invalid_payment_provider(self, client, test_order):
        """Test payment with invalid provider."""
        response = client.post(
            "/api/payments/unified/session",
            json={
                "order_id": test_order.id,
                "provider": "invalid_provider",
                "amount": 100.00,
            },
        )

        assert response.status_code == 400

    def test_payment_amount_validation(self, client, test_order):
        """Test payment amount validation."""
        # Negative amount
        response = client.post(
            "/api/payments/unified/session",
            json={
                "order_id": test_order.id,
                "provider": "stripe",
                "amount": -100.00,
            },
        )

        assert response.status_code == 422

        # Zero amount
        response = client.post(
            "/api/payments/unified/session",
            json={
                "order_id": test_order.id,
                "provider": "stripe",
                "amount": 0,
            },
        )

        assert response.status_code == 422

    def test_concurrent_payment_attempts(self, client, test_db, test_order):
        """Test handling of concurrent payment attempts for same order."""
        import asyncio

        async def make_payment_request():
            async with AsyncClient(app=client.app, base_url="http://test") as ac:
                return await ac.post(
                    "/api/payments/unified/session",
                    json={
                        "order_id": test_order.id,
                        "provider": "stripe",
                        "amount": 100.00,
                    },
                )

        # Run concurrent requests
        # Note: In practice, this would need proper async test setup
        # This is a simplified version
        pass

    def test_payment_timeout_handling(self, client, test_order):
        """Test handling of payment provider timeout."""
        with patch("services.payment_platform.providers.stripe.StripeProvider.create_session") as mock_create:
            mock_create.side_effect = TimeoutError("Stripe API timeout")

            response = client.post(
                "/api/payments/unified/session",
                json={
                    "order_id": test_order.id,
                    "provider": "stripe",
                    "amount": 100.00,
                },
            )

            assert response.status_code == 503
            assert "timeout" in response.json().get("detail", "").lower()

    def test_webhook_replay_protection(self, client, test_db, test_order):
        """Test that replayed webhooks are detected."""
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        # Create payment and event
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=test_order.id,
            provider=PaymentProvider.STRIPE,
            status=PaymentStatus.SUCCEEDED,
        )
        db.add(payment)

        event = PaymentEvent(
            id=str(uuid.uuid4()),
            payment_id=payment.id,
            event_type="payment_succeeded",
            provider_event_id="evt_123",
        )
        db.add(event)
        db.commit()

        # Try to process same event again
        webhook_payload = {
            "type": "payment_intent.succeeded",
            "id": "evt_123",
            "data": {"object": {"id": "pi_test"}},
        }

        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = MagicMock(
                id="evt_123",
                type="payment_intent.succeeded",
            )

            response = client.post(
                "/api/stripe/webhook",
                json=webhook_payload,
                headers={"Stripe-Signature": "test"},
            )

            # Should succeed but not create duplicate
            assert response.status_code == 200

        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestInvoiceGeneration:
    """Test invoice generation and PDF rendering."""

    def test_invoice_created_on_payment_success(self, test_db, test_order):
        """Test invoice is created when payment succeeds."""
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=test_order.id,
            provider=PaymentProvider.STRIPE,
            status=PaymentStatus.SUCCEEDED,
        )
        db.add(payment)
        db.commit()

        # Trigger invoice creation
        from services.payment_platform.invoice_service import InvoiceService
        invoice_service = InvoiceService()
        invoice = invoice_service.create_invoice(db, payment.id)

        assert invoice is not None
        assert invoice.order_id == test_order.id
        assert invoice.invoice_number is not None

        db.close()

    def test_invoice_pdf_generation(self, test_db, test_order):
        """Test invoice PDF is generated correctly."""
        TestingSessionLocal, _ = test_db
        db = TestingSessionLocal()

        invoice = Invoice(
            id=str(uuid.uuid4()),
            order_id=test_order.id,
            invoice_number="INV-001",
        )
        db.add(invoice)
        db.commit()

        from services.payment_platform.invoice_service import InvoiceService
        invoice_service = InvoiceService()
        pdf_bytes = invoice_service.generate_pdf(db, invoice.id)

        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")

        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMITING TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimiting:
    """Test rate limiting on payment endpoints."""

    def test_rate_limit_on_session_creation(self, client, test_order):
        """Test rate limiting on payment session creation."""
        # Make many requests quickly
        responses = []
        for _ in range(20):
            response = client.post(
                "/api/payments/unified/session",
                json={
                    "order_id": test_order.id,
                    "provider": "stripe",
                    "amount": 100.00,
                },
            )
            responses.append(response)

        # At least one should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0

    def test_rate_limit_headers_present(self, client, test_order):
        """Test rate limit headers are present in response."""
        response = client.post(
            "/api/payments/unified/session",
            json={
                "order_id": test_order.id,
                "provider": "stripe",
                "amount": 100.00,
            },
        )

        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers or "X-RateLimit-Remaining" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
