import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main():
    if sys.platform == 'win32':
        cmd = (f'make -C clean {HERE} && make -C {HERE} html',)
        kwargs = {'shell': True}
    else:
        cmd = (f"bash -c 'make -C {HERE} clean && make -C {HERE} html'",)
        kwargs = {}
    return subprocess.call(cmd, **kwargs)


if __name__ == '__main__':
    main()
