"""
NSpyre application style settings.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from pathlib import Path

from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtCore

HERE = Path(__file__).parent

dark = QtGui.QColor(53, 53, 53)  # (61, 64, 62) (196,201,201)
nspyre_palette = QtGui.QPalette()
nspyre_palette.setColor(QtGui.QPalette.ColorRole.Window, dark)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(25, 25, 25))
nspyre_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, dark)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtCore.Qt.GlobalColor.white)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.white)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.Button, dark)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.white)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
nspyre_palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
nspyre_palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218))
nspyre_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.black)

nspyre_style_sheet = (HERE / 'style.qss').read_text()

nspyre_font = QtGui.QFont('Helvetica [Cronyx]', 14)
