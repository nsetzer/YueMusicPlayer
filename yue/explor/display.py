
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.settings import Settings
from yue.client.widgets.explorer.display import ExplorerModel
from yue.client.widgets.explorer.filetable import ResourceManager, ExplorerFileTable
from yue.explor.assoc import FileAssoc

import subprocess, shlex

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
            cmd=cmdstr%(path)
            args=shlex.split(cmd)
            print(args)
            subprocess.Popen(args)

        else: #if FileAssoc.isText(path):

            cmdstr = Settings.instance()['cmd_edit_text']
            cmd=cmdstr%(path)
            args=shlex.split(cmd)
            print(args)
            subprocess.Popen(args)

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
        else:
            cmdstr = Settings.instance()['cmd_open_native']
            cmd=cmdstr%(path)
            args=shlex.split(cmd)
            print(args)
            subprocess.Popen(args)

    def action_open_directory(self):
        # open the cwd in explorer
        cmdstr = Settings.instance()['cmd_open_native']
        path = self.view.pwd()
        print(cmdstr)
        print("--")
        os.system(cmdstr%path)