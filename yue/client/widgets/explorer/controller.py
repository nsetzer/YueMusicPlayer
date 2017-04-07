

import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.explorer.jobs import Job, CopyJob, MoveJob, DeleteJob
from yue.core.explorer.source import DirectorySource,SourceListView
from yue.core.explorer.ftpsource import parseFTPurl, FTPSource

class DummyController(QObject):
    """ Dummy Controller takes no action
    """
    def __init__(self):
        super(DummyController, self).__init__()

        self.dialog = None
        self.cut_items = None
        self.cut_root = ""

    def contextMenu(self, event , model, items):
        pass
    def showMoveFileDialog(self, mdl,tgt,src):
        pass
    def showIngestDialog(self, paths):
        pass
    def onDialogExit(self):
        pass
    def canPaste( self, dirpath):
        return False
    def action_open_view(self):
        pass
    def action_close_view(self):
        pass

    def secondaryHidden(self):
        return True

class ExplorerController(DummyController):

    submitJob = pyqtSignal(Job)
    forceReload = pyqtSignal()

    def __init__(self):
        super(ExplorerController,self).__init__()

        #self.dialog = None

        self.cut_items = None
        self.cut_root = ""
        self.cut_view = None
        self.cut_model = None

        self.copy_items = None
        self.copy_root = ""
        self.copy_view = None
        self.copy_model = None

    def _ctxtMenu_addFileOperations1(self,ctxtmenu,model,items):

        is_files = all(not item['isDir'] for item in items)
        is_dirs  = all(item['isDir'] for item in items)

        ctxtmenu.addSeparator()

        act = ctxtmenu.addAction("Rename", lambda : model.action_rename_begin(items))
        #act.setDisabled( len(items)!=1 )

        act=ctxtmenu.addAction("Copy", lambda : self.action_copy( model, items ))
        act.setShortcut(QKeySequence("Ctrl+C"))
        act=ctxtmenu.addAction("Cut", lambda : self.action_cut( model, items ))
        act.setShortcut(QKeySequence("Ctrl+X"))
        if not model.view.readonly():
            act = ctxtmenu.addAction("Paste", lambda : self.action_paste(model))
            act.setShortcut(QKeySequence("Ctrl+V"))
            act.setDisabled( not model.canPaste() )

        ctxtmenu.addAction("Delete", lambda : self.action_delete( model, items ))

    def _ctxtMenu_addFileOperations2(self,ctxtmenu,model,items):

        #ctxtmenu.addSeparator()
        #act = ctxtmenu.addAction("Refresh",model.action_refresh)

        if model.showHiddenFiles():
            act = ctxtmenu.addAction("hide Hidden Files",lambda:model.action_set_hidden_visible(False))
        else:
            act = ctxtmenu.addAction("show Hidden Files",lambda:model.action_set_hidden_visible(True))
        ctxtmenu.addSeparator()

        if len(items) == 1:
            act = ctxtmenu.addAction("Copy Path To Clipboard",
                lambda : model.action_copy_path(items[0]))
            ctxtmenu.addSeparator()



    def contextMenu(self, event, model, items):

        ctxtmenu = QMenu(model)

        self._ctxtMenu_addFileOperations1(ctxtmenu,model,items)
        ctxtmenu.addSeparator()
        self._ctxtMenu_addFileOperations2(ctxtmenu,model,items)

        if model.view.islocal():
            ctxtmenu.addAction(QIcon(":/img/app_open.png"),"Open in Explorer",model.action_open_directory)


        action = ctxtmenu.exec_( event.globalPos() )

    """
    if len(items) == 1:
        act = contextMenu.addAction("Play Song", lambda: model.action_open_file( items[0] ))
        ext = os.path.splitext(items[0]['name'])[1].lower()
        if not model.supportedExtension( ext ):
            act.setDisabled( True )

    if len(items) == 1 and is_files:
        contextMenu.addSeparator()
        act = contextMenu.addAction("update/replace *", lambda: model.action_update_replace(items[0]))

    """

    """
    def showMoveFileDialog(self, mdl, tgt,src):
        self.dialog = MoveFileProgressDialog(mdl.view, tgt, src, self.parent)
        self.dialog.setOnCloseCallback(self.onDialogExit)
        self.dialog.start()
        self.dialog.show()

    def showIngestDialog(self, paths):
        self.dialog = IngestProgressDialog(paths, self.parent)
        self.dialog.setOnCloseCallback(self.onDialogExit)
        self.dialog.start()
        self.dialog.show()

    def onDialogExit(self):
        if isinstance(self.dialog,IngestProgressDialog):
            self.parent.ingest_finished.emit()
        self.dialog = None
        # reload current directory
        self.parent.ex_main.refresh()
        self.parent.ex_secondary.refresh()
    """

    def canPaste( self, dirpath):
        """ return true if we can paste into the given directory """
        if self.cut_items is not None and self.cut_root != dirpath:
            return True

        if self.copy_items is not None:
            return True

        return False

    def action_update_replace(self, path):

        def strmatch(s1,s2,field):
            return s1[field].lower().replace(" ","") == \
                   s2[field].lower().replace(" ","")

        p, n = os.path.split( path )
        gp, _ = os.path.split( p )

        songs = Library.instance().searchDirectory( gp, recursive=True )

        temp = Song.fromPath( path );
        sys.stdout.write(gp+"\n")
        for song in songs:
            match = strmatch(song,temp,Song.artist) and strmatch(song,temp,Song.title) or \
                    (temp[Song.album_index]>0 and song[Song.album_index] == temp[Song.album_index])
            sys.stdout.write( "[%d] %s\n"%(match,Song.toString(song)) )
            if match:
                Library.instance().update(song[Song.uid],**{Song.path:path})

    def action_delete(self,model,items):

        view = model.view
        paths = [ view.realpath(item['name']) for item in items ]
        job = DeleteJob(view,paths)
        job.finished.connect(model.onDeleteJobFinished)
        self.submitJob.emit(job)

    def action_cut(self, model, items):
        """
        view : a wrapper around the source for paths in fpaths
        fpaths: list of absolute paths
        """
        view = model.view
        cut_items =  [ view.realpath(item['name']) for item in items ]

        self.cut_items = cut_items
        self.cut_root = view.pwd()
        self.cut_view = view
        self.cut_model = model
        print("on action cut")

    def action_copy(self, model, items):
        """
        todo, there is an internal and external expectation for copy
            Allow copy within Yue by storing meta data (source, list)
            for local source (Directory) also place on the clipboard
        QMimeData* mimeData = new QMimeData();
        mimeData->setData("text/uri-list", "file:///C:/fileToCopy.txt");
        clipboard->setMimeData(mimeData);
        """
        view = model.view
        copy_items =  [ view.realpath(item['name']) for item in items ]

        self.copy_items = copy_items
        self.copy_root = view.pwd()
        self.copy_view = view
        self.copy_model = model

    def action_paste(self, model):
        """
        view: a wrapper around the source for paths
        dir_path: absolute path existing in view

        paste can copy across difference sources
        a cut or copy -> paste on the same DIRECTORY is a noop
        a cut -> paste on the same source is a move
        a cut -> paste across different sources is a copy
        a copy -> paste is always a copy, even on the same source
        """
        view = model.view
        dir_path = view.pwd()

        if not self.canPaste(dir_path):
            return

        if self.cut_items is not None:
            job = self.createMoveJob(view,dir_path)
            job.finished.connect(model.onJobFinished)
            if self.cut_model is not model:
                job.finished.connect(self.cut_model.onJobFinished)
            self.submitJob.emit(job)
            self.cut_items = None
            self.cut_root = ""

        elif self.copy_items is not None:
            job = self.createCopyJob(view,dir_path)
            job.finished.connect(model.onJobFinished)
            if self.copy_model is not model:
                job.finished.connect(self.copy_model.onJobFinished)
            self.submitJob.emit(job)

            self.copy_items = None
            self.copy_root = ""

    def createMoveJob(self,view,dir_path):
        if not self.cut_view.equals(view):
            job = CopyJob(self.cut_view,self.cut_items,view,dir_path)
        else:
            job = MoveJob(self.cut_view,self.cut_items,dir_path)
        return job

    def createCopyJob(self,view,dir_path):
        job = CopyJob(self.copy_view,self.copy_items,view,dir_path)
        return job
