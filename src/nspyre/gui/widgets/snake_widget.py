from pathlib import Path

from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui
from pyqtgraph.Qt import QtWidgets

_HERE = Path(__file__).parent


class sssss(QtWidgets.QWidget):
    """QWidget that displays the nspyre logo."""

    def __init__(self, size=300):
        """
        Args:
            size: Size of the logo in pixels.
        """
        super().__init__()

        # label to display the image
        spin_snake_img_widget = QtWidgets.QLabel(self)
        # logo image
        pixmap = QtGui.QPixmap(str(_HERE / '../images/ssssspin.png'))
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
