
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


















