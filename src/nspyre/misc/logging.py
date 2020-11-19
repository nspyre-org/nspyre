"""
Set up logging for an nspyre app

Author: Jacob Feder
Date: 11/14/2020
"""

###########################
# imports
###########################

# std
import logging
from pathlib import Path
import datetime

###########################
# classes / functions
###########################

def nspyre_init_logger(log_level, log_path=None, log_path_level=None, prefix=None):
    """Initialize system-wide logging to stdout and, optionally, a file
    log_level: stdout log messages of lower severity than this will be ignored (e.g. logging.INFO)
    log_path: if a file, log to that file; if a directory, generate a log file 
                name and create a new log file in that directory; if None, only log to stdout
    log_path_level: logging level for the log file - leave as None for same as log_level
    prefix: if a directory was specified for log_path, prepend this string
                to the log file name"""

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # create default log to stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(levelname)8s] %(message)s', '%Y-%m-%d %H:%M:%S')
    stream_handler.setFormatter(stream_formatter)
    root_logger.addHandler(stream_handler)

    # if a log file / folder was specified
    if log_path:
        # resolve relative paths
        if not log_path.is_absolute():
            log_path = Path.cwd() / log_path
        log_path = log_path.resolve()

        if log_path.is_file():
            pass
        elif log_path.is_dir():
            # log to a file in the folder
            file_name = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S.log'.format())
            # prepend the prefix if present
            if prefix:
                file_name = '{}-{}'.format(prefix, file_name)
            log_path = log_path / Path(file_name)

        # create the file handler
        file_handler = logging.FileHandler(log_path)
        file_formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(levelname)s] (%(filename)s:%(lineno)s) %(message)s', '%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        if log_path_level:
            file_handler.setLevel(log_path_level)
        else:
            file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
