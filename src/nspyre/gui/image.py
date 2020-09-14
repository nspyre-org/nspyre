from PyQt5 import QtWidgets, QtGui

class ImageWidget(QtWidgets.QWidget):
    def __init__(self, filename, parent=None):
        super().__init__(parent=parent)
        label = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(filename)
        label.setPixmap(pixmap)

        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(label,0,1) #add the widget in the second colum
        layout.setColumnStretch(0,1) #set stretch of first
        layout.setColumnStretch(2,1) #and third column
        self.setLayout(layout)