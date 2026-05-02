import os
import subprocess
import sys

# Change to backend directory
os.chdir(r'E:\CONFIT\backend')

# Run pytest on security tests
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/test_security_hardening.py', '-v', '--tb=short'],
    capture_output=True, text=True
)

# Write output to file for inspection
with open(r'E:\CONFIT\pytest-output.txt', 'w') as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\nExit code: {result.returncode}\n")

print(f"Test run complete. Exit code: {result.returncode}")
