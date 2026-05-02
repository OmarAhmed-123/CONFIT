import subprocess
import sys

def main():
    commands = [
        ['git', 'add', 'backend/routers/payment_platform.py'],
        ['git', 'commit', '-m', 'fix(integration): A.2 + A.3 — Add Valu eligibility and Fawry status endpoints'],
        ['git', 'add', 'backend/routers/payments.py'],
        ['git', 'commit', '-m', 'fix(integration): A.5 — Fix Payment Config schema with missing fields'],
        ['git', 'add', 'backend/routers/analytics_store.py', 'backend/routers/analytics.py'],
        ['git', 'commit', '-m', 'fix(integration): A.7 — Fix analytics endpoint authorization'],
        ['git', 'log', '--oneline', '-5']
    ]

    for cmd in commands:
        result = subprocess.run(cmd, cwd='e:\\CONFIT', capture_output=True, text=True)
        print(f"CMD: {' '.join(cmd)}")
        print(f"RC: {result.returncode}")
        if result.stdout:
            print(f"OUT: {result.stdout}")
        if result.stderr:
            print(f"ERR: {result.stderr}")
        print("-" * 40)

if __name__ == "__main__":
    main()
