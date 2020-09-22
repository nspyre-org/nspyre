#!/usr/bin/env python
"""
CLI for controlling mongodb

Author: Jacob Feder
Date: 9/13/2020
"""

###########################
# imports
###########################

# std
import argparse
from sys import platform
from pathlib import Path
import subprocess

###########################
# globals
###########################

THIS_DIR = Path(__file__).parent

###########################
# exceptions
###########################

class OSNotSupportedError(Exception):
    pass

###########################
# classes / functions
###########################

def main():
    """Entry point for mongodb CLI"""
    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='nspyre-mongodb',
                            description='Start / restart the MongoDB server')
    cmd_args = arg_parser.parse_args()
    if platform == 'linux' or platform == 'linux2' or platform == 'darwin':
        subprocess.run(['bash', str(THIS_DIR / 'start_mongo_unix.sh')])
    elif platform == 'win32':
        subprocess.run([str(THIS_DIR / 'start_mongo_win.bat')])
    else:
        raise OSNotSupportedError('Your OS [{}] is not supported'.\
                                    format(platform))

###########################
# standalone main
###########################

if __name__ == '__main__':
    main()
