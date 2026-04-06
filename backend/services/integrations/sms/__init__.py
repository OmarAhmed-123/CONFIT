"""
CONFIT Backend - SMS Integration
================================
Provider-agnostic SMS client with adapter pattern.
Supports multiple Egyptian SMS providers.
"""

from services.integrations.sms.base import BaseSmsAdapter, SmsMessage, SmsResult
from services.integrations.sms_client import SmsClient, get_sms_client

__all__ = [
    "BaseSmsAdapter",
    "SmsMessage",
    "SmsResult",
    "SmsClient",
    "get_sms_client",
]
