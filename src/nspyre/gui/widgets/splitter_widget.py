from PyQt5 import QtWidgets, QtCore, QtGui

from enum import Enum
import os

class SplitterOrientation(Enum):

    vertical_left_button = 0
    vertical_right_button = 1
    horizontal_top_button = 2
    horizontal_bottom_button = 3

class Splitter(QtWidgets.QSplitter):

    def __init__(self, main_w, side_w, orientation=None, parent=None):
        if orientation is None:
            orientation = SplitterOrientation.vertical_left_button

        if orientation in [SplitterOrientation.vertical_left_button,
                           SplitterOrientation.vertical_right_button]:
            super().__init__(QtCore.Qt.Horizontal, parent=parent)
        else:
            super().__init__(QtCore.Qt.Vertical, parent=parent)
        horizontal = int(orientation.value >= 2)
        if not orientation.value % 2:
            # main widget on container 1
            c1_hover = SplitterHoverArea(self, orientation=orientation)
            c2_hover = None
            initial_size = [1, 0]
        else:
            c1_hover = None
            c2_hover = SplitterHoverArea(self, orientation=orientation)
            initial_size = [0, 1]
        c1 = Container(main_w, c1_hover)
        c2 = Container(side_w, c2_hover)
        self.addWidget(c1)
        self.addWidget(c2)
        self.orientation = orientation
        self.setSizes(initial_size)
        self.showMaximized()
        return

    def setSizes(self, sizes):
        super().setSizes(sizes)
        button = self.widget((self.orientation.value % 2)).collapse_area.button
        if ((not self.orientation.value % 2 and not sizes[1]) or
            (self.orientation.value % 2 and not sizes[0])):
            button.closed = True
            button.on_splitter_moved(None, None)
        else:
            button.closed = False
            button.on_splitter_moved(None, None)
        return

class SplitterHoverArea(QtWidgets.QWidget):

    width = 30
    height = 60

    def __init__(self, splitter, orientation=None, parent=None):
        if orientation is None:
            orientation = SplitterOrientation.vertical_left_button
        super().__init__(parent=parent)
        if orientation.value % 2:
            self.even = False
        else:
            self.even = True
        if orientation.value >= 2:
            # horizontal orientation
            self.width, self.height = self.height, self.width
            self.start_x = 0
            self.start_y = 0
            if self.even:
                self.end_x = self.height
            else: self.end_x = -self.height
            self.end_y = 0
        else:
            self.start_x = 0
            self.start_y = 0
            self.end_x = 0
            if self.even:
                self.end_y = self.width
            else:
                self.end_y = -self.width
        self.setFixedSize(self.width, self.height)
        self.orientation = orientation
        self.button = SplitterHoverButton(splitter, parent=self)
        self.on_hover(False, duration=0)
        return

    def enterEvent(self, ev):
        self.on_hover(True)
        return

    def leaveEvent(self, ev):
        self.on_hover(False)
        return

    def on_hover(self, entering, duration=200):
        animation = QtCore.QPropertyAnimation(self)
        animation.setDuration(duration)
        animation.setTargetObject(self.button)
        animation.setPropertyName(b'pos')
        animation.setEasingCurve(QtCore.QEasingCurve.Linear)

        if entering:
            start = QtCore.QPoint(self.end_y, self.end_x)
            end = QtCore.QPoint(self.start_y, self.start_x)
        else:
            start = QtCore.QPoint(self.start_y, self.start_x)
            end = QtCore.QPoint(self.end_y, self.end_x)

        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.start()
        return

class SplitterHoverButton(QtWidgets.QPushButton):

    button_style = '''
        background-image: url({image});
        background-repeat: no-repeat;
        background-position: center;
        background-color: rgb(53, 53, 53);
        width: {width}px;
        height: {height}px;
        border-{corner1}-radius: 30px;
        border-{corner2}-radius: 30px;
        border-color: rgb(20, 20, 20);
        border-style: outset;
        border-width: {border_width};
    '''

    def __init__(self, splitter, parent=None):
        super().__init__(parent=parent)
        hover_area = self.parent()
        self.closed = False
        if hover_area.orientation.value % 2:
            self.even = False
        else:
            self.even = True

        image_path = os.path.join(os.path.dirname(__file__),'..\\images\\')
        image_path = image_path.replace("\\","/")

        if hover_area.orientation.value >= 2:
            # horizontal orientation
            self.closed_image = image_path + '/{}_arrow.png'.format('up' if self.even else 'down')
            self.opened_image = image_path + '/{}_arrow.png'.format('down' if self.even else 'up')
            self.width = 60
            self.height = 30
            self.button_params = {
                'image': self.opened_image,
                'width': 60,
                'height': 30,
                'corner1': 'top-left',
                'corner2': 'top-right',
                'border_width': '0.5px 0.5px 0 0.5px',
            }
            if not self.even:
                self.button_params['corner1'] = 'bottom-left'
                self.button_params['corner2'] = 'bottom-right'
                self.button_params['border_width'] = '0 0.5px 0.5px 0.5px'

        else:
            self.closed_image = image_path + '/{}_arrow.png'.format('left' if self.even else 'right')
            self.opened_image = image_path + '/{}_arrow.png'.format('right' if self.even else 'left')
            self.width = 30
            self.height = 60
            self.button_params = {
                'image': self.opened_image,
                'width': 30,
                'height': 60,
                'corner1': 'top-left',
                'corner2': 'bottom-left',
                'border_width': '0.5px 0 0.5px 0.5px',
            }
            if not self.even:
                self.button_params['corner1'] = 'top-right'
                self.button_params['corner2'] = 'bottom-right'
                self.button_params['border_width'] = '0.5px 0.5px 0.5px 0'


        self.style = self.button_style.format(**self.button_params)
        self.setStyleSheet(self.style)
        self.setFixedSize(self.width, self.height)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.splitter = splitter
        self.maximize = 400
        self.minimize = 1
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
        self.clicked.connect(self.on_clicked)
        return

    def on_clicked(self):
        self.setStyleSheet(self.style)
        if self.closed:
            size = [self.maximize, self.minimize]
        else:
            size = [1,0]
        if not self.even: size[0], size[1] = size[1], size[0]
        self.splitter.setSizes(size)
        self.on_splitter_moved(None, None)
        return

    def on_splitter_moved(self, pos, idx):
        sizes = self.splitter.sizes()
        if not self.even: sizes[0], sizes[1] = sizes[1], sizes[0]
        hover_area = self.parent()
        if not sizes[1]:
            self.button_params['image'] = self.closed_image
            self.closed = True
        else:
            self.button_params['image'] = self.opened_image
            self.closed = False
            self.maximize = sizes[0]
            self.minimize = sizes[1]
        self.style = self.button_style.format(**self.button_params)
        self.setStyleSheet(self.style)
        return

    def resizeEvent(self, ev):
        ev.ignore()
        return

class Container(QtWidgets.QWidget):

    def __init__(self, w, collapse=None, parent=None):
        super().__init__(parent=parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(w)
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0,0,0,0)
        if collapse is not None:
            self.collapse_area = collapse
            self.collapse_area.setParent(self)
        else:
            self.collapse_area = None
        return

    def resizeEvent(self, ev):
        if self.collapse_area is not None:
            if self.collapse_area.orientation.value % 2:
                even = False
            else:
                even = True
            if self.collapse_area.orientation.value >= 2:
                # horizontal orientation
                size = ev.size()
                b_size = self.collapse_area.size()
                w, h = size.width(), size.height()
                b_w, b_h = b_size.width(), b_size.height()
                if even:
                    self.collapse_area.move((w - b_w) / 2, h - b_h)
                else:
                    self.collapse_area.move((w - b_w) / 2, 0)
            else:
                size = ev.size()
                b_size = self.collapse_area.size()
                w, h = size.width(), size.height()
                b_w, b_h = b_size.width(), b_size.height()
                if even:
                    self.collapse_area.move(w - b_w, (h - b_h) / 2)
                else:
                    self.collapse_area.move(0, (h - b_h) / 2)
        return


def main():
    app = SpyreApp([])

    layout = QtWidgets.QGridLayout()

    for orientation in range(4):
        s_orientation = SplitterOrientation(orientation)
        left_item = QtWidgets.QLabel('Left')
        right_item = QtWidgets.QLabel('Right')
        s = Splitter(left_item, right_item, orientation=s_orientation)
        layout.addWidget(s, orientation // 2, orientation % 2)

    container = QtWidgets.QWidget()

    container.setLayout(layout)
    container.show()
    app.exec_()
    return


if __name__ == '__main__':
    main()
