"""
CONFIT Backend - SSRF Protection
=================================
Validates all outbound URLs to prevent Server-Side Request Forgery.
Blocks requests to localhost, internal IPs, and cloud metadata endpoints.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Blocked IP ranges (RFC 1918, loopback, link-local, cloud metadata)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),         # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),      # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),     # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / AWS metadata
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmark testing
    ipaddress.ip_network("224.0.0.0/4"),         # Multicast
    ipaddress.ip_network("240.0.0.0/4"),         # Reserved
    ipaddress.ip_network("::1/128"),             # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),           # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),            # IPv6 unique-local
    ipaddress.ip_network("ff00::/8"),            # IPv6 multicast
]

# Blocked hostnames (cloud metadata endpoints)
BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.google.internal.",
    "169.254.169.254",  # AWS/GCP metadata
    "100.100.100.200",  # Alibaba Cloud metadata
}

# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}


def is_url_safe(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a URL does not point to an internal or blocked destination.

    Returns:
        (is_safe, reason): True if safe, or False with a reason string.
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL: {e}"

    # Check scheme
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Scheme '{parsed.scheme}' not allowed (only http/https)"

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL"

    # Check blocked hostnames
    if hostname.lower() in BLOCKED_HOSTNAMES or hostname.lower().rstrip(".") in BLOCKED_HOSTNAMES:
        return False, f"Hostname '{hostname}' is a blocked metadata endpoint"

    # Check for localhost variations
    if hostname.lower() in ("localhost", "localhost.localdomain"):
        return False, "localhost is not allowed"

    # Resolve and check IP address
    try:
        import socket
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved_ips:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                for network in BLOCKED_NETWORKS:
                    if ip in network:
                        return False, f"Resolved IP {ip_str} is in blocked network {network}"
            except ValueError:
                continue
    except socket.gaierror:
        # DNS resolution failed — could be a typo or internal domain
        # Allow but log a warning
        logger.warning("ssrf_dns_resolve_failed hostname=%s", hostname)
    except Exception as e:
        logger.warning("ssrf_dns_check_error hostname=%s error=%s", hostname, e)

    return True, None


def validate_outbound_url(url: str) -> str:
    """
    Validate an outbound URL for SSRF safety.

    Args:
        url: The URL to validate

    Returns:
        The URL if safe

    Raises:
        ValueError: If the URL is not safe
    """
    is_safe, reason = is_url_safe(url)
    if not is_safe:
        raise ValueError(f"URL blocked by SSRF guard: {reason}")
    return url


__all__ = [
    "is_url_safe",
    "validate_outbound_url",
    "BLOCKED_NETWORKS",
    "BLOCKED_HOSTNAMES",
]
