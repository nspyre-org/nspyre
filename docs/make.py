import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main():
    if sys.platform == 'win32':
        # cmd = (f'make -C clean {HERE} && make -C {HERE} html',)
        cmd = ['make', '-C', str(HERE), 'clean']
        ret = subprocess.call(cmd)
        if ret:
            return ret
        cmd = ['make', '-C', str(HERE), 'html']
        return subprocess.call(cmd)
    else:
        cmd = (f'bash -c \'make -C {HERE} clean && make -C {HERE} html\'',)
        return subprocess.call(cmd)


if __name__ == '__main__':
    main()
