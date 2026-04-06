"""
CONFIT Backend - Firebase Cloud Messaging (FCM) Client
======================================================
Push notification integration using Firebase Admin SDK.
Works in Egypt without restrictions.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.integrations.base import BaseIntegration, IntegrationError

logger = logging.getLogger(__name__)

# Lazy import firebase_admin to avoid import errors if not installed
_firebase_app = None


def _get_firebase_app():
    """Get or initialize Firebase app lazily."""
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        # Check if already initialized
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app
        
        # Load credentials from path
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        
        if not cred_path:
            raise IntegrationError(
                "FIREBASE_CREDENTIALS_PATH not configured",
                provider="firebase",
            )
        
        if not os.path.exists(cred_path):
            raise IntegrationError(
                f"Firebase credentials file not found: {cred_path}",
                provider="firebase",
            )
        
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred, {
            "projectId": project_id,
        })
        
        logger.info(f"Firebase app initialized for project: {project_id}")
        return _firebase_app
        
    except ImportError:
        raise IntegrationError(
            "firebase-admin package not installed. Run: pip install firebase-admin",
            provider="firebase",
        )


class FirebaseClient(BaseIntegration):
    """
    Firebase Cloud Messaging client for push notifications.
    
    Features:
    - Send to individual device tokens
    - Send to topics (for broadcast notifications)
    - Multicast to multiple devices
    - Support for Arabic text (UTF-8)
    
    Configuration:
        FIREBASE_PROJECT_ID=your-project-id
        FIREBASE_CREDENTIALS_PATH=./secrets/firebase-service-account.json
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ):
        super().__init__(
            provider="firebase",
            timeout_seconds=timeout_seconds,
            max_retries=3,
        )
        self.project_id = project_id or os.getenv("FIREBASE_PROJECT_ID")
        self.credentials_path = credentials_path or os.getenv("FIREBASE_CREDENTIALS_PATH")
        self._messaging = None
    
    def _get_messaging(self):
        """Get Firebase messaging module lazily."""
        if self._messaging is None:
            app = _get_firebase_app()
            from firebase_admin import messaging
            self._messaging = messaging
        return self._messaging
    
    async def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """
        Send push notification to a single device token.
        
        Args:
            token: FCM device token
            title: Notification title
            body: Notification body text
            data: Optional data payload (key-value strings)
            image_url: Optional image URL for rich notification
            
        Returns:
            Message ID string
            
        Raises:
            IntegrationError: On send failure
        """
        messaging = self._get_messaging()
        
        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )
            
            # Build message
            message = messaging.Message(
                token=token,
                notification=notification,
                data=data or {},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        title=title,
                        body=body,
                        image=image_url,
                        default_sound=True,
                        default_vibrate=True,
                        default_light_settings=True,
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body,
                            ),
                            sound="default",
                            badge=1,
                        ),
                    ),
                ),
            )
            
            # Send (firebase-admin is sync, run in executor)
            import asyncio
            loop = asyncio.get_event_loop()
            message_id = await loop.run_in_executor(
                None,
                lambda: messaging.send(message),
            )
            
            logger.info(
                f"[firebase] Sent notification to token {token[:16]}... "
                f"(message_id: {message_id})"
            )
            
            return message_id
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for specific errors
            if "registration-token-not-registered" in error_msg.lower():
                logger.warning(f"[firebase] Token not registered: {token[:16]}...")
                raise IntegrationError(
                    "Device token not registered",
                    provider="firebase",
                    response_data={"token": token, "error": "unregistered"},
                    original_error=e,
                )
            
            raise IntegrationError(
                f"Failed to send FCM message: {error_msg}",
                provider="firebase",
                original_error=e,
            )
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """
        Send push notification to a topic (broadcast to subscribers).
        
        Args:
            topic: Topic name (e.g., "orders", "promotions")
            title: Notification title
            body: Notification body text
            data: Optional data payload
            image_url: Optional image URL
            
        Returns:
            Message ID string
        """
        messaging = self._get_messaging()
        
        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )
            
            message = messaging.Message(
                topic=topic,
                notification=notification,
                data=data or {},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        title=title,
                        body=body,
                        image=image_url,
                    ),
                ),
            )
            
            import asyncio
            loop = asyncio.get_event_loop()
            message_id = await loop.run_in_executor(
                None,
                lambda: messaging.send(message),
            )
            
            logger.info(
                f"[firebase] Sent notification to topic '{topic}' "
                f"(message_id: {message_id})"
            )
            
            return message_id
            
        except Exception as e:
            raise IntegrationError(
                f"Failed to send to topic: {e}",
                provider="firebase",
                original_error=e,
            )
    
    async def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple devices.
        
        Args:
            tokens: List of FCM device tokens (max 500)
            title: Notification title
            body: Notification body text
            data: Optional data payload
            image_url: Optional image URL
            
        Returns:
            Dict with 'success_count', 'failure_count', 'responses'
        """
        messaging = self._get_messaging()
        
        if len(tokens) > 500:
            raise IntegrationError(
                "Multicast supports maximum 500 tokens",
                provider="firebase",
            )
        
        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )
            
            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=notification,
                data=data or {},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        title=title,
                        body=body,
                        image=image_url,
                    ),
                ),
            )
            
            import asyncio
            loop = asyncio.get_event_loop()
            batch_response = await loop.run_in_executor(
                None,
                lambda: messaging.send_multicast(message),
            )
            
            # Build response
            responses = []
            for i, resp in enumerate(batch_response.responses):
                responses.append({
                    "token": tokens[i][:16] + "...",
                    "success": resp.success,
                    "message_id": resp.message_id if resp.success else None,
                    "error": str(resp.exception) if resp.exception else None,
                })
            
            result = {
                "success_count": batch_response.success_count,
                "failure_count": batch_response.failure_count,
                "responses": responses,
            }
            
            logger.info(
                f"[firebase] Multicast sent: {batch_response.success_count} success, "
                f"{batch_response.failure_count} failed"
            )
            
            return result
            
        except Exception as e:
            raise IntegrationError(
                f"Failed to send multicast: {e}",
                provider="firebase",
                original_error=e,
            )
    
    async def subscribe_to_topic(
        self,
        tokens: List[str],
        topic: str,
    ) -> bool:
        """
        Subscribe device tokens to a topic.
        
        Args:
            tokens: List of FCM device tokens
            topic: Topic name to subscribe to
            
        Returns:
            True if successful
        """
        messaging = self._get_messaging()
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: messaging.subscribe_to_topic(tokens, topic),
            )
            
            if response.failure_count > 0:
                logger.warning(
                    f"[firebase] Subscribe to '{topic}': {response.success_count} success, "
                    f"{response.failure_count} failed"
                )
            
            return response.failure_count == 0
            
        except Exception as e:
            raise IntegrationError(
                f"Failed to subscribe to topic: {e}",
                provider="firebase",
                original_error=e,
            )
    
    async def unsubscribe_from_topic(
        self,
        tokens: List[str],
        topic: str,
    ) -> bool:
        """Unsubscribe device tokens from a topic."""
        messaging = self._get_messaging()
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: messaging.unsubscribe_from_topic(tokens, topic),
            )
            
            return response.failure_count == 0
            
        except Exception as e:
            raise IntegrationError(
                f"Failed to unsubscribe from topic: {e}",
                provider="firebase",
                original_error=e,
            )
    
    async def health_check(self) -> bool:
        """Check if Firebase is properly configured."""
        try:
            app = _get_firebase_app()
            return app is not None
        except Exception as e:
            logger.error(f"[firebase] Health check failed: {e}")
            return False


# Singleton instance
_firebase_client: Optional[FirebaseClient] = None


def get_firebase_client() -> FirebaseClient:
    """Get Firebase client singleton."""
    global _firebase_client
    if _firebase_client is None:
        _firebase_client = FirebaseClient()
    return _firebase_client
