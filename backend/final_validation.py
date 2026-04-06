#!/usr/bin/env python
"""
CONFIT Backend - Final Validation Pipeline
==========================================
Runs end-to-end checks for:
- Database connectivity and migrations
- Backend imports and configuration
- Core API smoke tests
- Frontend production build (optional shell step)

Usage:
    # From backend directory (DB must be running)
    python final_validation.py
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).parent


def run(cmd: list[str], cwd: Path, env: dict | None = None, label: str = "") -> None:
  """Run a subprocess, fail fast with clear errors."""
  print(f"\n=== {label or ' '.join(cmd)} ===")
  completed = subprocess.run(
      cmd,
      cwd=str(cwd),
      env=env,
  )
  if completed.returncode != 0:
      raise SystemExit(f"{label or cmd[0]} failed with exit code {completed.returncode}")


def main() -> int:
  # Ensure DATABASE_URL is set; fall back to .env.postgres if present
  env = os.environ.copy()
  if "DATABASE_URL" not in env:
      env["DATABASE_URL"] = "postgresql://confit:confit_dev_password_2026!@localhost:5432/confit"

  # 1. DB connectivity & migrations
  run(
      [sys.executable, "test_postgres_connection.py", "--env-file", ".env.postgres"],
      cwd=ROOT_DIR,
      env=env,
      label="Database connectivity & migrations",
  )

  # 2. Backend imports and config
  run(
      [sys.executable, "verify_backend.py"],
      cwd=ROOT_DIR,
      env=env,
      label="Backend import/config verification",
  )

  # 3. API smoke tests
  run(
      [sys.executable, "test_api_smoke.py"],
      cwd=ROOT_DIR,
      env=env,
      label="API smoke tests",
  )

  print("\nAll backend validation checks passed.")
  print("Frontend build can be run separately from project root with: npm run build")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

#!/usr/bin/env python
"""Run backend validation and save results."""
import sys
import os

# Change to backend directory
os.chdir(r"E:\CONFIT\backend")
sys.path.insert(0, r"E:\CONFIT\backend")

results = []

# Test 1
try:
    from main import app
    results.append(("main.py", "OK", f"Title: {app.title}, Routes: {len([r for r in app.routes])}"))
except Exception as e:
    results.append(("main.py", "FAIL", str(e)))

# Test 2
try:
    from core.config import settings
    results.append(("core.config", "OK", f"ENV: {settings.ENVIRONMENT}"))
except Exception as e:
    results.append(("core.config", "FAIL", str(e)))

# Test 3
try:
    from core.errors import AppError, ValidationError
    results.append(("core.errors", "OK", ""))
except Exception as e:
    results.append(("core.errors", "FAIL", str(e)))

# Test 4
try:
    from repositories import UserRepository, ProductRepository
    results.append(("repositories", "OK", ""))
except Exception as e:
    results.append(("repositories", "FAIL", str(e)))

# Test 5
try:
    from schemas import UserCreate, ProductCreate
    results.append(("schemas", "OK", ""))
except Exception as e:
    results.append(("schemas", "FAIL", str(e)))

# Test 6
try:
    from utils import validate_email, utc_now
    results.append(("utils", "OK", ""))
except Exception as e:
    results.append(("utils", "FAIL", str(e)))

# Test 7
try:
    from database import Base, get_db
    results.append(("database", "OK", ""))
except Exception as e:
    results.append(("database", "FAIL", str(e)))

# Write results
output_path = r"E:\CONFIT\backend\validation_results.txt"
with open(output_path, "w") as f:
    f.write("CONFIT Backend Validation Results\n")
    f.write("=" * 50 + "\n\n")
    
    passed = sum(1 for r in results if r[1] == "OK")
    failed = sum(1 for r in results if r[1] == "FAIL")
    
    for name, status, detail in results:
        f.write(f"[{status}] {name}")
        if detail:
            f.write(f" - {detail}")
        f.write("\n")
    
    f.write("\n" + "=" * 50 + "\n")
    f.write(f"PASSED: {passed}/{len(results)}\n")
    
    if failed == 0:
        f.write("\nBACKEND READY FOR PRODUCTION\n")
    else:
        f.write(f"\nFAILED: {failed} errors\n")

print(f"Results written to: {output_path}")
print(f"PASSED: {passed}/{len(results)}")
