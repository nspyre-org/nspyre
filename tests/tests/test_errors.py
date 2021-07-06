from pathlib import Path
import logging

import pytest

from nspyre import InstrumentGateway, InstrumentServerError, InstrumentGatewayError

class TestErrors:
    def test_output(self, tmp_log_file, inserv, gateway):
        """Test that the log files are working properly and receiving all the stdout / stderr messages as well"""

        # TODO
        # do some stuff and throw some errors to generate log messages
        import pdb; pdb.set_trace()

        # open the log files
        with open(tmp_log_file) as main_reader, open(inserv) as inserv_reader:
            main_log = main_reader.read()
            inserv_log = inserv_reader.read()

            # # make sure each message in stdout and stderr were logged to the file
            # for o in out:
            #     assert o in log
            # for e in err:
            #     assert e in log
