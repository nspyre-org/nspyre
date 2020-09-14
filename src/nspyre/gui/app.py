from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import pyqtRemoveInputHook

class NSpyreApp(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_theme()
        return

    def set_theme(self):
        fusion = QtWidgets.QStyleFactory.create('Fusion')
        self.setStyle(fusion)
        dark = QtGui.QColor(53, 53, 53)
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, dark)
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25,25,25))
        palette.setColor(QtGui.QPalette.AlternateBase, dark)
        palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Button, dark)
        palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        self.setPalette(palette)
        self.setStyleSheet("QToolTip { color: #ffffff; background-color: #353535; border: 1px solid white; }")
        return