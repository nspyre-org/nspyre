import logging
from threading import Lock
from typing import Dict
from collections.abc import Iterable

from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtWidgets

_logger = logging.getLogger(__name__)


class _ObjectOnMainThread(QtCore.QObject):
    def __init__(self):
        super().__init__()
        # move self to main thread
        self.moveToThread(QtWidgets.QApplication.instance().thread())

    def run(self, fun, args: tuple, kwargs: Dict, blocking: bool):
        if blocking:
            wrapper_list = QtCore.QMetaObject.invokeMethod(
                self,
                '_run',
                QtCore.Qt.ConnectionType.BlockingQueuedConnection,
                QtCore.Q_RETURN_ARG(list),
                QtCore.Q_ARG(object, fun),
                QtCore.Q_ARG(tuple, args),
                QtCore.Q_ARG(dict, kwargs),
            )
            return wrapper_list[0]
        else:
            QtCore.QMetaObject.invokeMethod(
                self,
                '_run',
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(object, fun),
                QtCore.Q_ARG(tuple, args),
                QtCore.Q_ARG(dict, kwargs),
            )

    @QtCore.pyqtSlot(object, tuple, dict, result=list)
    def _run(self, fun, args, kwargs):
        return [fun(*args, **kwargs)]


class QThreadSafeObject(QtCore.QObject):
    """Qt object associated with a new QThread. Implements several methods to
    make it easier to work with data in a thread-safe way."""

    def __init__(self):
        super().__init__()
        self.mutex = Lock()
        """Mutex to lock access to instance variables."""

        # object that belongs to main thread
        self.main_obj = _ObjectOnMainThread()

        self.thread = QtCore.QThread()
        """Thread to manage access requests for this object."""

        # move this object to the new thread
        self.moveToThread(self.thread)

        # quit the thread when this object is destroyed
        self.destroyed.connect(self._wait_thread_quit)

        # start the thread to handle requests
        self.thread.start()

    def run_main(self, fun, *args, blocking=False, **kwargs):
        """Run the given function on the main thread.

        Args:
            fun: Function to run.
            args: Arguments to the function.
            kwargs: Keyword arguments to the function.
            blocking: If true, block until the function returns. Non-blocking
                calls cannot return anything.

        Returns:
            Return value of the function.
        """
        return self.main_obj.run(fun, args, kwargs, blocking=blocking)

    def run_safe(self, fun, *args, blocking=False, **kwargs):
        """Run a given function on the thread of this object.

        Args:
            fun: Function to run.
            args: Arguments to the function.
            kwargs: Keyword arguments to the function.
            blocking: If true, block until the function returns. Non-blocking
                calls cannot return anything.

        Returns:
            Return value of the function.
        """
        if blocking:
            wrapper_list = QtCore.QMetaObject.invokeMethod(
                self,
                '_run_safe',
                QtCore.Qt.ConnectionType.BlockingQueuedConnection,
                QtCore.Q_RETURN_ARG(list),
                QtCore.Q_ARG(object, fun),
                QtCore.Q_ARG(tuple, args),
                QtCore.Q_ARG(dict, kwargs),
            )
            if len(wrapper_list):
                return wrapper_list[0]
        else:
            QtCore.QMetaObject.invokeMethod(
                self,
                '_run_safe',
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(object, fun),
                QtCore.Q_ARG(tuple, args),
                QtCore.Q_ARG(dict, kwargs),
            )

    @QtCore.pyqtSlot(object, tuple, dict, result=list)
    def _run_safe(self, fun, args, kwargs):
        # wrap the result in a list in order to have a standardized return type
        return [fun(*args, **kwargs)]

    def get_safe(self, attrs: Iterable[str]) -> tuple:
        """Retrieve object attributes in a thread-safe way by accessing them
        while holding the internal mutex.

        Args:
            attrs: Object attribute names.

        Returns:
            tuple of object attributes.
        """
        if QtCore.QThread.currentThread() == self.thread:
            return tuple(self._get_safe(attrs))
        else:
            return tuple(
                QtCore.QMetaObject.invokeMethod(
                    self,
                    '_get_safe',
                    QtCore.Qt.ConnectionType.BlockingQueuedConnection,
                    QtCore.Q_RETURN_ARG(list),
                    QtCore.Q_ARG(list, attrs),
                )
            )

    @QtCore.pyqtSlot(list, result=list)
    def _get_safe(self, attrs) -> list:
        """Helper for get_safe()."""
        with self.mutex:
            ret = []
            for i in attrs:
                ret.append(getattr(self, i))
            return ret

    def _wait_thread_quit(self):
        """Wait until the internal thread quits."""
        import pdb; pdb.set_trace()
        print('quiting, waiting')
        self.thread.quit()
        self.thread.wait()
