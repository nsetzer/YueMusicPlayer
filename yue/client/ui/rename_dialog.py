#! python34 $this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

import yue
from yue.client.widgets.LineEdit import LineEdit

class RenameDialog(QDialog):

    def __init__(self,text='',title='Rename', prompt='', parent=None):

        super(RenameDialog,self).__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 50)

        hbox = QHBoxLayout();
        vbox = QVBoxLayout(self);
        self.edit = LineEdit()

        self.btna = QPushButton("Accept")
        self.btnc = QPushButton("Cancel")

        hbox.addWidget(self.btnc)
        hbox.addWidget(self.btna)

        vbox.addWidget(self.edit)


        if len(prompt) > 0:
            vbox.addWidget(QLabel(prompt))

        vbox.addLayout(hbox)

        self.btna.clicked.connect(self.accept)
        self.btnc.clicked.connect(self.reject)
        self.edit.returnPressed.connect(self.accept)

        self.edit.setText(text)

    def text(self):
        return self.edit.text()