
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class SettingsDialog(QDialog):
    """docstring for SettingsDialog"""
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,8,16,8)

        self.grid = QGridLayout()

        self.edit_tools =[]
        for i,(s,n) in enumerate([ ("cmd_edit_text","Text Editor"),
                                   ("cmd_edit_image","Image Editor"),
                                   ("cmd_open_native","Open Native"),
                                   ("cmd_launch_terminal","Open Terminal"),
                                   ("cmd_diff_files","Diff Tool"),
                                   ("cmd_vagrant","Vagrant Binary")]):
            edit = QLineEdit(self)
            edit.setText(Settings.instance()[s])
            edit.setCursorPosition(0)
            self.grid.addWidget(QLabel(n,self),i,0)
            self.grid.addWidget(edit,i,1)

        self.btn_accept = QPushButton("Save",self)
        self.btn_cancel = QPushButton("Cancel",self)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.hbox_btns = QHBoxLayout()
        self.hbox_btns.setContentsMargins(0,0,0,0)
        self.hbox_btns.addStretch(1)
        self.hbox_btns.addWidget(self.btn_accept)
        self.hbox_btns.addWidget(self.btn_cancel)

        self.vbox.addLayout(self.grid)
        self.vbox.addLayout(self.hbox_btns)
