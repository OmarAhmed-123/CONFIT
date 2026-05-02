import sys, os
sys.path.insert(0, '.')
os.environ['ENVIRONMENT'] = 'test'
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

from core.logging import configure_logging, get_logger, StructlogContextMiddleware
from core.observability.sentry import init_sentry
from core.observability.prometheus_metrics import confit_orders_total, get_metrics_text
from routers.health import router as health_router
from routers.metrics import router as metrics_router
from main import app

paths = [r.path for r in app.routes if hasattr(r, 'path')]
health = sorted([p for p in paths if 'health' in p])
metrics = sorted([p for p in paths if 'metrics' in p])
print('HEALTH ROUTES:', health)
print('METRICS ROUTES:', metrics)
assert '/api/health' in paths
assert '/api/health/ready' in paths
assert '/api/health/deep' in paths
assert '/api/metrics' in paths
print('ALL_CHECKS_PASSED')
