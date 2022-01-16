"""
NSpyre application style settings.

Copyright (c) 2021, Michael Solomon, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QPalette

HERE = Path(__file__).parent

dark = QColor(53, 53, 53)  # (61, 64, 62) (196,201,201)
nspyre_palette = QPalette()
nspyre_palette.setColor(QPalette.Window, dark)
nspyre_palette.setColor(QPalette.WindowText, Qt.white)
nspyre_palette.setColor(QPalette.Base, QColor(25, 25, 25))
nspyre_palette.setColor(QPalette.AlternateBase, dark)
nspyre_palette.setColor(QPalette.ToolTipText, Qt.white)
nspyre_palette.setColor(QPalette.Text, Qt.white)
nspyre_palette.setColor(QPalette.Button, dark)
nspyre_palette.setColor(QPalette.ButtonText, Qt.white)
nspyre_palette.setColor(QPalette.BrightText, Qt.red)
nspyre_palette.setColor(QPalette.Link, QColor(42, 130, 218))
nspyre_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
nspyre_palette.setColor(QPalette.HighlightedText, Qt.black)

nspyre_style_sheet = (HERE / 'style.qss').read_text()

nspyre_font = QFont('Helvetica [Cronyx]', 14)
