from PyQt5 import QtWidgets
from nspyre.spyrelet import Spyrelet_Launcher
from nspyre.widgets.param_widget import ParamWidget

class Spyrelet_Launcher_Widget(QtWidgets.QWidget):
    def __init__(self, spyrelet, parent=None):
        self.spyrelet = spyrelet
        self.launcher = Spyrelet_Launcher(spyrelet)
        self.param_w = ParamWidget(self.launcher.params)
        super().__init__(parent=parent)

        #Build ctrl pannel
        ctrl_pannel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        run_btn = QtWidgets.QPushButton('Run')
        progress_bar = QtWidgets.QLabel('Progress bar in construction')#@TODO add progress bar
        layout.addWidget(run_btn)
        layout.addWidget(progress_bar)
        ctrl_pannel.setLayout(layout)

        #Build main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(ctrl_pannel)
        layout.addWidget(self.param_w)
        self.setLayout(layout)

        #Connect signal
        run_btn.clicked.connect(self.run)

    def run(self):
        print('run!')
        self.launcher.run(**self.param_w.get())
        
    