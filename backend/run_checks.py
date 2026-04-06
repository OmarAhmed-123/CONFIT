"""Run security checks and save output to file."""
import subprocess
import sys
import os

VENV = r"e:\CONFIT\backend\venv\Scripts"
PIP = os.path.join(VENV, "pip.exe")
PY = os.path.join(VENV, "python.exe")
OUTFILE = r"e:\CONFIT\backend\security_check_output.txt"

def run(cmd, label):
    """Run command and capture output."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300,
        env={**os.environ, "PYTHONPATH": r"e:\CONFIT\backend"},
    )
    return f"\n{'='*60}\n{label}\n{'='*60}\nCMD: {' '.join(cmd)}\nRC: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"

with open(OUTFILE, "w", encoding="utf-8") as f:
    # Step 1: Install dependencies
    f.write(run([PIP, "install", "pytest", "pytest-asyncio", "bandit", "safety",
                  "argon2-cffi", "pyotp", "qrcode", "bleach", "slowapi", "httpx",
                  "bcrypt", "cryptography", "passlib", "python-jose"], "STEP 1: Install Dependencies"))

    # Step 2: Check installed
    f.write(run([PIP, "list"], "STEP 2: Installed Packages"))

    # Step 3: Run security tests
    f.write(run([PY, "-m", "pytest", r"e:\CONFIT\backend\tests\test_security_hardening.py",
                  "-v", "--tb=short"], "STEP 3: Security Tests"))

    # Step 4: Run bandit
    bandit_exe = os.path.join(VENV, "bandit.exe")
    if os.path.exists(bandit_exe):
        f.write(run([bandit_exe, "-r", r"e:\CONFIT\backend", "-f", "txt", "-ll", "-ii",
                      "--exclude", r"e:\CONFIT\backend\venv,e:\CONFIT\backend\tests"],
                     "STEP 4: Bandit Scan"))
    else:
        f.write(run([PY, "-m", "bandit", "-r", r"e:\CONFIT\backend", "-f", "txt", "-ll", "-ii",
                      "--exclude", r"e:\CONFIT\backend\venv,e:\CONFIT\backend\tests"],
                     "STEP 4: Bandit Scan"))

    # Step 5: Run safety
    safety_exe = os.path.join(VENV, "safety.exe")
    if os.path.exists(safety_exe):
        f.write(run([safety_exe, "check", "--json"], "STEP 5: Safety Check"))
    else:
        f.write(run([PY, "-m", "safety", "check", "--json"], "STEP 5: Safety Check"))

    f.write("\n\nALL CHECKS COMPLETE\n")

print(f"Output written to {OUTFILE}")
