"""The base exception class and subclasses for exceptions raised by NSpyre.

The InstrumentManagerWindow class is the main GUI window for viewing the live
state and settings of the hardware devices connected to an NSpyre InstrumentServer.
It is defined by the QtWidgets.QMainWindow subclass from Qt and consists of a
QTreeWidget and subsequent QTreeWidgetItem(s) for displaying the attributes of
each device located on each connected Instrument Server. It is also responsible
for creating and connecting all the callback functions to the device drivers'
PySignal.Signal(s) for updating it's own GUI QtWidgets.QtWidget(s) in real-time.
i.e. QComboBox, QLineEdit, SpinBox, etc.


  Typical usage example:

  app = app.NSpyreApp([sys.argv])
  pyqtgraph._connectCleanup()
  with ..inserv.gateway.InservGateway() as isg:
      window = main_window.InstrumentManagerWindow(isg)
      sys.exit(app.exec())

Copyright (c) 2020, Alexandre Bourassa, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
import logging


class NSpyreError(Exception):
    """Base class for all NSpyre exceptions."""
    def __init__(self, message='', error_labels=None):
        super().__init__(message)
        self._message = message
        self._error_labels = set(error_labels or [])

    def has_error_label(self, label):
        """Return True if this error contains the given label."""
        return label in self._error_labels

    def _add_error_label(self, label):
        """Add the given label to this error."""
        self._error_labels.add(label)

    def _remove_error_label(self, label):
        """Remove the given label from this error."""
        self._error_labels.discard(label)


class EntryNotFoundError(NSpyreError):
    """Raised for failures Exception for when a configuration file doesn't contain the desired
    entry"""
    def __init__(self, config_path, msg=None):
        if msg is None:
            msg = 'Config file was expected to contain parameter: [{}] ' \
                    'but it wasn\'t found'.format(' -> '.join(config_path))
        super().__init__(msg)
        self.config_path = config_path


class ConfigurationError(NSpyreError):
    """Raised for failures with loading configuration files."""


class SpyreletLoadError(NSpyreError):
    """Raised for failures while loading a Spyrelet."""


class SpyreletUnloadError(NSpyreError):
    """Raised for failures with unloading a Spyrelet."""


class SpyreletRunningError(NSpyreError):
    """Raised for failures with executing the main method of a Spyrelet."""


class OSNotSupportedError(NSpyreError):
    """Raise for failures with"""


class InservGatewayError(NSpyreError):
    """Raised for failures related to the InservGateway."""


class InstrumentServerError(NSpyreError):
    """Raised for failures related to the InstrumentServer Service."""


class InstrumentManagerError(NSpyreError):
    """Raised for failures related to the InstrumentManagerWindow QMainWindow."""
