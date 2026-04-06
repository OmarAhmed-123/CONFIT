"""
CONFIT Backend - Notification Template Engine
=============================================

Jinja2-based template engine for notification localization.
Supports English (en) and Arabic (ar) templates.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

logger = logging.getLogger(__name__)

# Template directory path
TEMPLATE_DIR = Path(__file__).parent / "templates"


class TemplateEngine:
    """
    Jinja2 template engine for notification content.
    
    Features:
    - Loads templates from filesystem
    - Supports multiple channels (push, email, whatsapp, sms)
    - RTL support for Arabic
    - Variable interpolation
    """
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._cache: Dict[str, Template] = {}
    
    def _get_template_path(
        self,
        trigger: str,
        channel: str,
        language: str,
        extension: str,
    ) -> str:
        """Get template path relative to template directory."""
        return f"{language}/{trigger}.{channel}.{extension}"
    
    def render_push(
        self,
        trigger: str,
        language: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Render push notification template.
        
        Args:
            trigger: Trigger type (e.g., 'order_placed')
            language: Language code ('en' or 'ar')
            variables: Template variables
            
        Returns:
            Dict with 'title', 'body', and 'data' keys
        """
        template_path = self._get_template_path(trigger, "push", language, "json")
        
        try:
            template = self._env.get_template(template_path)
            rendered = template.render(**variables)
            return json.loads(rendered)
        except Exception as e:
            logger.error(f"Failed to render push template {template_path}: {e}")
            # Fallback to basic message
            return {
                "title": trigger.replace("_", " ").title(),
                "body": f"Update on order #{variables.get('order_number', 'N/A')}",
                "data": variables,
            }
    
    def render_email(
        self,
        trigger: str,
        language: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render email HTML template.
        
        Args:
            trigger: Trigger type
            language: Language code
            variables: Template variables
            
        Returns:
            HTML string
        """
        template_path = self._get_template_path(trigger, "email", language, "html")
        
        try:
            template = self._env.get_template(template_path)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Failed to render email template {template_path}: {e}")
            # Fallback to basic HTML
            return f"""
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <h1>{trigger.replace('_', ' ').title()}</h1>
                    <p>Order #{variables.get('order_number', 'N/A')}</p>
                </body>
                </html>
            """
    
    def render_whatsapp(
        self,
        trigger: str,
        language: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render WhatsApp text template.
        
        Args:
            trigger: Trigger type
            language: Language code
            variables: Template variables
            
        Returns:
            Plain text string (WhatsApp-formatted)
        """
        template_path = self._get_template_path(trigger, "whatsapp", language, "txt")
        
        try:
            template = self._env.get_template(template_path)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Failed to render WhatsApp template {template_path}: {e}")
            # Fallback
            return f"*{trigger.replace('_', ' ').title()}*\n\nOrder #{variables.get('order_number', 'N/A')}"
    
    def render_sms(
        self,
        trigger: str,
        language: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render SMS text template.
        
        Note: Arabic SMS is limited to 70 characters per segment.
        
        Args:
            trigger: Trigger type
            language: Language code
            variables: Template variables
            
        Returns:
            Plain text string (truncated if necessary)
        """
        template_path = self._get_template_path(trigger, "sms", language, "txt")
        
        try:
            template = self._env.get_template(template_path)
            rendered = template.render(**variables)
            
            # Truncate for SMS limits
            # Arabic: 70 chars per segment
            # English: 160 chars per segment
            max_length = 70 if language == "ar" else 160
            if len(rendered) > max_length:
                logger.warning(f"SMS truncated from {len(rendered)} to {max_length} chars")
                rendered = rendered[:max_length - 3] + "..."
            
            return rendered
        except Exception as e:
            logger.error(f"Failed to render SMS template {template_path}: {e}")
            # Fallback
            return f"CONFIT: {trigger.replace('_', ' ')} - Order #{variables.get('order_number', 'N/A')}"
    
    def render(
        self,
        trigger: str,
        channel: str,
        language: str,
        variables: Dict[str, Any],
    ) -> Any:
        """
        Render template for any channel.
        
        Args:
            trigger: Trigger type
            channel: Channel type ('push', 'email', 'whatsapp', 'sms')
            language: Language code
            variables: Template variables
            
        Returns:
            Rendered content (type depends on channel)
        """
        if channel == "push":
            return self.render_push(trigger, language, variables)
        elif channel == "email":
            return self.render_email(trigger, language, variables)
        elif channel == "whatsapp":
            return self.render_whatsapp(trigger, language, variables)
        elif channel == "sms":
            return self.render_sms(trigger, language, variables)
        else:
            raise ValueError(f"Unknown channel: {channel}")


# Singleton instance
_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    """Get template engine singleton."""
    global _engine
    if _engine is None:
        _engine = TemplateEngine()
    return _engine


def render_notification(
    trigger: str,
    channel: str,
    language: str,
    variables: Dict[str, Any],
) -> Any:
    """
    Convenience function to render notification template.
    
    Args:
        trigger: Trigger type
        channel: Channel type
        language: Language code
        variables: Template variables
        
    Returns:
        Rendered content
    """
    engine = get_template_engine()
    return engine.render(trigger, channel, language, variables)


__all__ = [
    "TemplateEngine",
    "get_template_engine",
    "render_notification",
]
