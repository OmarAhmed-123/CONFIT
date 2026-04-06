"""Unit test: Paymob HMAC verification."""

import hashlib
import hmac
import os

import pytest

from services.payment_platform.providers import paymob_provider as pm


def test_verify_callback_hmac_accepts_valid_signature(monkeypatch):
    secret = b"testsecret"
    monkeypatch.setenv("PAYMOB_HMAC_SECRET", secret.decode())
    obj = {
        "amount_cents": 1000,
        "created_at": "2024-01-01T00:00:00.000Z",
        "currency": "EGP",
        "error_occured": False,
        "has_parent_transaction": False,
        "id": 99,
        "integration_id": 1,
        "is_3d_secure": False,
        "is_auth": False,
        "is_capture": False,
        "is_refunded": False,
        "is_standalone_payment": True,
        "is_voided": False,
        "order": {"id": 555},
        "owner": 1,
        "pending": False,
        "source_data": {"pan": "1234", "sub_type": "Visa", "type": "card"},
        "success": True,
    }
    parts = [
        str(obj["amount_cents"]),
        str(obj["created_at"]),
        str(obj["currency"]),
        str(obj["error_occured"]).lower(),
        str(obj["has_parent_transaction"]).lower(),
        str(obj["id"]),
        str(obj["integration_id"]),
        str(obj["is_3d_secure"]).lower(),
        str(obj["is_auth"]).lower(),
        str(obj["is_capture"]).lower(),
        str(obj["is_refunded"]).lower(),
        str(obj["is_standalone_payment"]).lower(),
        str(obj["is_voided"]).lower(),
        str(obj["order"]["id"]),
        str(obj["owner"]),
        str(obj["pending"]).lower(),
        str(obj["source_data"]["pan"]),
        str(obj["source_data"]["sub_type"]),
        str(obj["source_data"]["type"]),
        str(obj["success"]).lower(),
    ]
    concat = "".join(parts)
    expected = hmac.new(secret, concat.encode("utf-8"), hashlib.sha512).hexdigest()
    assert pm.verify_callback_hmac(obj, expected) is True


def test_verify_rejects_bad_hmac(monkeypatch):
    monkeypatch.setenv("PAYMOB_HMAC_SECRET", "s")
    assert pm.verify_callback_hmac({"order": {"id": 1}}, "deadbeef") is False


def test_hmac_falls_back_to_secret_key(monkeypatch):
    """When PAYMOB_HMAC_SECRET is unset, PAYMOB_SECRET_KEY is used (Egypt accounts)."""
    monkeypatch.delenv("PAYMOB_HMAC_SECRET", raising=False)
    secret = b"fallback_sk"
    monkeypatch.setenv("PAYMOB_SECRET_KEY", secret.decode())
    obj = {
        "amount_cents": 100,
        "created_at": "x",
        "currency": "EGP",
        "error_occured": False,
        "has_parent_transaction": False,
        "id": 1,
        "integration_id": 1,
        "is_3d_secure": False,
        "is_auth": False,
        "is_capture": False,
        "is_refunded": False,
        "is_standalone_payment": True,
        "is_voided": False,
        "order": {"id": 2},
        "owner": 0,
        "pending": False,
        "source_data": {"pan": "", "sub_type": "", "type": ""},
        "success": True,
    }
    parts = [
        "100",
        "x",
        "EGP",
        "false",
        "false",
        "1",
        "1",
        "false",
        "false",
        "false",
        "false",
        "true",
        "false",
        "2",
        "0",
        "false",
        "",
        "",
        "",
        "true",
    ]
    concat = "".join(parts)
    expected = hmac.new(secret, concat.encode("utf-8"), hashlib.sha512).hexdigest()
    assert pm.verify_callback_hmac(obj, expected) is True
