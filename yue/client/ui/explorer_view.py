#! cd ../../.. && python client-main.py

import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback

from yue.qtcommon.Tab import Tab

from yue.qtcommon.explorer.controller import ExplorerController
from yue.qtcommon.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, \
    DropRequestJob, Dashboard
from yue.qtcommon.explorer.source import LazySourceListView
from yue.qtcommon.explorer.filetable import ExplorerFileTable
from yue.qtcommon.ResourceManager import ResourceManager
from yue.qtcommon.explorer.display import ExplorerModel

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library

from yue.client.dialog.ingest_dialog import IngestProgressDialog
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

class YueExplorerController(ExplorerController):

    def __init__(self):
        super(YueExplorerController,self).__init__()

        self.dialog = None

    def contextMenu(self, event, model, items):

        is_files = all(not item['isDir'] for item in items)
        is_dirs  = all(item['isDir'] for item in items)

        ctxtmenu = QMenu(model)

        # file manipulation options
        menu = ctxtmenu.addMenu("New")
        menu.addAction("Empty File",lambda : model.action_touch_begin())
        menu.addAction("Folder", lambda : model.action_mkdir_begin())

        if len(items) == 1:
            ctxtmenu.addAction("Play Song",lambda : model.action_play_song(items[0]))

        if model.canIngest():
            ctxtmenu.addAction("Ingest Selection", lambda : model.action_ingest(items))

        ctxtmenu.addSeparator()

        self._ctxtMenu_addFileOperations1(ctxtmenu,model,items)

        ctxtmenu.addSeparator()


        self._ctxtMenu_addFileOperations2(ctxtmenu,model,items)

        if model.view.islocal():
            ctxtmenu.addAction(QIcon(":/img/app_open.png"),"Open in Explorer",model.action_open_directory)

        ctxtmenu.addAction("Refresh",model.action_refresh)

        if len(items) > 0 and is_files:
            ctxtmenu.addSeparator()
            act = ctxtmenu.addAction("update/replace *", lambda: model.action_update_replace(items))

        action = ctxtmenu.exec_( event.globalPos() )

class YueExplorerModel(ExplorerModel):

    play_file = pyqtSignal(str)
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
        exists = self.view[idx]['name'].lower() in self.list_library_files
        #print(exists,self.view[idx]['name'].lower())
        # OSX normalized the file name
        # a="/Users/nsetzer/Music/Library/大凶作_(Dai_kyousaku)/大喝采/05_片恋マンドレイク.mp3"
        # b="/Users/nsetzer/Music/Library/大凶作_(Dai_kyousaku)/大喝采/05_片恋マンドレイク.mp3"
        # c=unicodedata.normalize('NFC', a)
        # c==b

        return exists

    def action_play_song(self,item):
        path = self.view.realpath(item['name'])
        self.play_file.emit(path)

    def action_update_replace(self, items):

        for item in items:
            path = self.view.realpath(item['name'])
            self.action_update_replace_impl(path)

        self.action_refresh()

    def action_update_replace_impl(self, path):

        def strmatch(s1,s2,field):
            return s1[field].lower().replace(" ","") == \
                   s2[field].lower().replace(" ","")

        def _match(song, temp):
            # match songs based on index or title
            a = strmatch(song,temp,Song.artist) and \
                strmatch(song,temp,Song.title)
            i = False
            if temp[Song.album_index] > 0:
                i = song[Song.album_index] == temp[Song.album_index]
            return a or i

        # load the given path as a song to get meta data
        temp = Song.fromPath( path );

        p, n = os.path.split( path )
        gp, _ = os.path.split( p )

        # search grandparent for songs
        songs = Library.instance().searchDirectory( gp, recursive=True )

        sys.stdout.write(gp+"\n")
        for song in songs:
            if _match(song, temp):
                Library.instance().update(song[Song.uid],**{Song.path:path})
                break;
        else:
            print("failed to update/replace record.")

    def action_ingest(self,items):
        paths = [ self.view.realpath(item['name']) for item in items ]
        self.do_ingest.emit( paths )

    def action_open_file(self,item):
        path = self.view.realpath(item['name'])
        _,ext = self.view.splitext(path)
        self.play_file.emit(path)

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

    def onRenameFinished(self):

        songs = Library.instance().searchDirectory(self.view.pwd(),False)
        self.list_library_files = set( self.view.split(song[Song.path])[1].lower() \
                                       for song in songs )
        self.tbl_file.update()


class ExplorerView(Tab):
    """docstring for ExplorerView"""

    play_file = pyqtSignal(str)
    ingest_finished = pyqtSignal()

    primaryDirectoryChanged = pyqtSignal(str)
    secondaryDirectoryChanged = pyqtSignal(str)

    submitJob = pyqtSignal(Job)


    def __init__(self, parent=None):
        super(ExplorerView, self).__init__(parent)

        self.controller = YueExplorerController( )

        self.source = DirectorySource()

        self.dashboard = Dashboard(self)

        self.ex_main = YueExplorerModel( None, self.controller, self )
        self.ex_secondary = YueExplorerModel( None, self.controller, self )
        self.ex_secondary.btn_split.setIcon(QIcon(":/img/app_join.png"))

        self.ex_main.do_ingest.connect(self.onIngestPaths)
        self.ex_secondary.do_ingest.connect(self.onIngestPaths)

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

            self.ex_main.play_file.connect(self.onPlayFile)
            self.ex_secondary.play_file.connect(self.onPlayFile)

            self.ex_main.submitJob.connect(self.dashboard.startJob)
            self.ex_secondary.submitJob.connect(self.dashboard.startJob)
            self.controller.submitJob.connect(self.dashboard.startJob)

            self.ex_main.chdir("~")
            self.ex_secondary.chdir("~")

    def chdir(self, path):

        # chdir can be called from another Tab, prior to onEnter,
        # if that happens run the onEnter first time setup.
        self.onEnter()

        self.ex_main.chdir(path)

    def onLazyLoadDirectory(self,model):

        job = LoadDirectoryJob(model)
        self.dashboard.startJob(job)

    def refresh(self):
        self.ex_main.refresh()
        if self.ex_secondary.isVisible():
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

    def onIngestPaths(self,paths):

        self.controller.dialog = IngestProgressDialog(paths,self)
        self.controller.dialog.finished.connect(self.onDialogFinished)

        self.controller.dialog.show()
        self.controller.dialog.start()

    def onDialogFinished(self):
        if isinstance(self.controller.dialog,IngestProgressDialog):
            self.ingest_finished.emit()
        self.controller.dialog = None
        self.ex_main.refresh()
        self.ex_secondary.refresh()

    def onPlayFile(self,path):
        self.play_file.emit(path)