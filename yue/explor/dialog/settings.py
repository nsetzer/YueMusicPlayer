
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.settings import Settings
from yue.qtcommon.Tab import TabWidget,Tab

class SettingsDialog(QDialog):
    """docstring for SettingsDialog"""
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,8,16,8)

        self.tabview = TabWidget(self)
        self.initEditTab()
        self.initFileAssocTab()

        self.btn_accept = QPushButton("Save",self)
        self.btn_cancel = QPushButton("Cancel",self)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.hbox_btns = QHBoxLayout()
        self.hbox_btns.setContentsMargins(0,0,0,0)
        self.hbox_btns.addStretch(1)
        self.hbox_btns.addWidget(self.btn_accept)
        self.hbox_btns.addWidget(self.btn_cancel)

        self.vbox.addWidget(self.tabview)
        self.vbox.addLayout(self.hbox_btns)

        self.resize(640,-1)

    def initEditTab(self):

        self.tab_edit = Tab(self)
        self.tabview.addTab(self.tab_edit,"Edit Tools")
        self.edit_grid = QGridLayout(self.tab_edit)

        self.edit_info = [("cmd_edit_text","Text Editor"),
                         ("cmd_edit_image","Image Editor"),
                         ("cmd_open_native","Open Native"),
                         ("cmd_launch_terminal","Open Terminal"),
                         ("cmd_diff_files","Diff Tool"),
                         ("cmd_vagrant","Vagrant Binary")]
        self.edit_tools =[]
        for i,(s,n) in enumerate(self.edit_info):
            edit = QLineEdit(self)
            edit.setText(Settings.instance()[s])
            edit.setCursorPosition(0)
            lbl = QLabel(n+":",self)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.edit_grid.addWidget(lbl,i,0)
            self.edit_grid.addWidget(edit,i,1)
            self.edit_tools.append(edit)


    def initFileAssocTab(self):

        self.tab_assoc = Tab(self)
        self.tabview.addTab(self.tab_assoc,"File Association")
        self.assoc_grid = QGridLayout(self.tab_assoc)
        self.assoc_info = [("ext_text","Text Files"),
                            ("ext_archive","Archive Files"),
                            ("ext_image","Image Files"),
                            ("ext_movie","Video Files"),
                            ("ext_document","Document Files")]
        self.assoc_tools = []

        for i,(s,n) in enumerate(self.assoc_info):
            print(i,s,n)
            edit = QLineEdit(self)
            terms = []
            for term in Settings.instance()[s]:
                if term.startswith("."):
                    term = term[1:]
                terms.append(term)
            terms_s =', '.join(terms)
            edit.setText(terms_s)
            edit.setCursorPosition(0)
            lbl = QLabel(n+":",self)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.assoc_grid.addWidget(lbl,i,0)
            self.assoc_grid.addWidget(edit,i,1)
            self.assoc_tools.append(edit)

    def accept(self):

        data = {}
        for t,(s,n) in zip(self.edit_tools,self.edit_info):
            data[s] = t.text()
            print(s)
        Settings.instance().setMulti(data,True)

        super(SettingsDialog, self).accept()
