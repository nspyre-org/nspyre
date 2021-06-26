"""The base exception class and subclasses for exceptions raised by NSpyre.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging

logger = logging.getLogger(__name__)


class NSpyreError(Exception):
    """Base class for all NSpyre exceptions."""

    def __init__(self, message='', exception=None, error_labels=None):
        super().__init__(message)
        self._message = message
        self._error_labels = set(error_labels or [])
        if exception:
            logger.exception(exception)

    def has_error_label(self, label):
        """Return True if this error contains the given label."""
        return label in self._error_labels

    def _add_error_label(self, label):
        """Add the given label to this error."""
        self._error_labels.add(label)

    def _remove_error_label(self, label):
        """Remove the given label from this error."""
        self._error_labels.discard(label)


class InstrumentGatewayError(NSpyreError):
    """Raised for failures related to the Instrument Gateway."""


class InstrumentServerError(NSpyreError):
    """Raised for failures related to the Instrument Server."""


class InstrumentManagerError(NSpyreError):
    """Raised for failures related to the InstrumentManagerWindow QMainWindow."""
