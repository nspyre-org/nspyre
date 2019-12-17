from PyQt5 import QtCore, QtWidgets
from nspyre.widgets.image import ImageWidget
from nspyre.utils import join_nspyre_path
from subprocess import Popen, CREATE_NEW_CONSOLE
import os
import time


class Spyre_Launcher(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        main_layout = QtWidgets.QVBoxLayout()
        im = ImageWidget(join_nspyre_path('images/spyre.png'))
        main_layout.addWidget(im)

        # btn_widget = QtWidgets.QWidget()
        # btn_layout = QtWidgets.QHBoxLayout()

        self.inst_server_btn = QtWidgets.QPushButton('Start Instrument Server')
        self.inst_manager_btn = QtWidgets.QPushButton('Start Instrument Manager')
        self.view_manager_btn = QtWidgets.QPushButton('Start View Manager')
        self.spyrelet_launcher_btn = QtWidgets.QPushButton('Start Spyrelet Launcher')
        self.data_explorer_btn = QtWidgets.QPushButton('Data Explorer')

        main_layout.addWidget(self.inst_server_btn)
        main_layout.addWidget(self.inst_manager_btn)
        main_layout.addWidget(self.view_manager_btn)
        main_layout.addWidget(self.spyrelet_launcher_btn)
        main_layout.addWidget(self.data_explorer_btn)

        self.inst_server_btn.clicked.connect(lambda: self.launch('instrument_server.py', new_console=True))
        self.inst_manager_btn.clicked.connect(lambda: self.launch('widgets/instrument_manager.py'))
        self.view_manager_btn.clicked.connect(lambda: self.launch('widgets/view_manager.py'))
        self.spyrelet_launcher_btn.clicked.connect(lambda: self.launch('widgets/launcher.py'))
        self.data_explorer_btn.clicked.connect(lambda: self.launch('widgets/data_explorer.py'))

        self.setLayout(main_layout)
    
    def launch(self, nspyre_py_file, new_console=False):
        start = time.time()
        if new_console:
            filename = os.path.normpath(join_nspyre_path(nspyre_py_file))
            filename = filename.replace('\\', '/')
            cmd = 'bash -c "activate notebook; python {}"'.format(filename)
            Popen(cmd, creationflags=CREATE_NEW_CONSOLE)
        else:
            Popen(['python', join_nspyre_path(nspyre_py_file)])
        print(time.time()-start)




if __name__ == '__main__':
    from nspyre.widgets.app import NSpyreApp
    app = NSpyreApp([])
    w = Spyre_Launcher()
    w.show()
    app.exec_()