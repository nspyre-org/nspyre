import logging
from pathlib import Path

from nspyre import nspyre_init_logger

logger_name = 'test_errors'
logger = logging.getLogger(logger_name)
HERE = Path(__file__).parent


class TestErrors:
    def test_output(self, inserv, gateway):
        """Test that the log files are working properly and receiving all the stdout / stderr messages as well"""

        # Generate a temporary log file that can be analyzed by the test
        log_path = Path(HERE / 'test_errors.log')
        # Delete the log file if it already exists
        log_path.unlink(missing_ok=True)
        nspyre_init_logger(
            logging.DEBUG, log_path=log_path, log_path_level=logging.DEBUG
        )

        # messages logged in the main / client python instance
        main_messages = []
        # messages logged in the instrument server
        inserv_messages = []

        logger.debug('debug test')
        main_messages.append('debug test')
        logger.info('info test')
        main_messages.append('info test')
        logger.warning('warning test')
        main_messages.append('warning test')
        logger.error('error test')
        main_messages.append('error test')
        # TODO for some reason nspyre_init_logger() doesn't seem able to
        # permanently overwrite sys.stdout/err in pytest
        # print('stderr test')
        # main_messages.append('[stderr] stderr test')
        # print('stdout test')
        # main_messages.append('stdout test')

        # purposefully throw an error on the instrument server
        try:
            # the instrument server should log this error
            gateway.nonexistent_device
        except AttributeError:
            pass

        # open the log files
        with open(log_path) as main_reader, open(inserv['log']) as inserv_reader:
            main_log = main_reader.read()
            inserv_log = inserv_reader.read()
            # make sure each message was logged to the file
            for m in main_messages:
                assert m in main_log
            for m in inserv_messages:
                assert m in inserv_log
