import os

from services.tryon_runtime.capability_registry import CapabilityRegistry


def test_backend_priority_contains_preview_only():
    reg = CapabilityRegistry()
    snap = reg.snapshot().to_dict()
    assert "preview_only" in snap["backend_priority"]


def test_final_unavailable_without_gpu_and_remote(monkeypatch):
    monkeypatch.delenv("TRYON_REMOTE_URL", raising=False)
    reg = CapabilityRegistry()
    snap = reg.snapshot().to_dict()
    # In CPU-only CI this should be false; if GPU exists this may be true.
    if not snap["details"].get("cuda_available"):
        assert snap["final_render_available"] is False
        assert snap["active_backend"] == "preview_only"


def test_remote_health_detection(monkeypatch):
    monkeypatch.setenv("TRYON_REMOTE_URL", "http://127.0.0.1:9/render")
    reg = CapabilityRegistry()
    snap = reg.snapshot().to_dict()
    assert isinstance(snap["details"]["health"], dict)

