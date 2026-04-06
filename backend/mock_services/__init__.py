"""
CONFIT Mock Services
====================
Mock services for development without GPU.

These services simulate AI inference behavior for local development.
They are activated when INFERENCE_MODE=mock (default).
"""

from .mock_data_generator import (
    MockDataGenerator,
    MockGarment,
    MockTryOnResult,
)

__all__ = [
    'MockDataGenerator',
    'MockGarment',
    'MockTryOnResult',
]
