from PyQt5 import QtWidgets
import time
from nspyre.gui.data_handling import save_data

class Save_Widget(QtWidgets.QWidget):

    def __init__(self, spyrelet, parent=None):
        super().__init__(parent=parent)
        self.spyrelet = spyrelet
        self.filename = None
        self.init_ui()
        return

    def init_ui(self):
        # Create file selection widget
        file_w = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        file_w.setLayout(layout)
        self.filename_label = QtWidgets.QLabel('No filename currently selected')
        self.select_repository = QtWidgets.QPushButton('Select repository...')
        self.select_repository.clicked.connect(self.select_repository_dialog)
        layout.addWidget(self.select_repository)
        layout.addWidget(self.filename_label)

        # Entry widget
        entry_w = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        entry_w.setLayout(layout)
        label = QtWidgets.QLabel('Entry name: ')
        self.dataset_name = QtWidgets.QLineEdit()
        layout.addWidget(label)
        layout.addWidget(self.dataset_name)
        self.dataset_name.setText(self.spyrelet.__class__.__name__)

        # Other widget
        self.dataset_description = QtWidgets.QTextEdit()
        self.save_btn = QtWidgets.QPushButton('Save')
        self.save_btn.clicked.connect(self.save)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Save widget for {}'.format(self.spyrelet.name)))
        layout.addWidget(file_w)
        layout.addWidget(entry_w)
        layout.addWidget(QtWidgets.QLabel('Description:'))
        layout.addWidget(self.dataset_description)
        layout.addWidget(self.save_btn)
        self.setLayout(layout)
        return

    def select_repository_dialog(self):
        filename, other = QtWidgets.QFileDialog.getSaveFileName(None, 'Save spyrelet to...', '', 'JSON files (*.json)')
        self.filename = filename
        self.filename_label.setText(filename)
        return

    def save(self):
        description = self.dataset_description.toPlainText()
        name = self.dataset_name.text()
        if self.filename:
            save_data(self.spyrelet, self.filename, name=name, description=description)
            print('Data for {} was saved under {}'.format(self.spyrelet.name, self.filename))
        return