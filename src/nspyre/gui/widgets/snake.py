"""
Ssssspin snake logo.

Copyright (c) 2021, Jacob Feder
All rights reserved.

This work is licensed under the terms of the 3-Clause BSD license.
For a copy, see <https://opensource.org/licenses/BSD-3-Clause>.
"""
from pathlib import Path

from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

HERE = Path(__file__).parent


class sssss(QtWidgets.QWidget):
    """Image widget showing the nspyre logo."""

    def __init__(self, size=300):
        """
        Args:
            size: size of the logo in pixels.
        """
        super().__init__()

        # label to display the image
        spin_snake_img_widget = QtWidgets.QLabel(self)
        # logo image
        pixmap = QtGui.QPixmap(str(HERE / '../images/ssssspin.png'))
        # rescale the image
        scaled_pixmap = pixmap.scaledToHeight(
            size, QtCore.Qt.TransformationMode.SmoothTransformation
        )
        spin_snake_img_widget.setPixmap(scaled_pixmap)

        # put the widget centered in a vertical layout
        snake_layout = QtWidgets.QVBoxLayout()
        snake_layout.addWidget(
            spin_snake_img_widget, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.setLayout(snake_layout)
