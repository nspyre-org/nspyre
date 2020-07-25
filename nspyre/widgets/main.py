from PyQt5 import QtCore, QtWidgets
from nspyre.widgets.image import ImageWidget
from nspyre.utils.utils import join_nspyre_path, get_configs
from subprocess import Popen
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
            cmd = 'bash -c "activate {}; python {}"'.format(get_configs()['conda_env'], filename)
            Popen(cmd, shell=True)
        else:
            Popen(['python', join_nspyre_path(nspyre_py_file)])
        print(time.time()-start)

if __name__ == '__main__':
    from nspyre.widgets.app import NSpyreApp
    app = NSpyreApp([])
    w = Spyre_Launcher()
    w.show()
    app.exec_()

    # parse command-line arguments
    arg_parser = argparse.ArgumentParser(prog='inserv',
                            usage='%(prog)s [options]',
                            description='Run an nspyre instrument server')
    arg_parser.add_argument('-c', '--config',
                            default=DEFAULT_CONFIG,
                            help='server configuration file location')
    arg_parser.add_argument('-l', '--log',
                            default=DEFAULT_LOG,
                            help='server log file location')
    arg_parser.add_argument('-m', '--mongo',
                            default=None,
                            help='mongodb address e.g. '
                            'mongodb://192.168.1.27:27017/')
    arg_parser.add_argument('-q', '--quiet',
                            action='store_true',
                            help='disable logging')
    arg_parser.add_argument('-v', '--verbose',
                            action='store_true',
                            help='log debug messages')
    cmd_args = arg_parser.parse_args()

    # configure server logging behavior
    if not cmd_args.quiet:
        logging.basicConfig(level=logging.DEBUG if cmd_args.verbose
                        else logging.INFO,
                        format='%(asctime)s -- %(levelname)s -- %(message)s',
                        handlers=[logging.FileHandler(cmd_args.log, 'w+'),
                                logging.StreamHandler()])
    # init and start RPyC server
    logging.info('starting instrument server...')
    inserv = InstrumentServer(cmd_args.config, cmd_args.mongo)

    # start the shell prompt event loop
    cmd_prompt = InservCmdPrompt(inserv)
    cmd_prompt.prompt = 'inserv > '
    cmd_prompt.cmdloop('instrument server started...')
