"""
CONFIT Backend - SMS Adapter Base
================================
Abstract base class for SMS provider adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SmsStatus(str, Enum):
    """SMS delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class SmsMessage:
    """
    SMS message payload.
    
    Supports Arabic text (UCS-2 encoding, 70-char limit per SMS).
    """
    to: str  # Phone number with country code
    body: str  # Message text
    sender_id: Optional[str] = None  # Sender ID (alpha or numeric)
    reference_id: Optional[str] = None  # For delivery tracking
    scheduled_at: Optional[datetime] = None  # For scheduled delivery
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_arabic(self) -> bool:
        """Check if message contains Arabic characters."""
        arabic_range = range(0x0600, 0x06FF + 1)
        return any(ord(c) in arabic_range for c in self.body)
    
    @property
    def segment_count(self) -> int:
        """
        Calculate SMS segment count.
        - GSM-7: 160 chars per segment (153 for multi-segment)
        - UCS-2 (Arabic): 70 chars per segment (67 for multi-segment)
        """
        if self.is_arabic:
            # UCS-2 encoding for Arabic
            char_limit = 70
            multi_limit = 67
        else:
            # GSM-7 encoding
            char_limit = 160
            multi_limit = 153
        
        length = len(self.body)
        if length <= char_limit:
            return 1
        return (length + multi_limit - 1) // multi_limit


@dataclass
class SmsResult:
    """SMS send result."""
    success: bool
    message_id: Optional[str] = None
    status: SmsStatus = SmsStatus.PENDING
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    segments: int = 1
    cost: Optional[float] = None
    currency: str = "USD"
    provider_response: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseSmsAdapter(ABC):
    """
    Abstract base class for SMS provider adapters.
    
    Each adapter implements provider-specific API calls while
    conforming to the common interface.
    
    Egypt-specific considerations:
    - Support Arabic text (UCS-2 encoding)
    - Handle local phone number formats
    - Track costs in EGP or USD
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name for logging and errors."""
        pass
    
    @abstractmethod
    async def send(self, message: SmsMessage) -> SmsResult:
        """
        Send a single SMS message.
        
        Args:
            message: SMS message payload
            
        Returns:
            SmsResult with delivery status
        """
        pass
    
    @abstractmethod
    async def send_batch(self, messages: List[SmsMessage]) -> List[SmsResult]:
        """
        Send multiple SMS messages.
        
        Args:
            messages: List of SMS messages
            
        Returns:
            List of SmsResult for each message
        """
        pass
    
    @abstractmethod
    async def get_delivery_status(self, message_id: str) -> SmsStatus:
        """
        Get delivery status for a sent message.
        
        Args:
            message_id: Message ID from send response
            
        Returns:
            Current delivery status
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy and credentials valid."""
        pass
    
    def format_phone(self, phone: str) -> str:
        """
        Format phone number for provider.
        
        Handles Egyptian formats:
        - 01xxxxxxxxx -> +201xxxxxxxxx
        - 201xxxxxxxxx -> +201xxxxxxxxx
        """
        # Remove spaces and dashes
        phone = phone.replace(" ", "").replace("-", "")
        
        # Already has country code
        if phone.startswith("+"):
            return phone
        
        # Has 00 prefix
        if phone.startswith("00"):
            return "+" + phone[2:]
        
        # Egyptian local format (0xxxxxxxxxxx)
        if phone.startswith("0"):
            return "+20" + phone[1:]
        
        # Assume Egyptian number without prefix
        return "+20" + phone
    
    def validate_for_egypt(self, phone: str) -> bool:
        """Validate Egyptian phone number format."""
        formatted = self.format_phone(phone)
        # Egyptian mobile: +201[0-2]xxxxxxxx (11 digits after +20)
        if formatted.startswith("+20"):
            return len(formatted) == 13 and formatted[4] in "012"
        return False
