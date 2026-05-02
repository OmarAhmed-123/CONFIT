import subprocess
import sys

def run_git(args):
    result = subprocess.run(
        ['git', '-C', 'e:\\CONFIT'] + args,
        capture_output=True,
        text=True,
        shell=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    return result.returncode

if __name__ == "__main__":
    import sys
    run_git(sys.argv[1:])
