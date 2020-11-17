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
from sys import platform, exit
from pathlib import Path
from subprocess import check_call, CalledProcessError

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
    try:
        if platform == 'linux' or platform == 'linux2' or platform == 'darwin':
            check_call(['bash', str(THIS_DIR / 'start_mongo_unix.sh')])
        elif platform == 'win32':
            check_call([str(THIS_DIR / 'start_mongo_win.bat')])
        else:
            raise OSNotSupportedError('Your OS [{}] is not supported'.\
                                        format(platform))
    except CalledProcessError:
        exit(1)
    
    exit(0)

###########################
# standalone main
###########################

if __name__ == '__main__':
    main()
