import logging
from pathlib import Path

import pytest
from nspyre import nspyre_init_logger

logger_name = 'test_errors'
logger = logging.getLogger(logger_name)
HERE = Path(__file__).parent


class TestErrors:
    def test_output(self, gateway):
        """Test that the log files are working properly and receiving all the
        stdout / stderr messages as well."""

        # Generate a temporary log file that can be analyzed by the test
        log_path = Path(HERE / 'test_errors.log')
        # Delete the log file if it already exists
        log_path.unlink(missing_ok=True)
        nspyre_init_logger(
            logging.DEBUG, log_path=log_path, log_path_level=logging.DEBUG
        )

        # messages logged in the main / client python instance
        log_messages = []

        logger.debug('debug test')
        log_messages.append('debug test')
        logger.info('info test')
        log_messages.append('info test')
        logger.warning('warning test')
        log_messages.append('warning test')
        logger.error('error test')
        log_messages.append('error test')
        # TODO for some reason nspyre_init_logger() doesn't seem able to
        # permanently overwrite sys.stdout/err in pytest
        # print('stderr test')
        # log_messages.append('[stderr] stderr test')
        # print('stdout test')
        # log_messages.append('stdout test')

        # open the log files
        with open(log_path) as log_reader:
            log = log_reader.read()
            # make sure each message was logged to the file
            for m in log_messages:
                assert m in log

        with pytest.raises(AttributeError):
            gateway.nonexistent_device
