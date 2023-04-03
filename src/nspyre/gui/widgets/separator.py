"""
Lines to separate GUI elements. From https://stackoverflow.com/questions/5671354/how-to-programmatically-make-a-horizontal-line-in-qt.
"""
from pyqtgraph.Qt import QtWidgets


class QHLine(QtWidgets.QFrame):
    """Qt widget that displays a horizontal line."""

    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)


class QVLine(QtWidgets.QFrame):
    """Qt widget that displays a vertical line."""

    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
