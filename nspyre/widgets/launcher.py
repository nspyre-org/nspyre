from PyQt5 import QtWidgets, QtCore
from nspyre.spyrelet import Spyrelet_Launcher
from nspyre.widgets.param_widget import ParamWidget
from nspyre.widgets.save_widget import Save_Widget
from nspyre.utils import RangeDict, get_configs, get_class_from_str
import time
import traceback

class Progress_Bar(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vars = []
        self.iterators = []
        layout = QtWidgets.QVBoxLayout()
        self.pbar = QtWidgets.QProgressBar()
        self.pbar.setTextVisible(True)
        self.text = QtWidgets.QLabel('stopped')
        layout.addWidget(self.pbar)
        layout.addWidget(self.text)
        self.setLayout(layout)
        
    
    def reset(self):
        self.vars = []
        self.iterators = []
        self.text.setText('stopped')

    def call_iter(self, iterable):
        try:
            max_val = len(iterable)
        except TypeError:
            max_val = '?'

        self.iterators.append(iter(iterable))
        self.vars.append({'val':0, 'max':max_val, 'start':time.time(), 'last':time.time(), 'avg':0, 'tot':0, 'rem':'?', 'per':0})

        if max_val != '?':
            self.pbar.setValue(0)
            self.pbar.setRange(0, max_val)

    def call_next(self):
        try:
            next(self.iterators[-1])
            self.vars[-1]['val'] += 1
            t = time.time()
            self.vars[-1]['avg'] = t-self.vars[-1]['last']
            self.vars[-1]['last'] = t
            self.vars[-1]['tot'] = t-self.vars[-1]['start']
            self.vars[-1]['per'] = 100*self.vars[-1]['val']/self.vars[-1]['max']
            self.vars[-1]['rem'] = (self.vars[-1]['max'] - self.vars[-1]['val'])*self.vars[-1]['avg']

            if self.vars[-1]['max'] != '?':
                self.pbar.setValue(self.vars[-1]['val'])
                self.pbar.setRange(0, self.vars[-1]['max'])
            self.text.setText('\t'.join(['[{per:.0f}% {val:.0f}/{max:.0f} [{tot:.0f}s<{rem:.0f}s] {avg:.2f}s/it ]'.format(**d) for d in self.vars]))
            QtWidgets.QApplication.processEvents()
        except StopIteration:
            self.vars = self.vars[:-1]
            if not self.vars == [] and self.vars[-1]['max'] != '?':
                self.pbar.setValue(self.vars[-1]['max'])
                self.pbar.setRange(0, self.vars[-1]['max'])
                QtWidgets.QApplication.processEvents()
            self.iterators = self.iterators[:-1]

    # def update(self, iterator):

class Spyrelet_Launcher_Widget(QtWidgets.QWidget):
    def __init__(self, spyrelet, parent=None):
        self.spyrelet = spyrelet
        self.progress_bar = Progress_Bar()
        self.launcher = Spyrelet_Launcher(spyrelet)
        self.param_w = ParamWidget(self.launcher.params)
        self.param_w.set(**self.launcher.get_defaults())
        super().__init__(parent=parent)

        #Build ctrl pannel
        ctrl_pannel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        self.run_btn = QtWidgets.QPushButton('Run')
        self.set_defaults_btn = QtWidgets.QPushButton('Set Defaults')
        self.save_btn = QtWidgets.QPushButton('Save')
        layout.addWidget(self.run_btn)
        layout.addWidget(self.save_btn)
        ctrl_pannel.setLayout(layout)

        #Build main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(ctrl_pannel)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.param_w)
        layout.addStretch()
        self.setLayout(layout)

        #Connect signal
        self.run_btn.clicked.connect(self.run)
        self.set_defaults_btn.clicked.connect(self.set_defaults)
        self.save_btn.clicked.connect(self.save_data)

        self.run_thread = None
        

    def run(self):
        if self.run_thread is None or self.run_thread.isFinished():
            self.progress_bar.reset()
            param_dict = self.param_w.get()
            self.run_thread = Spyrelet_Run_Thread(self.launcher, param_dict)
            self.run_thread.start()
            self.run_btn.setText('Stop')
            self.run_thread.finished.connect(lambda: self.run_btn.setText('Run'))
            self.run_thread.progressed_iter.connect(self.progress_bar.call_iter)
            self.run_thread.progressed_next.connect(self.progress_bar.call_next)
        else:
            self.run_thread.stop_requested.emit()

    def set_defaults(self):
        self.spyrelet.set_defaults(**self.param_w.get())

    def save_data(self):
        self.save_w = Save_Widget(self.spyrelet)
        self.save_w.show()

class Spyrelet_Run_Thread(QtCore.QThread):
    """Qt Thread which monitors for changes to qither a collection or a database and emits a signal when something happens"""
    progressed_iter = QtCore.pyqtSignal(object) #This will be emitted when iter is called on progress is called in the spyrelet
    progressed_next = QtCore.pyqtSignal() #This will be emitted when next is called on progress is called in the spyrelet
    stop_requested = QtCore.pyqtSignal() # This will be emitted externally to stop the execution of a spyrelet prematurly
    def __init__(self, launcher, param_dict):
        super().__init__()
        self.param_dict = param_dict
        self.launcher = launcher
        self.spyrelet = self.launcher.spyrelet
        class Progress_Iter():
            def __init__(_self, iterable):
                _self.iterable = iterable
            def __iter__(_self):
                self.progressed_iter.emit(_self.iterable)
                _self.iterable = iter(_self.iterable)
                return _self
            def __next__(_self):
                self.progressed_next.emit()
                return next(_self.iterable)


        self.progress = Progress_Iter
        self.stop_requested.connect(self.stop_run)

    def progress(self, iterator):
        for x in iterator:
            self.progressed.emit(iterator)
            yield x

    def run(self):
        self.launcher.run(progress=self.progress, **self.param_dict)

    def stop_run(self):
        self.spyrelet.stop()


class Combined_Launcher(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        layout = QtWidgets.QVBoxLayout()
        self.selector = QtWidgets.QComboBox()
        container = QtWidgets.QWidget()
        layout.addWidget(self.selector)
        layout.addWidget(container)

        self.setLayout(layout)


        #Create the launchers
        cfg = get_configs()
        names = list(cfg['experiment_list'].keys())
        names.sort(key=lambda x: len(cfg['experiment_list'][x][2]))
        self.launchers = dict()
        last_len = -1
        while last_len != len(self.launchers):
            last_len = len(self.launchers)
            for sname in names:
                sclass, devs, subs = cfg['experiment_list'][sname]
                print(sname, all([x in self.launchers for x in list(subs.values())]))
                if not sname in self.launchers and all([x in self.launchers for x in list(subs.values())]):
                    try:
                        sclass = get_class_from_str(sclass)
                        subs = {real_name:self.launchers[alias].spyrelet for real_name,alias in subs.items()}
                        s = sclass(sname, spyrelets=subs, device_alias=devs)
                        self.launchers[sname] = Spyrelet_Launcher_Widget(s)
                    except:
                        print("Could not instanciate launcher for spyrelet {}...".format(sname))
                        traceback.print_exc()

        #Add to layout
        layout = QtWidgets.QStackedLayout()
        container.setLayout(layout)
        names = list(self.launchers.keys())
        names.sort()
        for n in names:
            layout.addWidget(self.launchers[n])

        self.selector.addItems(names)
        self.container_layout = layout
        
        self.selector.currentTextChanged.connect(self.change_widget)

    def change_widget(self, name):
        self.container_layout.setCurrentWidget(self.launchers[name])
        # self.container_layout.

if __name__=='__main__':
    from nspyre.widgets.app import NSpyreApp
    app = NSpyreApp([])
    w = Combined_Launcher()
    w.show()
    app.exec_()
        

    