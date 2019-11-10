from PyQt5 import QtWidgets, QtCore
from nspyre.spyrelet import Spyrelet_Launcher
from nspyre.widgets.param_widget import ParamWidget
from nspyre.utils import RangeDict
import time

class Progress_Bar(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vars = []
        layout = QtWidgets.QVBoxLayout()
        self.pbar = QtWidgets.QProgressBar()
        self.pbar.setTextVisible(True)
        self.text = QtWidgets.QLabel('stopped')
        layout.addWidget(self.pbar)
        layout.addWidget(self.text)
        self.setLayout(layout)
    
    def reset(self):
        self.vars = []
        self.text.setText('stopped')

    def update(self, iterator):
        try:
            max_val = len(iterator)
        except TypeError:
            max_val = '?'

        self.vars.append({'val':0, 'max':max_val, 'start':time.time(), 'last':time.time(), 'avg':0, 'tot':0, 'rem':'?', 'per':0})
        if max_val != '?':
            self.pbar.setValue(0)
            self.pbar.setRange(0, max_val)

        for i,x in enumerate(iterator):
            try:
                self.vars[-1]['val'] += 1
                t = time.time()
                self.vars[-1]['avg'] = t-self.vars[-1]['last']
                self.vars[-1]['last'] = t
                self.vars[-1]['tot'] = t-self.vars[-1]['start']
                self.vars[-1]['per'] = 100*self.vars[-1]['val']/self.vars[-1]['max']
                self.vars[-1]['rem'] = (self.vars[-1]['max'] - self.vars[-1]['val'])*self.vars[-1]['avg']

                if max_val != '?':
                    self.pbar.setValue(i)
                    self.pbar.setRange(0, max_val)
                self.text.setText('\t'.join(['[{per:.0f}% {val:.0f}/{max:.0f} [{tot:.0f}s<{rem:.0f}s] {avg:.2f}s/it ]'.format(**d) for d in self.vars]))
                QtWidgets.QApplication.processEvents()
            except:
                pass
            finally:
                yield x
        self.vars = self.vars[:-1]
        if max_val != '?' and not self.vars == []:
            self.pbar.setValue(self.vars[-1]['max'])
            self.pbar.setRange(0, self.vars[-1]['max'])
            QtWidgets.QApplication.processEvents()

class Spyrelet_Launcher_Widget(QtWidgets.QWidget):
    def __init__(self, spyrelet, parent=None):
        self.spyrelet = spyrelet
        self.progress_bar = Progress_Bar()
        self.spyrelet.progress = self.progress_bar.update
        self.launcher = Spyrelet_Launcher(spyrelet)
        self.param_w = ParamWidget(self.launcher.params)
        self.param_w.set(**self.launcher.default_params)
        super().__init__(parent=parent)

        #Build ctrl pannel
        ctrl_pannel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        run_btn = QtWidgets.QPushButton('Run')
        # progress_bar = QtWidgets.QLabel('Progress bar in construction')#@TODO add progress bar
        layout.addWidget(run_btn)
        layout.addWidget(self.progress_bar)
        ctrl_pannel.setLayout(layout)

        #Build main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(ctrl_pannel)
        layout.addWidget(self.param_w)
        self.setLayout(layout)
        self.running = False

        #Connect signal
        run_btn.clicked.connect(self.run)

    def run(self):
        self.progress_bar.reset()
        if not self.running:
            self.running = True
            params_dict = self.param_w.get()
            self.launcher.run(params_dict)
            self.running = False
        else:
            #Stop the run
            self.running = False
            self.spyrelet.stop()
        
    