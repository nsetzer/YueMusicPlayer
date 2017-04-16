
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.LargeTable import LargeTable
from yue.client.widgets.TableEditColumn import EditColumn

class SshSessionsTable(LargeTable):
    """
    """

    def __init__(self, parent=None):
        super(SshSessionsTable,self).__init__(parent)

    def initColumns(self):

        self.columns.append( EditColumn(self,'name',"Session Name") )
        self.columns[-1].setWidthByCharCount(35)

class SshCredentialsDialog(QDialog):
    """docstring for SettingsDialog"""
    def __init__(self, parent=None):
        super(SshCredentialsDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,8,16,8)

        self.grid = QGridLayout()

        i=1

        self.cbox_proto = QComboBox(self)
        self.lbl_proto = QLabel("Protocol:",self)
        self.lbl_proto.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_proto,i,0)
        self.grid.addWidget(self.cbox_proto,i,1,1,4)
        i+=1

        self.edit_host = QLineEdit(self)
        self.spbx_port = QSpinBox(self)
        self.spbx_port.setRange(0,65536)
        self.spbx_port.setValue(22)
        self.lbl_server = QLabel("Server:",self)
        self.lbl_server.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_server,i,0)
        self.grid.addWidget(self.edit_host,i,1,1,2)
        self.lbl_port = QLabel("Port:",self)
        self.lbl_port.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_port,i,3)
        self.grid.addWidget(self.spbx_port,i,4,)
        i+=1

        self.lbl_url = QLabel("ssh://",self)
        self.lbl_url_ = QLabel("URL:",self)
        self.lbl_url_.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_url_,i,0)
        self.grid.addWidget(self.lbl_url,i,1)
        i+=1

        self.edit_user = QLineEdit(self)
        self.lbl_user = QLabel("User Name:",self)
        self.lbl_user.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_user,i,0)
        self.grid.addWidget(self.edit_user,i,1,1,2)
        i+=1

        self.edit_pass = QLineEdit(self)
        self.lbl_pass = QLabel("Password:",self)
        self.lbl_pass.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_pass,i,0)
        self.grid.addWidget(self.edit_pass,i,1,1,2)
        i+=1

        self.edit_ikey = QLineEdit(self)
        self.lbl_ikey = QLabel("Private Key:",self)
        self.lbl_ikey.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_ikey,i,0)
        self.grid.addWidget(self.edit_ikey,i,1,1,4)
        i+=1

        self.btn_save = QPushButton("Save",self)
        self.grid.addWidget(self.btn_save,i,4)
        i+=1

        self.tbl_save = SshSessionsTable(self)

        self.cbox_proto.addItem("SSH")
        self.cbox_proto.addItem("FTP")

        self.btn_accept = QPushButton("Connect",self)
        self.btn_cancel = QPushButton("Cancel",self)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.hbox_btns = QHBoxLayout()
        self.hbox_btns.setContentsMargins(0,0,0,0)
        self.hbox_btns.addStretch(1)
        self.hbox_btns.addWidget(self.btn_accept)
        self.hbox_btns.addWidget(self.btn_cancel)

        self.vbox.addLayout(self.grid)
        self.vbox.addWidget(self.tbl_save.container)
        self.vbox.addLayout(self.hbox_btns)

    def setConfig(self,cfg):

        if "proto" in cfg:
            index = self.cbox_proto.findText(cfg['proto'])
            self.cbox_proto.setCurrentIndex(index)

        if "host" in cfg:
            self.edit_host.setText(cfg['host'])
        if "port" in cfg:
            self.spbx_port.setText(cfg['port'])
        if "user" in cfg:
            self.edit_user.setText(cfg['user'])
        if "password" in cfg:
            self.edit_pass.setText(cfg['password'])
        if "key" in cfg:
            self.edit_ikey.setText(cfg['key'])

    def getConfig(self):

        cfg = {}
        cfg['proto'] = self.cbox_proto.currentText()

        cfg['host'] = self.edit_host.strip().text()
        cfg['port'] = self.spbx_port.strip().value()
        # user/pass I will take literally incase whitespace is significant
        cfg['user'] = self.edit_user.text()
        cfg['password'] = self.edit_pass.text() or None
        cfg['key'] = self.edit_ikey.text().strip() or None
        return cfg
