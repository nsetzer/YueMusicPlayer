
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.settings import Settings
from yue.client.widgets.explorer.display import ExplorerModel
from yue.client.widgets.explorer.filetable import ResourceManager, ExplorerFileTable
from yue.explor.assoc import FileAssoc
from yue.core.explorer.zipfs import ZipFS,isArchiveFile

import subprocess, shlex

def proc_exec(cmdstr):
    args=shlex.split(cmdstr)
    print(args)
    subprocess.Popen(args)

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

        if FileAssoc.isImage(path):
            cmdstr = Settings.instance()['cmd_edit_image']
            proc_exec(cmdstr%(path))

        else: #if FileAssoc.isText(path):

            cmdstr = Settings.instance()['cmd_edit_text']
            proc_exec(cmdstr%(path))


    def action_edit_link(self,item):

        if self.view.islocal():
            pass
        path = self.view.realpath(item['name'])

        dlg = EditLinkDialog(self.view,path,self)
        if dlg.exec_():
            mklink(self.view,path,dlg.text())

    def action_open_term(self):

        cmdstr = Settings.instance()['cmd_launch_terminal']
        path = self.view.pwd()
        print(cmdstr)
        os.system(cmdstr%path)

    def action_open_file(self, item):
        path = self.view.realpath(item['name'])

        print("open path",path)
        if isArchiveFile(path):
            self.openAsTab.emit(self.view,path)

        elif FileAssoc.isImage(path):
            cmdstr = Settings.instance()['cmd_edit_image']
            proc_exec(cmdstr%(path))
        elif FileAssoc.isText(path):
            cmdstr = Settings.instance()['cmd_edit_text']
            proc_exec(cmdstr%(path))
        elif not fileIsBinary(self.view,path):
            cmdstr = Settings.instance()['cmd_edit_text']
            proc_exec(cmdstr%(path))
        else:
            cmdstr = Settings.instance()['cmd_open_native']
            proc_exec(cmdstr%(path))

    def action_open_directory(self):
        # open the cwd in explorer
        cmdstr = Settings.instance()['cmd_open_native']
        path = self.view.pwd()
        print(cmdstr)
        print("--")
        os.system(cmdstr%path)


















