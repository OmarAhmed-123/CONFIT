"""
CONFIT Backend — Native Log Suppression
=========================================
MediaPipe/TensorFlow/absl logs are emitted from native code (C++) and often go
directly to OS-level stderr/stdout file descriptors.

This helper temporarily redirects the underlying file descriptors to
`os.devnull` so noisy `W0000 ...` messages don't spam our logs.
"""

from __future__ import annotations

import contextlib
import os
from typing import Iterator


@contextlib.contextmanager
def suppress_native_output() -> Iterator[None]:
    # Duplicate current stdout/stderr FDs, then redirect both to devnull.
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    old_stdout_fd = os.dup(1)
    old_stderr_fd = os.dup(2)
    try:
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(old_stdout_fd, 1)
        os.dup2(old_stderr_fd, 2)
        os.close(devnull_fd)
        os.close(old_stdout_fd)
        os.close(old_stderr_fd)

