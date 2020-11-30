"""
A CLI for the DataServer

Author: Jacob Feder
Date: 11/28/2020
"""

import argparse
from cmd import Cmd
import pdb
import logging

from nspyre.dataserv import DataServer
from nspyre.definitions import DATASERV_PORT

logger = logging.getLogger(__name__)

class DataservCmdPrompt(Cmd):
    """Data Server shell prompt processor"""
    def __init__(self, dataserv):
        super().__init__()
        self.dataserv = dataserv

    def emptyline(self):
        """When no command is entered"""
        pass

    def do_list(self, arg_string):
        """List all the available DataSets"""
        if arg_string:
            print('Expected 0 args')
            return
        for d in self.dataserv.datasets.keys():
            print(d)

    def do_debug(self, arg_string):
        """Drop into the debugging console"""
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
        # stop the server
        self.dataserv.stop()
        # exit
        raise SystemExit

def main():
    """Entry point for data server"""
    from nspyre.misc.logging import nspyre_init_logger
    import logging
    import argparse

    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='nspyre-dataserv',
                            description='Run an nspyre data server')
    arg_parser.add_argument('-l', '--log',
                            default=None,
                            help='log to the provided file / directory')
    arg_parser.add_argument('-p', '--port', type=int,
                            default=DATASERV_PORT,
                            help='Port to run the server on')
    arg_parser.add_argument('-q', '--quiet',
                            action='store_true',
                            help='disable logging')
    arg_parser.add_argument('-v', '--verbosity',
                            default='info',
                            help='the verbosity of logging to stdout - options are: '
                            'debug, info, warning, error')
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
            pass
            # TODO
            # raise DataServerError('didn\'t recognize logging level [{}]'.\
            #                             format(cmd_args.verbosity)) from None
        if cmd_args.log:
            nspyre_init_logger(log_level, log_path=Path(cmd_args.log),
                                        log_path_level=logging.DEBUG,
                                        prefix='dataserv')
        else:
            # the user asked for no log file
            nspyre_init_logger(log_level)

    # init and start data server
    logger.info('starting data server...')
    dataserv = DataServer(cmd_args.port)

    # start the shell prompt event loop
    cmd_prompt = DataservCmdPrompt(dataserv)
    cmd_prompt.prompt = 'dataserv > '
    cmd_prompt.cmdloop('data server started...')

if __name__ == '__main__':
    main()
