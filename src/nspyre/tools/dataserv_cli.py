"""
A CLI for the DataServer

Author: Jacob Feder
Date: 11/28/2020
"""

import argparse
from cmd import Cmd
import pdb
import logging
from threading import Thread
import logging
import argparse
import signal

from ..dataserv.dataserv import DataServer
from ..misc.logging import nspyre_init_logger, LOG_FILE_MAX_SIZE

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
        # notify the command loop to exit
        return True

def _cmd_prompt(dataserv_cmd):
    dataserv_cmd.cmdloop()

def main():
    """Entry point for data server"""

    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='nspyre-dataserv',
                            description='Run an nspyre data server')
    arg_parser.add_argument('-l', '--log',
                            default=None,
                            help='log to the provided file / directory')
    arg_parser.add_argument('-p', '--port', type=int,
                            default=None,
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
            raise ValueError('didn\'t recognize logging level [{}]'.\
                                        format(cmd_args.verbosity)) from None
        if cmd_args.log:
            nspyre_init_logger(log_level, log_path=Path(cmd_args.log),
                                        log_path_level=logging.DEBUG,
                                        prefix='dataserv',
                                        filesize=LOG_FILE_MAX_SIZE)
        else:
            # the user asked for no log file
            nspyre_init_logger(log_level)

    # init the data server
    if cmd_args.port:
        dataserv = DataServer(cmd_args.port)
    else:
        dataserv = DataServer()

    # properly stop the server when a kill signal is received
    def stop_server(signum, frame):
        dataserv.stop()
    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    # init command prompt
    cmd_prompt = DataservCmdPrompt(dataserv)
    cmd_prompt.prompt = 'dataserv > '

    # start the shell prompt event loop in a new thread, since DataServer
    # must be run in the main thread
    # daemon=True so that the program will exit when the data server is stopped with a signal - otherwise the cmd loop will hang forever
    cmd_prompt_thread = Thread(target=_cmd_prompt, args=(cmd_prompt,), daemon=True)
    cmd_prompt_thread.start()

    # start the data server event loop
    logger.info('starting data server...')
    dataserv.serve_forever()

if __name__ == '__main__':
    main()
