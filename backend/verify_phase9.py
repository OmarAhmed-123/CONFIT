import sys, os
sys.path.insert(0, '.')
os.environ['ENVIRONMENT'] = 'test'
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

from main import app
paths = [r.path for r in app.routes if hasattr(r, 'path')]
health = [p for p in paths if 'health' in p]
metrics = [p for p in paths if 'metrics' in p]
print('HEALTH ROUTES:', sorted(health))
print('METRICS ROUTES:', sorted(metrics))

assert '/api/health' in paths
assert '/api/health/ready' in paths
assert '/api/health/deep' in paths
assert '/api/metrics' in paths
print('ALL_PHASE_9_CHECKS_PASSED')
