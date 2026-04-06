"""
Isolated verification for the Try-On pipeline.
Patches out heavy ML imports (torch, mediapipe, cv2) to run fast.
"""
import sys, os, base64, time, asyncio

# ── Mock heavy ML modules BEFORE any imports ──────────────────────
class _MockModule:
    """Lightweight mock for heavy ML packages."""
    def __getattr__(self, name):
        return _MockModule()
    def __call__(self, *a, **kw):
        return _MockModule()
    def __bool__(self):
        return False

for mod in ['torch', 'torch.cuda', 'torch.backends', 'torch.backends.mps',
            'torchvision', 'mediapipe', 'cv2', 'scipy', 'scipy.ndimage',
            'transformers', 'accelerate', 'gradio_client',
            'sentence_transformers', 'sklearn', 'qdrant_client', 'faiss']:
    if mod not in sys.modules:
        sys.modules[mod] = _MockModule()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0

def check(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  PASS  {name}")
        passed += 1
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        failed += 1

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ═══════════════════════════════════════════════════════════════════
# CACHE LAYER
# ═══════════════════════════════════════════════════════════════════
def t_cache_import():
    from services.mcp.cache_layer import TryOnCache
    assert TryOnCache is not None

def t_cache_hash_image():
    from services.mcp.cache_layer import TryOnCache
    h = TryOnCache.hash_image("abcdef" * 100)
    assert isinstance(h, str) and len(h) == 16

def t_cache_hash_options():
    from services.mcp.cache_layer import TryOnCache
    h1 = TryOnCache.hash_options({"a": 1})
    h2 = TryOnCache.hash_options({"b": 2})
    assert h1 != h2
    assert TryOnCache.hash_options(None) == "default"

def t_cache_key():
    from services.mcp.cache_layer import TryOnCache
    k = TryOnCache.make_result_key("ih", "gid", "oh")
    assert k.startswith("tryon:result:")

def t_cache_set_get():
    from services.mcp.cache_layer import TryOnCache
    c = TryOnCache()
    async def go():
        await c.set_result("k1", "val1", ttl=60)
        r = await c.get_result("k1")
        assert r == "val1"
    run_async(go())

def t_cache_miss():
    from services.mcp.cache_layer import TryOnCache
    c = TryOnCache()
    async def go():
        r = await c.get_result("nonexistent")
        assert r is None
    run_async(go())

def t_cache_garment():
    from services.mcp.cache_layer import TryOnCache
    c = TryOnCache()
    async def go():
        await c.set_garment("g1", b"garment_data", ttl=60)
        r = await c.get_garment("g1")
        assert r == b"garment_data"
    run_async(go())

def t_cache_stats():
    from services.mcp.cache_layer import TryOnCache
    s = TryOnCache().stats()
    assert s["backend"] == "memory"

def t_cache_hit_rate():
    from services.mcp.cache_layer import TryOnCache
    c = TryOnCache()
    async def go():
        await c.set_result("hr", "v", ttl=60)
        await c.get_result("hr")   # hit
        await c.get_result("xx")   # miss
        assert 0.4 < c.hit_rate < 0.6
    run_async(go())

# ═══════════════════════════════════════════════════════════════════
# GPU SCHEDULER
# ═══════════════════════════════════════════════════════════════════
def t_scheduler_import():
    from services.mcp.gpu_scheduler import GPUScheduler, Priority
    s = GPUScheduler()
    assert s.device in ("cpu", "cuda", "mps")

def t_scheduler_accept():
    from services.mcp.gpu_scheduler import GPUScheduler
    s = GPUScheduler(max_queue_size=5)
    assert s.can_accept_job()

def t_scheduler_sync():
    from services.mcp.gpu_scheduler import GPUScheduler
    s = GPUScheduler()
    r = run_async(s.submit("j1", lambda x: x * 7, args=(6,)))
    assert r == 42

def t_scheduler_async():
    from services.mcp.gpu_scheduler import GPUScheduler
    async def dbl(x): return x * 2
    s = GPUScheduler()
    r = run_async(s.submit("j2", dbl, args=(21,)))
    assert r == 42

def t_scheduler_error():
    from services.mcp.gpu_scheduler import GPUScheduler
    def boom(): raise ValueError("boom")
    s = GPUScheduler()
    try:
        run_async(s.submit("j3", boom))
        assert False, "Should have raised"
    except ValueError:
        pass

def t_scheduler_stats():
    from services.mcp.gpu_scheduler import GPUScheduler
    s = GPUScheduler().stats()
    assert "device" in s and "total_processed" in s

# ═══════════════════════════════════════════════════════════════════
# MODEL ROUTER
# ═══════════════════════════════════════════════════════════════════
def t_router_import():
    from services.mcp.model_router import ModelRouter, ModelBackend
    r = ModelRouter()
    assert r.is_available(ModelBackend.LOCAL)

def t_router_fast():
    from services.mcp.model_router import ModelRouter, ModelBackend
    assert ModelRouter().select(quality="fast") == ModelBackend.LOCAL

def t_router_mark():
    from services.mcp.model_router import ModelRouter, ModelBackend
    r = ModelRouter()
    r.mark_unavailable(ModelBackend.ADVANCED)
    assert not r.is_available(ModelBackend.ADVANCED)
    r.mark_available(ModelBackend.ADVANCED)
    assert r.is_available(ModelBackend.ADVANCED)

def t_router_backends():
    from services.mcp.model_router import ModelRouter
    b = ModelRouter().available_backends()
    assert isinstance(b, list) and len(b) >= 1

def t_router_stats():
    from services.mcp.model_router import ModelRouter
    s = ModelRouter().stats()
    assert "available_backends" in s

# ═══════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════
def t_category_tops():
    from services.mcp.orchestrator import detect_garment_category
    assert detect_garment_category("Classic T-Shirt") == "tops"

def t_category_bottoms():
    from services.mcp.orchestrator import detect_garment_category
    assert detect_garment_category("Slim Fit Jeans") == "bottoms"

def t_category_dresses():
    from services.mcp.orchestrator import detect_garment_category
    assert detect_garment_category("Evening Gown") == "dresses"

def t_category_outerwear():
    from services.mcp.orchestrator import detect_garment_category
    assert detect_garment_category("Leather Jacket") == "outerwear"

def t_category_shoes():
    from services.mcp.orchestrator import detect_garment_category
    assert detect_garment_category("Running Sneakers") == "shoes"

def t_category_accessories():
    from services.mcp.orchestrator import detect_garment_category
    assert detect_garment_category("Gold Necklace") == "accessories"

def t_category_default():
    from services.mcp.orchestrator import detect_garment_category
    assert detect_garment_category("Unknown Item") == "tops"

def t_orch_empty_image():
    from services.mcp.orchestrator import TryOnOrchestrator
    TryOnOrchestrator._instance = None
    o = TryOnOrchestrator()
    r = run_async(o.process("", "https://x.com/g.jpg", "Shirt"))
    assert not r.success
    assert "Invalid" in (r.error_message or "")

def t_orch_bad_url():
    from services.mcp.orchestrator import TryOnOrchestrator
    TryOnOrchestrator._instance = None
    o = TryOnOrchestrator()
    r = run_async(o.process("a" * 200, "not-a-url", "Shirt"))
    assert not r.success
    assert "URL" in (r.error_message or "")

# ═══════════════════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════════════════
def t_pipeline_singleton():
    from services.mcp.pipeline import ModelControlPipeline
    ModelControlPipeline._instance = None
    p1 = ModelControlPipeline.get_instance()
    p2 = ModelControlPipeline.get_instance()
    assert p1 is p2

def t_pipeline_stats():
    from services.mcp.pipeline import ModelControlPipeline
    s = ModelControlPipeline.get_instance().stats()
    assert "router" in s and "cache" in s and "scheduler" in s

# ═══════════════════════════════════════════════════════════════════
# LIVE PREVIEW
# ═══════════════════════════════════════════════════════════════════
def t_preview_import():
    from services.live_preview import LivePreviewManager
    m = LivePreviewManager()
    assert m.active_sessions() == 0

def t_preview_stats():
    from services.live_preview import LivePreviewManager
    s = LivePreviewManager().stats()
    assert s["active_sessions"] == 0

# ═══════════════════════════════════════════════════════════════════
# SECURITY
# ═══════════════════════════════════════════════════════════════════
def t_sec_validate_empty():
    from middleware.tryon_security import validate_upload_image
    ok, _ = validate_upload_image("")
    assert not ok

def t_sec_validate_jpeg():
    from middleware.tryon_security import validate_upload_image
    d = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 200).decode()
    ok, _ = validate_upload_image(d)
    assert ok

def t_sec_validate_png():
    from middleware.tryon_security import validate_upload_image
    d = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200).decode()
    ok, _ = validate_upload_image(d)
    assert ok

def t_sec_validate_injection():
    from middleware.tryon_security import validate_upload_image
    d = base64.b64encode(b"\xff\xd8\xff\xe0<script>" + b"\x00" * 200).decode()
    ok, _ = validate_upload_image(d)
    assert not ok

def t_sec_data_url():
    from middleware.tryon_security import validate_upload_image
    d = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 200).decode()
    ok, _ = validate_upload_image(d)
    assert ok

def t_sec_bad_mime():
    from middleware.tryon_security import validate_upload_image
    d = "data:text/html;base64," + base64.b64encode(b"\x00" * 200).decode()
    ok, _ = validate_upload_image(d)
    assert not ok

def t_sec_signed_url():
    from middleware.tryon_security import generate_signed_url, verify_signed_url
    url = generate_signed_url("r123", 3600)
    parts = url.split("?")[1].split("&")
    params = dict(p.split("=") for p in parts)
    assert verify_signed_url("r123", int(params["expires"]), params["sig"])

def t_sec_expired():
    from middleware.tryon_security import verify_signed_url
    assert not verify_signed_url("r", int(time.time()) - 100, "bad")

def t_sec_cleanup():
    from middleware.tryon_security import ImageCleanupTracker
    t = ImageCleanupTracker()
    t.register("/tmp/__nonexistent__.jpg", ttl=0)
    t.cleanup_expired()  # file doesn't exist, just clears tracking

# ═══════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  CONFIT Try-On Pipeline — Full Verification")
    print("=" * 60)

    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("t_") and callable(v)]
    for name, fn in tests:
        check(name, fn)

    print("=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
