import sys, os
sys.path.insert(0, '.')
os.environ['ENVIRONMENT'] = 'test'
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

from main import app
paths = [r.path for r in app.routes if hasattr(r, 'path')]
health = sorted([p for p in paths if 'health' in p])
metrics = sorted([p for p in paths if 'metrics' in p])

with open('_final_verify_results.txt', 'w') as f:
    f.write('HEALTH_ROUTES: ' + str(health) + '\n')
    f.write('METRICS_ROUTES: ' + str(metrics) + '\n')
    f.write('TOTAL_ROUTES: ' + str(len(paths)) + '\n')
    assert '/api/health' in paths
    assert '/api/health/ready' in paths
    assert '/api/health/deep' in paths
    assert '/api/metrics' in paths
    f.write('ALL_CHECKS_PASSED\n')
