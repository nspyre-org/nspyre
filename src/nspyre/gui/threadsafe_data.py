from pyqtgraph.Qt import QtCore
import logging

_logger = logging.getLogger(__name__)

class QThreadSafeData(QtCore.QObject):
    """Manage access to Qt state variables in a thread-safe way."""

    def __init__(self):
        super().__init__()
        # mutex to lock access to the data
        self.mutex = Lock()
        # thread to
        self.thread = QtCore.QThread()
        # move this object to the new thread
        self.moveToThread(self.thread)
        self.thread.start()

    def get_threadsafe(self, attr):
        """Retrieve object attribute in a thread-safe way.

        Args:
            attr: Object attribute name.

        Returns:
            Object attribute.
        """

        # TODO check if current thread is same as self.thread
        # https://stackoverflow.com/questions/23452218/proper-use-of-qthread-currentthreadid
        if int(QThread.currentThreadId()) == 0: # self.thread.id()
            return self._get_threadsafe(attr)
        else:
            return QtCore.QMetaObject.invokeMethod(self, 
                '_get_threadsafe', 
                QtCore.Qt.ConnectionType.BlockingQueuedConnection, 
                QtCore.Q_RETURN_ARG(object), 
                QtCore.Q_ARG(str, attr))

    @QtCore.pyqtSlot(str, result=object)
    def _get_threadsafe(self, attr) -> object:
        """Helper for get_threadsafe()."""
        with self.mutex:
            return getattr(self, attr)

#     def __getattribute__(self, attr):
#         return self.get_threadsafe(attr)
# #        return super().__getattribute__(attr) 
