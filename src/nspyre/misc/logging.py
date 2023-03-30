import datetime
import logging
import sys
from io import TextIOBase
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOG_FILE_MAX_SIZE = 100e6
"""Max size of a log file (in bytes) before creating a new one."""

class _StreamToLog(TextIOBase):
    """Fake stream object that redirects writes to a logger"""

    def __init__(self, logger: logging.Logger, log_level: int, terminator: str):
        super().__init__()
        self.logger = logger
        self.log_level = log_level
        self.write_buffer = ''
        self.terminator = terminator

    def write(self, buff: str):
        """Override the stream write method"""
        while buff:
            # if buff contains a terminator, we should split into multiple
            # log messages, separated by the terminator
            if self.terminator in buff:
                before, _, after = buff.partition(self.terminator)
                self.write_buffer += before
                self.logger.log(self.log_level, self.write_buffer)
                self.write_buffer = ''
                buff = after
            # otherwise, just add it to the buffer for writing later when
            # a terminator is received
            else:
                self.write_buffer += buff
                buff = ''

    def flush(self):
        """Write out the contents of the current buffer"""
        if self.write_buffer:
            self.write(self.terminator)


def nspyre_init_logger(
    log_level: int,
    log_path: Path = None,
    log_path_level: int = 0,
    prefix: str = '',
    file_size: int = None,
):
    """Initialize system-wide logging to stdout/err and, optionally, a file.

    Args:
        log_level: Log messages of lower severity than this will not be sent \
            to stdout/err (e.g. :code:`logging.INFO`).
        log_path: If a file, log to that file. If a directory, generate a log \
            file name containing the prefix and date/time, and create a new \
            log file in that directory. If :code:`None`, only log to stdout/err.
        log_path_level: Logging level for the log file. Leave as :code:`None` \
            for same as log_level.
        prefix: If a directory was specified for log_path, prepend this string \
            to the log file name.
        file_size: Maximum log file size (bytes). If this size is exceeded, \
            the log file is rotated according to :code:`RotatingFileHandler` \
            (https://docs.python.org/3/library/logging.handlers.html).
    """

    root_logger = logging.getLogger()
    # the root logger will accept all messages
    root_logger.setLevel(logging.DEBUG)

    # log format for stdout messages
    stdout_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)s] (%(filename)s:%(lineno)s) %(message)s',
        '%Y-%m-%d %H:%M:%S',
    )
    # create stdout log handler
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(stdout_formatter)
    root_logger.addHandler(stdout_handler)

    # all stderr messages will now be redirected to a special logger
    stderr_logger = logging.getLogger('stderr')
    stderr_logger.propagate = False
    sys.stderr = _StreamToLog(stderr_logger, logging.CRITICAL, '\n')  # type: ignore

    # log format for stderr messages
    stderr_formatter = logging.Formatter('[stderr] %(message)s')
    # create stderr log handler
    stderr_handler = logging.StreamHandler(stream=sys.stdout)
    stderr_handler.setLevel(log_level)
    stderr_handler.setFormatter(stderr_formatter)
    stderr_logger.addHandler(stderr_handler)

    # if a log file / folder was specified
    if log_path:
        # resolve relative paths
        log_path = log_path.expanduser().resolve()

        if log_path.is_dir():
            # log to a file in the folder
            file_name = datetime.datetime.now().strftime(
                '%Y-%m-%d-%H-%M-%S.log'.format()
            )
            # prepend the prefix if present
            if prefix:
                file_name = '{}-{}'.format(prefix, file_name)
            log_path = log_path / Path(file_name)

        # create the file handler
        if file_size:
            file_handler: Any = RotatingFileHandler(
                log_path, maxBytes=file_size, backupCount=1000
            )
        else:
            file_handler = logging.FileHandler(log_path)
        file_formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d [%(levelname)8s] (%(filename)20s:%(lineno)4s) %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        file_handler.setFormatter(file_formatter)
        if log_path_level:
            file_handler.setLevel(log_path_level)
        else:
            file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
        stderr_logger.addHandler(file_handler)
