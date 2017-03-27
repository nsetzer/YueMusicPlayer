#! python35 ../../../test/test_client.py $this

import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback

from yue.client.widgets.Tab import Tab

from yue.client.widgets.explorer.controller import ExplorerController
from yue.client.widgets.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, \
    DropRequestJob, Dashboard
from yue.client.widgets.explorer.source import LazySourceListView
from yue.client.widgets.explorer.filetable import ResourceManager, ExplorerFileTable
from yue.client.widgets.explorer.display import ExplorerModel

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library

from yue.client.ui.ingest_dialog import IngestProgressDialog
from yue.client.ui.movefile_dialog import MoveFileProgressDialog
from yue.client.ui.rename_dialog import RenameDialog
from yue.core.explorer.source import DirectorySource,SourceListView
from yue.core.explorer.ftpsource import parseFTPurl, FTPSource

def explorerOpen( url ):

    if os.name == "nt":
        os.startfile(url);
    elif sys.platform == "darwin":
        os.system("open %s"%url);
    else:
        # could also use kde-open, gnome-open etc
        # TODO: implement code that tries each one until one works
        #subprocess.call(["xdg-open",filepath])
        sys.stderr.write("open unsupported on %s"%os.name)

class YueExplorerModel(ExplorerModel):

    do_ingest = pyqtSignal(list) # list of absolute paths

    def __init__(self, view, controller, parent=None):
        super(YueExplorerModel, self).__init__(view, controller, parent)

        self.list_library_files = set()

        self.brush_library = self.tbl_file.addRowHighlightComplexRule( self.indexInLibrary , QColor(128,128,224))

    def _getNewFileTable(self,view):
        tbl =  ExplorerFileTable(view,self)
        tbl.showColumnHeader( True )
        tbl.showRowHeader( False )
        tbl.setLastColumnExpanding( False )

        tbl.renamePaths.connect(self.action_rename)
        tbl.createFile.connect(self.action_touch)
        tbl.createDirectory.connect(self.action_mkdir)
        return tbl

    def indexInLibrary(self,idx):
        return self.view[idx]['name'].lower() in self.list_library_files

    def action_ingest(self,items):
        paths = [ self.view.realpath(item['name']) for item in items ]
        self.do_ingest.emit( paths )

    def canIngest( self ):
        return self.controller.dialog is None

    def supportedExtension(self,ext):
        return ext in Song.supportedExtensions()

    def item2img(self,item):

        l = ResourceManager.LINK if item['isLink'] else 0
        if item['isDir']:
            return ResourceManager.instance().get(l|ResourceManager.DIRECTORY)

        _,ext = self.view.splitext(item['name'])
        return ResourceManager.instance().get(l|ResourceManager.instance().getExtType(ext))

    def onLoadComplete(self,data):
        super().onLoadComplete(data)

        songs = Library.instance().searchDirectory(self.view.pwd(),False)
        self.list_library_files = set( self.view.split(song[Song.path])[1].lower() \
                                       for song in songs )

    def action_open_directory(self):
        # open the cwd in explorer
        explorerOpen( self.view.pwd() )

class ExplorerView(Tab):
    """docstring for ExplorerView"""

    play_file = pyqtSignal(str)
    ingest_finished = pyqtSignal()

    primaryDirectoryChanged = pyqtSignal(str)
    secondaryDirectoryChanged = pyqtSignal(str)

    submitJob = pyqtSignal(Job)


    def __init__(self, parent=None):
        super(ExplorerView, self).__init__(parent)

        self.controller = ExplorerController( )

        self.source = DirectorySource()

        self.dashboard = Dashboard(self)

        self.ex_main = YueExplorerModel( None, self.controller, self )
        self.ex_secondary = YueExplorerModel( None, self.controller, self )
        self.ex_secondary.btn_split.setIcon(QIcon(":/img/app_join.png"))

        self.ex_main.toggleSecondaryView.connect(self.onToggleSecondaryView)
        self.ex_secondary.toggleSecondaryView.connect(self.onToggleSecondaryView)

        self.ex_main.directoryChanged.connect(self.primaryDirectoryChanged)
        self.ex_secondary.directoryChanged.connect(self.secondaryDirectoryChanged)

        self.ex_main.showSplitButton(True)
        self.ex_secondary.hide()

        self.hbox = QHBoxLayout()
        self.hbox.setContentsMargins(0,0,0,0)
        self.hbox.addWidget(self.ex_main)
        self.hbox.addWidget(self.ex_secondary)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.vbox.addLayout(self.hbox)
        self.vbox.addWidget(self.dashboard)

    def onEnter(self):

        # delay creating the views until the tab is entered for the first
        # time, this slightly improves startup performance
        print("on enter yue",self.ex_main.view)
        if (self.ex_main.view is None):
            view1 = LazySourceListView(self.source,self.source.root())
            view2 = LazySourceListView(self.source,self.source.root())

            # this is a hack, source views are currently in flux
            view1.chdir(view1.pwd())
            view2.chdir(view2.pwd())

            view1.loadDirectory.connect(lambda : self.onLazyLoadDirectory(self.ex_main))
            view2.loadDirectory.connect(lambda : self.onLazyLoadDirectory(self.ex_secondary))

            self.ex_main.setView(view1)
            self.ex_secondary.setView(view2)

            self.ex_main.submitJob.connect(self.dashboard.startJob)
            self.ex_secondary.submitJob.connect(self.dashboard.startJob)
            self.controller.submitJob.connect(self.dashboard.startJob)

            print("chdir")
            self.ex_main.chdir("C:\\Users\\Nick\\Documents\\playground")
            self.ex_secondary.chdir("~")

    def chdir(self, path):

        # chdir can be called from another Tab, prior to onEnter,
        # if that happens run the onEnter first time setup.
        self.onEnter()

        self.ex_main.chdir(path)

        print("expview chdir",path)

    def onLazyLoadDirectory(self,model):

        print("on lazy load")
        job = LoadDirectoryJob(model)
        self.dashboard.startJob(job)

    def refresh(self):
        print(self.ex_main.view.pwd())
        self.ex_main.refresh()
        if self.ex_secondary.isVisible():
            print(self.ex_secondary.view.pwd())
            self.ex_secondary.refresh()

    def onToggleSecondaryView(self):
        if self.ex_secondary.isHidden():
            self.ex_secondary.show()
            self.ex_main.showSplitButton(False)
            self.ex_secondary.showSplitButton(True)
        else:
            self.ex_secondary.hide()
            self.ex_main.showSplitButton(True)
            self.ex_secondary.showSplitButton(False)

