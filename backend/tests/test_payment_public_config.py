"""Public payment config shape (storefront feature flags)."""

import pytest

from routers.payments import payment_public_config


@pytest.mark.asyncio
async def test_payment_public_config_keys():
    body = await payment_public_config()
    assert "stripe_enabled" in body
    assert "publishable_key" in body
    assert "paymob_enabled" in body
    assert "paymob_iframe_ready" in body
    assert "paypal_enabled" in body
    assert isinstance(body["stripe_enabled"], bool)
    assert isinstance(body["paymob_enabled"], bool)
