"""The base exception class and subclasses for exceptions raised by NSpyre.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging

logger = logging.getLogger(__name__)


class InstrumentGatewayError(Exception):
    """Raised for failures related to the Instrument Gateway."""


class InstrumentServerError(Exception):
    """Raised for failures related to the Instrument Server."""


class InstrumentManagerError(Exception):
    """Raised for failures related to the InstrumentManagerWindow QMainWindow."""
