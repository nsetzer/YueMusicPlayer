
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.explorer.source import DirectorySource
from yue.core.settings import Settings
from yue.qtcommon.explorer.display import ExplorerModel
from yue.qtcommon.explorer.filetable import ExplorerFileTable
from yue.qtcommon.ResourceManager import ResourceManager
from yue.explor.assoc import FileAssoc
from yue.core.explorer.zipfs import ZipFS,isArchiveFile

import subprocess, shlex
import os,sys

from yue.explor.util import proc_exec

def fileIsBinary(view,path):
    """
    open the file and read some bytes
    guess if it is actually a text file or not.

    return true if it looks like a binary file
    """
    with view.open(path,"rb") as rf:
        buf = rf.read(1024)

        if b'\x00' in buf:
            return True

        try:
            buf.decode("utf-8")
        except UnicodeDecodeError:
            return True

    return False;

class EditLinkDialog(QDialog):
    """docstring for EditLinkDialog"""
    def __init__(self, view, path, parent=None):
        super(EditLinkDialog, self).__init__(parent)
        self.view = view
        self.path = path

        self.setWindowTitle("Edit Link")
        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,0,16,0)

        self.grid = QGridLayout()

        self.btn_accept = QPushButton("Save",self)
        self.btn_cancel = QPushButton("Cancel",self)

        target = view.readlink(path)
        self.edit_target = QLineEdit(target,self)


        self.grid.addWidget(QLabel("Link Name:"),0,0)
        self.grid.addWidget(QLabel(view.split(path)[1]),0,1)
        self.grid.addWidget(QLabel("Target:"),1,0)
        self.grid.addWidget(self.edit_target,1,1)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.hbox_btns = QHBoxLayout()
        self.hbox_btns.addStretch(1)
        self.hbox_btns.addWidget(self.btn_cancel)
        self.hbox_btns.addWidget(self.btn_accept)

        self.vbox.addLayout(self.grid)
        self.vbox.addLayout(self.hbox_btns)

    def text(self):
        return self.edit_target.text()

def mklink(view,path,target):

    try:
        st = view.stat(path)

        # if it exists and is not a link
        if not st['isLink']:
            raise Exception("EEXISTS %s"%st)

        # remove the existing link
        if st['isLink']>0:
            # TODO bypass the view cache, where delete would remove
            # the item from the cache,
            # the whole caching thing needs to be rethought
            view.source.delete(path)

    except FileNotFoundError as e:
        pass # if it doesnt exist, just create the link

    view.mklink(target,path)

class ExplorModel(ExplorerModel):
    # TODO rename ExplorerModel / ExplorModel to
    # ExplorDisplay, to prevent confusion
    # a Display is a model/view into single directory


    openAsTab = pyqtSignal(object,str)  # view, path
    openRemote = pyqtSignal(object,str) # model, path

    def _getNewFileTable(self,view):
        tbl = ExplorerFileTable(view,self)
        tbl.showColumnHeader( True )
        tbl.showRowHeader( False )
        tbl.setLastColumnExpanding( False )

        tbl.renamePaths.connect(self.action_rename)
        tbl.createFile.connect(self.action_touch)
        tbl.createDirectory.connect(self.action_mkdir)

        return tbl

    def action_edit(self,item):

        path = self.view.realpath(item['name'])

        if self.view.isdir(path):
            pwd = path
        else:
            pwd,_ = self.view.split(path)

        if FileAssoc.isImage(path):
            cmdstr = Settings.instance()['cmd_edit_image']
            proc_exec(cmdstr%(path),pwd)
        else: #if FileAssoc.isText(path):

            cmdstr = Settings.instance()['cmd_edit_text']
            proc_exec(cmdstr%(path),pwd)


    def action_edit_link(self,item):

        if self.view.islocal():
            pass
        path = self.view.realpath(item['name'])

        dlg = EditLinkDialog(self.view,path,self)
        if dlg.exec_():
            mklink(self.view,path,dlg.text())

    def action_openas(self, cmdstr_base, item):
        path = self.view.realpath(item['name'])
        if self.view.isdir(path):
            return
        pwd,_ = self.view.split(path)
        proc_exec(cmdstr_base%(path),pwd)

    def action_openas_audio(self,item):
        return self.action_openas(Settings.instance()['cmd_play_audio'], item)

    def action_openas_video(self,item):
        return self.action_openas(Settings.instance()['cmd_play_video'], item)

    def action_open_term(self):

        cmdstr = Settings.instance()['cmd_launch_terminal']
        path = self.view.pwd()
        print(cmdstr)
        os.system(cmdstr%path)

    def action_open_file(self, item):
        path = self.view.realpath(item['name'])

        if not self.view.isOpenSupported():
            # not local, but supports get/put api
            if self.view.isGetPutSupported():
                return self._action_open_file_remote(path)
        elif self.view.islocal():
            return self._action_open_file_local(self.view,path)

        QMessageBox.critical(None,"Error","open not supported")

    def _action_open_file_remote(self,path):

        self.openRemote.emit(self,path)

    def _action_open_file_local(self,view,path):
        cmdstr_img = Settings.instance()['cmd_edit_image']

        if view.isdir(path):
            pwd = path
        else:
            pwd,_ = view.split(path)

        if isArchiveFile(path):
            self.openAsTab.emit(view,path)

        elif FileAssoc.isImage(path) and cmdstr_img:
            proc_exec(cmdstr_img%(path),pwd)
        elif FileAssoc.isText(path):
            cmdstr = Settings.instance()['cmd_edit_text']
            proc_exec(cmdstr%(path),pwd)
        elif FileAssoc.isAudio(path):
            cmdstr = Settings.instance()['cmd_play_audio']
            proc_exec(cmdstr%(path),pwd)
        elif FileAssoc.isMovie(path):
            cmdstr = Settings.instance()['cmd_play_video']
            proc_exec(cmdstr%(path),pwd)
        elif not fileIsBinary(view,path):
            cmdstr = Settings.instance()['cmd_edit_text']
            proc_exec(cmdstr%(path),pwd)
        else:
            cmdstr = Settings.instance()['cmd_open_native']
            proc_exec(cmdstr%(path),pwd)

    def action_open_directory(self):
        # open the cwd in explorer
        cmdstr = Settings.instance()['cmd_open_native']
        path = self.view.pwd()
        print(cmdstr)
        print("--")
        os.system(cmdstr%path)


















