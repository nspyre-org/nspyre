#!/usr/bin/env python
import time
import traceback
import logging

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow
from pyqtgraph import _connectCleanup as pyqtgraph_connectCleanup

from nspyre.config.config_files import load_meta_config
from nspyre.definitions import CLIENT_META_CONFIG_PATH
from nspyre.spyrelet.spyrelet import SpyreletLauncher
from nspyre.gui.widgets.param_widget import ParamWidget
from nspyre.gui.widgets.save_widget import Save_Widget
from nspyre.spyrelet.spyrelet import load_all_spyrelets
from nspyre.inserv.gateway import InservGateway

logger = logging.getLogger(__name__)


class ProgressBar(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vars = []
        # self.iterators = []
        layout = QtWidgets.QVBoxLayout()
        self.pbar = QtWidgets.QProgressBar()
        self.pbar.setTextVisible(True)
        self.text = QtWidgets.QLabel('stopped')
        layout.addWidget(self.pbar)
        layout.addWidget(self.text)
        self.setLayout(layout)
    
    def reset(self):
        self.vars = []
        # self.iterators = []
        self.text.setText('stopped')

    def call_iter(self, iterable, max_val):
        # self.iterators.append(iter(iterable))
        self.vars.append({'val': 0, 'max': max_val, 'start': time.time(), 'last': time.time(), 'avg': 0, 'tot': 0, 'rem': '?', 'per': 0})

        if max_val != '?':
            self.pbar.setValue(0)
            self.pbar.setRange(0, max_val)

    def call_next(self):
        self.vars[-1]['val'] += 1
        t = time.time()
        self.vars[-1]['avg'] = t-self.vars[-1]['last']
        self.vars[-1]['last'] = t
        self.vars[-1]['tot'] = t-self.vars[-1]['start']

        if self.vars[-1]['max'] != '?':
            self.pbar.setValue(self.vars[-1]['val'])
            self.pbar.setRange(0, self.vars[-1]['max'])
            self.vars[-1]['per'] = 100*self.vars[-1]['val']/self.vars[-1]['max']
            self.vars[-1]['rem'] = (self.vars[-1]['max'] - self.vars[-1]['val'])*self.vars[-1]['avg']
        s_with_max = '[{per:.0f}% {val:.0f}/{max:.0f} [{tot:.0f}s<{rem:.0f}s] {avg:.2f}s/it]'
        s_without_max = '[{val:.0f}[{tot:.0f}s] {avg:.2f}s/it]'
        self.text.setText('\t'.join([(s_without_max if d['max'] == '?' else s_with_max).format(**d)for d in self.vars]))
        QtWidgets.QApplication.processEvents()
    
    def call_stopiter(self):
        self.vars = self.vars[:-1]
        if not self.vars == [] and self.vars[-1]['max'] != '?':
            self.pbar.setValue(self.vars[-1]['max'])
            self.pbar.setRange(0, self.vars[-1]['max'])
            QtWidgets.QApplication.processEvents()
        # self.iterators = self.iterators[:-1]


class SpyreletLauncherWidget(QtWidgets.QWidget):
    def __init__(self, spyrelet, parent=None):
        self.spyrelet = spyrelet
        self.progress_bar = ProgressBar()
        self.launcher = SpyreletLauncher(spyrelet)
        self.param_w = ParamWidget(self.launcher.params)
        self.param_w.set(**self.launcher.get_defaults())
        super().__init__(parent=parent)

        # Build ctrl pannel
        ctrl_pannel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        self.run_btn = QtWidgets.QPushButton('Run')
        self.set_defaults_btn = QtWidgets.QPushButton('Set Defaults')
        self.save_btn = QtWidgets.QPushButton('Save')
        layout.addWidget(self.run_btn)
        layout.addWidget(self.save_btn)
        ctrl_pannel.setLayout(layout)

        # Build main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(ctrl_pannel)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.param_w)
        layout.addStretch()
        self.setLayout(layout)

        # Connect signal
        self.run_btn.clicked.connect(self.run)
        self.set_defaults_btn.clicked.connect(self.set_defaults)
        self.save_btn.clicked.connect(self.save_data)

        self.run_thread = None

    def run(self):
        if self.run_thread is None or self.run_thread.isFinished():
            self.progress_bar.reset()
            param_dict = self.param_w.get()
            self.run_thread = SpyreletRunThread(self.launcher, param_dict)
            self.run_thread.start()
            self.run_btn.setText('Stop')
            self.run_thread.finished.connect(lambda: self.run_btn.setText('Run'))
            self.run_thread.progressed_iter.connect(self.progress_bar.call_iter)
            self.run_thread.progressed_next.connect(self.progress_bar.call_next)
            self.run_thread.progressed_stopiter.connect(self.progress_bar.call_stopiter)
        else:
            self.run_thread.stop_requested.emit()

    def set_defaults(self):
        self.spyrelet.set_defaults(**self.param_w.get())

    def save_data(self):
        self.save_w = Save_Widget(self.spyrelet)
        self.save_w.show()

class SpyreletRunThread(QtCore.QThread):
    """Qt Thread which monitors for changes to qather a collection or a database
    and emits a signal when something happens.
    """
    progressed_iter = QtCore.pyqtSignal(object, object)  # This will be emitted when iter is called on progress is called in the spyrelet
    progressed_next = QtCore.pyqtSignal()  # This will be emitted when next is called on progress is called in the spyrelet
    progressed_stopiter = QtCore.pyqtSignal()  # This will be emitted when next is called on progress is called in the spyrelet
    stop_requested = QtCore.pyqtSignal()  # This will be emitted externally to stop the execution of a spyrelet prematurly

    def __init__(self, launcher, param_dict):
        super().__init__()
        self.param_dict = param_dict
        self.launcher = launcher
        self.spyrelet = self.launcher.spyrelet

        class ProgressIter():
            def __init__(_self, iterable):
                _self.iterable = iterable

            def __iter__(_self):
                try:
                    max_val = len(_self.iterable)
                except TypeError:
                    traceback.print_exc()
                    max_val = '?'
                _self.iterable = iter(_self.iterable)
                self.progressed_iter.emit(_self.iterable, max_val)
                return _self

            def __next__(_self):
                try:
                    val = next(_self.iterable)
                    self.progressed_next.emit()
                except StopIteration as e:
                    self.progressed_stopiter.emit()
                    raise e
                return val

        self.progress = ProgressIter
        self.stop_requested.connect(self.stop_run)

    def progress(self, iterator):
        for x in iterator:
            self.progressed.emit(iterator)
            yield x

    def run(self):
        self.launcher.run(progress=self.progress, **self.param_dict)

    def stop_run(self):
        self.spyrelet.stop()


class CombinedSpyreletWindow(QMainWindow):
    def __init__(self, gateway, spyrelets=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the main window layout to consist of vertical boxes.
        # The QVBoxLayout class lines up widgets vertically.
        layout = QtWidgets.QVBoxLayout()

        self.selector = QtWidgets.QComboBox()
        container = QtWidgets.QWidget()
        layout.addWidget(self.selector)
        layout.addWidget(container)

        #Create the launchers
        spyrelets = load_all_spyrelets(gateway) if spyrelets is None else spyrelets
        self.launchers = {name: SpyreletLauncherWidget(s) for name, s in spyrelets.items()}

        #Add to layout
        stacked_layout = QtWidgets.QStackedLayout()
        names = list(self.launchers.keys())
        names.sort()
        for n in names:
            stacked_layout.addWidget(self.launchers[n])
        container.setLayout(stacked_layout)
        self.setWindowTitle('NSpyre Spyrelet Window: {}'.format(names[0]))

        self.selector.addItems(names)
        self.container_layout = stacked_layout
        self.selector.currentTextChanged.connect(self.change_widget)
        w = QtWidgets.QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.show()

    def change_widget(self, name):
        self.container_layout.setCurrentWidget(self.launchers[name])
        self.setWindowTitle('NSpyre Spyrelet Window: {}'.format(name))


if __name__ == '__main__':
    import logging
    import sys
    from PyQt5.QtCore import Qt
    from nspyre.gui.app import NSpyreApp
    from nspyre.misc.logging import nspyre_init_logger

    nspyre_init_logger(logging.INFO)

    logger.info('starting Spyrelets...')
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = NSpyreApp([sys.argv])
    pyqtgraph_connectCleanup()
    config_path = load_meta_config(CLIENT_META_CONFIG_PATH)
    with InservGateway(config_path) as isg:
        combined_spyrelet_window = CombinedSpyreletWindow(isg)
        sys.exit(app.exec())
