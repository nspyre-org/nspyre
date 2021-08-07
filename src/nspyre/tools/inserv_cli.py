#!/usr/bin/env python
"""
This module serves a shell prompt allowing the user runtime control of
the instrument server.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import argparse
import cmd
import logging
import pdb
import signal
from pathlib import Path

from nspyre import InstrumentGateway
from nspyre import InstrumentGatewayError
from nspyre import InstrumentServer
from nspyre import InstrumentServerError
from nspyre import nspyre_init_logger
from nspyre.misc.logging import LOG_FILE_MAX_SIZE

logger = logging.getLogger(__name__)


class InservCmdPrompt(cmd.Cmd):
    """Instrument Server shell prompt processor"""

    def __init__(self, inserv):
        super().__init__()
        self.inserv = inserv

    def emptyline(self):
        """When no command is entered"""
        pass

    def do_list(self, arg_string):
        """List all the available devices"""
        if arg_string:
            print('Expected 0 args')
            return
        for d in self.inserv.devs.keys():
            print(d)

    def do_del(self, arg_string):
        """Delete a device\narg 1: <string> the device name"""
        args = arg_string.split(' ')
        if not arg_string or len(args) > 1:
            print('Expected 1 arg: device name')
            return
        dev_name = args[0]
        try:
            self.inserv.remove(dev_name)
        except Exception as exc:
            logger.exception(exc)
            print(f'Failed to delete device [{dev_name}]')
            return

    def do_restart_device(self, arg_string):
        """Restart a device\narg 1: <string> the device name"""
        args = arg_string.split(' ')
        if not arg_string or len(args) > 1:
            print('Expected 1 arg: device name')
            return
        dev_name = args[0]
        try:
            self.inserv.restart(dev_name)
        except Exception as exc:
            logger.exception(exc)
            print(f'Failed to reload device [{dev_name}]')
            return

    def do_restart(self, arg_string):
        """Restart all devices"""
        if arg_string:
            print('Expected 0 args')
            return
        try:
            self.inserv.restart_all()
        except Exception as exc:
            logger.exception(exc)
            print('Failed to reload all devices')
            return

    def do_debug(self, arg_string):
        """Drop into the pdb debugging console"""
        if arg_string:
            print('Expected 0 args')
            return
        pdb.set_trace()

    def do_quit(self, arg_string):
        """Quit the program"""
        if arg_string:
            print('Expected 0 args')
            return
        logger.info('exiting...')

        if isinstance(self.inserv, InstrumentServer):
            # if the instrument server is local, stop it
            self.inserv.stop()

        raise SystemExit


def main():
    """Entry point for instrument server CLI"""

    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(
        prog='nspyre-inserv', description='Start an nspyre instrument server'
    )
    arg_parser.add_argument(
        '-l',
        '--log',
        default=None,
        help='log to the provided file / directory',
    )
    arg_parser.add_argument(
        '-p',
        '--port',
        default=None,
        type=int,
        help='port to start the server on',
    )
    arg_parser.add_argument(
        '-q', '--quiet', action='store_true', help='disable logging'
    )
    arg_parser.add_argument(
        '-s',
        '--start',
        action='store_true',
        help='start the instrument server without trying to connect',
    )
    arg_parser.add_argument(
        '-v',
        '--verbosity',
        default='info',
        help='the verbosity of logging to stdout - options are: '
        'debug, info, warning, error',
    )
    cmd_args = arg_parser.parse_args()

    # configure server logging behavior
    if not cmd_args.quiet:
        if cmd_args.verbosity.lower() == 'debug':
            log_level = logging.DEBUG
        elif cmd_args.verbosity.lower() == 'info':
            log_level = logging.INFO
        elif cmd_args.verbosity.lower() == 'warning':
            log_level = logging.WARNING
        elif cmd_args.verbosity.lower() == 'error':
            log_level = logging.ERROR
        else:
            raise InstrumentServerError(
                'didn\'t recognize logging level [{}]'.format(cmd_args.verbosity)
            )

        if cmd_args.log:
            nspyre_init_logger(
                log_level,
                log_path=Path(cmd_args.log),
                log_path_level=logging.DEBUG,
                prefix='inserv',
                file_size=LOG_FILE_MAX_SIZE,
            )
        else:
            # the user asked for no log file
            nspyre_init_logger(log_level)

    # whether a new instrument server should be started
    new_server = False
    if not cmd_args.start:
        # try connecting to a running instrument server
        try:
            if cmd_args.port:
                inserv = InstrumentGateway(port=cmd_args.port)
                inserv.connect()
            else:
                inserv = InstrumentGateway()
                inserv.connect()
        except InstrumentGatewayError as exc:
            logger.exception(exc)
            answer = input(
                'Failed connecting to the Instrument Server. Create one? [Y/n] '
            )
            if answer in ['y', 'Y', '']:
                new_server = True
            else:
                logger.info('exiting...')
                return
    else:
        new_server = True

    if new_server:
        # start a new instrument server
        if cmd_args.port:
            inserv = InstrumentServer(port=cmd_args.port)
            inserv.start()
        else:
            inserv = InstrumentServer()
            inserv.start()

        # properly stop the server when a kill signal is received
        def stop_server(signum, frame):
            inserv.stop()
            raise SystemExit

        signal.signal(signal.SIGINT, stop_server)
        signal.signal(signal.SIGTERM, stop_server)

    # start the shell prompt event loop
    cmd_prompt = InservCmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    cmd_prompt.cmdloop('')


if __name__ == '__main__':
    main()
