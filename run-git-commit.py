import os
import subprocess
import sys

os.chdir(r'E:\CONFIT')
print(f"Working directory: {os.getcwd()}")

# Run git status
result = subprocess.run(['git', 'status'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Add all changes
subprocess.run(['git', 'add', '-A'])

# Commit
result = subprocess.run(
    ['git', 'commit', '-m', 'Phase 8: Security hardening - rate limiting, auth, audit logging, CSRF, frontend integration'],
    capture_output=True, text=True
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Push
result = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
