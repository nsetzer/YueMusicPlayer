
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.qtcommon.LargeTable import LargeTable
from yue.qtcommon.TableEditColumn import EditColumn

from yue.explor.ymlsettings import YmlSettings

class SshSessionsTable(LargeTable):
    """
    """
    updateConfig = pyqtSignal(dict);

    def __init__(self, parent=None):
        super(SshSessionsTable,self).__init__(parent)

    def initColumns(self):

        self.columns.append( EditColumn(self,'name',"Session Name") )
        self.columns[-1].setWidthByCharCount(35)

    def mouseDoubleClick(self,row,col,event=None):

        if 0 <= row < len(self.data):
            self.updateConfig.emit( self.data[row] )

class SshCredentialsDialog(QDialog):
    """docstring for SettingsDialog"""
    def __init__(self, parent=None):
        super(SshCredentialsDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,8,16,8)

        self.grid = QGridLayout()

        i=0

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

        self.edit_sshcfg = QLineEdit(self)
        self.edit_sshcfg.setText("~/.ssh/config")
        self.lbl_sshcfg = QLabel("SSH Config:",self)
        self.lbl_sshcfg.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.grid.addWidget(self.lbl_sshcfg,i,0)
        self.grid.addWidget(self.edit_sshcfg,i,1,1,4)
        i+=1

        self.edit_name = QLineEdit(self)
        self.edit_name.setPlaceholderText("Name")
        self.btn_save = QPushButton("Save",self)
        self.btn_save.clicked.connect(self.saveCurrentConfig)
        self.grid.addWidget(self.edit_name,i,1,1,3)
        self.grid.addWidget(self.btn_save,i,4)
        i+=1

        self.tbl_save = SshSessionsTable(self)
        self.tbl_save.updateConfig.connect(self.setConfig)
        profiles = YmlSettings.instance().data["remote"]["profiles"]
        self.tbl_save.setData(profiles)

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

        self.resize(512,480)

    def setConfig(self,cfg):

        if "protocol" in cfg:
            index = self.cbox_proto.findText(cfg['protocol'])
            self.cbox_proto.setCurrentIndex(index)

        if "name" in cfg:
            self.edit_name.setText(cfg['name'])

        if "hostname" in cfg:
            self.edit_host.setText(cfg['hostname'])
        if "port" in cfg:
            self.spbx_port.setValue(cfg['port'])
        if "username" in cfg:
            self.edit_user.setText(cfg['username'])
        if "password" in cfg:
            self.edit_pass.setText(cfg['password'])
        if "private_key" in cfg:
            self.edit_ikey.setText(cfg['private_key'])
        if "config" in cfg:
            self.edit_sshcfg.setText(cfg['config'])

    def getConfig(self):

        cfg = {}
        cfg['protocol'] = self.cbox_proto.currentText()
        cfg['name'] = self.edit_name.text();

        cfg['hostname'] = self.edit_host.text().strip()
        cfg['port'] = self.spbx_port.value()
        # user/pass I will take literally incase whitespace is significant
        cfg['username'] = self.edit_user.text()
        cfg['password'] = self.edit_pass.text() or None
        cfg['private_key'] = self.edit_ikey.text().strip() or None
        cfg['config'] = self.edit_sshcfg.text().strip() or None

        return cfg

    def saveCurrentConfig(self):

        """
            save the current config so that it can be reloaded later
            update the yml settings to persist the data
            refresh the table to reflect changes

            update a config if the name matches, otherwise append to the
            end of the list.
        """
        cfg = self.getConfig();

        if cfg["name"] == "":
            # todo, must have a name, show a message box error
            return

        # TODO: bug in yml prevents this list from having length 0 or 1.
        profiles = YmlSettings.instance().data["remote"]["profiles"]
        for i,profile in enumerate(profiles):
            if profile["name"] == cfg["name"]:
                profiles[i] = cfg
                break;
        else:
            profiles.append(cfg)

        self.tbl_save.setData(profiles)

        YmlSettings.instance().save()


