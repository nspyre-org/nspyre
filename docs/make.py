import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main():
    cmd = ['make', '-C', str(HERE), 'clean']
    ret = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    if ret.returncode:
        return ret.returncode
    print(ret.stdout, file=sys.stdout)
    print(ret.stderr, file=sys.stderr)
    cmd = ['make', '-C', str(HERE), 'html']
    ret = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    if ret.returncode:
        return ret.returncode
    print(ret.stdout, file=sys.stdout)
    print(ret.stderr, file=sys.stderr)


if __name__ == '__main__':
    main()
