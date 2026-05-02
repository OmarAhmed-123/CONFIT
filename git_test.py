import subprocess
import sys
import os

print("CWD:", os.getcwd())

# Test git status
result = subprocess.run(
    ['git', 'status', '--short'],
    cwd='e:\\CONFIT',
    capture_output=True,
    text=True
)
print("Git status RC:", result.returncode)
print("Git status OUT:", repr(result.stdout))
print("Git status ERR:", repr(result.stderr))
