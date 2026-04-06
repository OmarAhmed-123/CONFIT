"""
GPU Production Module
=====================
This module contains GPU-accelerated inference components.

IMPORTANT: This module is NOT imported when INFERENCE_MODE=mock.
It should only be imported when GPU inference is enabled.

Import Safety:
    The main application should NOT import this module directly.
    Use the service factory instead:

    from services.inference import get_inference_service
    service = get_inference_service()  # Returns mock or GPU based on env
"""

# This file exists to mark the directory as a Python package.
# It intentionally has no imports to prevent accidental GPU dependency loading.

__all__ = []  # Empty - do not expose any GPU components by default
