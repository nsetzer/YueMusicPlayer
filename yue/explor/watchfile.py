

"""

A mechanism for watching a list of files or directories.

Any remote file system that supports the get/put api copies files
locally when "opened". A machanism is needed to check for changes
and copy the files back.

Different file systems have different methods for noftifying
when a file is changed. A callback system should be used and
support 4 different modes of operation
    * Windows
    * linux : inotify
    * Darwin
    * None  : UI button activates callback for all files

watch files need to know the source they came from, the local
and remote file path.

Eventually a way to recover the session will be required.
sources should provide a method that returns a dictionary
of parameters required to reopen the source -- excluding passwords

parts that are pure python should be moved to yue/core/explorer

how files are copied locally depends on how the
various platforms support watch files,

This will complicate closing source
    - fast close : ignore watch files
    - safe close : copy modified watch files then close

how do we close watch files?
    need some way to garbage collect files
    that have not been modified in a long time.
    couple different use cases:
        code file : opened, modified, then tested for some time
        log file: opened, read, and then closed.
    these are the same from the outside looking in, but removing
        the code file if it is still opened in an editor is bad

"""


from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.qtcommon.explorer.jobs import Job
from yue.qtcommon.LargeTable import LargeTable, TableColumn
from yue.explor.util import proc_exec
from yue.core.settings import Settings

import os,sys

class WatchFile(object):
    """docstring for WatchFile"""
    def __init__(self, localSource, localPath, remoteSource,remotePath):
        super(WatchFile, self).__init__()
        self.localSource = localSource
        self.remoteSource = remoteSource
        self.localPath = localPath
        self.remotePath = remotePath
        self.st = self.localSource.stat(self.localPath)
        self.dirty = False;

    def hasChanged(self):
        """ return True if the file has changed on disk """
        if self.dirty == False:
            st = self.localSource.stat(self.localPath)
            self.dirty = st['mtime'] != self.st['mtime'] or st['size'] != self.st['size']
        return self.dirty;

    def sync(self):

        st = self.localSource.stat(self.localPath)

        with self.localSource.open(self.localPath,"rb") as rf:
            self.remoteSource.putfo(self.remotePath,rf)

        st_r = self.remoteSource.stat(self.remotePath)

        if st_r['size'] != st['size']:
            sys.stderr.write("error syncing file: %s"%self.remotePath)

        self.st = st
        self.dirty = False

    def close(self):
        """
        todo: undefined cleanup process
        """
        pass

class WatchFileController(QObject):
    """docstring for WatchFileController"""

    submitJob = pyqtSignal(Job)
    watchersChanged =  pyqtSignal(int)

    def __init__(self,localSource):
        """
        localSouce is any source that implements the file open API
        if it is a directory source, a per platform notify system
        will be attached.
        """
        super(WatchFileController, self).__init__()

        self.source = localSource

        self.watch_list = {}

    def clear(self):

        #TODO: move this to a task
        for _,wf in self.watch_list.items():
            wf.close()
        self.watch_list = {}
        self.watchersChanged.emit(0)

    def addFile(self,localPath,source,remotePath):

        if localPath in self.watch_list:
            self.watch_list[localPath].close()
            del self.watch_list[localPath]

        wf = WatchFile(self.source,localPath,source,remotePath)

        self.watch_list[localPath] = wf

        self.watchersChanged.emit(len(self.watch_list))

    def closeFile(self,localPath):

        wf = self.watch_list[localPath];
        wf.close()
        del self.watch_list[localPath]

        self.watchersChanged.emit(len(self.watch_list))

    def onPostAll(self):
        """
        iterate through all watch files, if the mtime has changed
        queue a job for
        """

        for _,wf in self.watch_list.items():
            if wf.hasChanged():
                print("sync file",wf.remotePath)
                wf.sync()
            else:
                print("file has not changed",wf.remotePath)

    def onChange(self,localPath):
        """
        a watch file given by localPath has changed, sync with remote
        """

        # TODO: move this to a task
        if localPath in self.watch_list:
            wf = self.watch_list[localPath]
            wf.sync()

    def count(self):
        return len(self.watch_list)

    def getDirtyFiles(self):
        files = []
        for path, wf in self.watch_list.items():
            if wf.hasChanged():
                files.append(wf);
        return files

    def iter(self):

        for path,wf in self.watch_list.items():
            yield wf;

class WatchFileTable(LargeTable):
    """
    displays the contents of the WatchFileController
    """
    changeDirectory = pyqtSignal(str)

    def __init__(self, wfctrl, parent=None):
        super(WatchFileTable,self).__init__(parent)
        self.wfctrl = wfctrl

        self.wfctrl.watchersChanged.connect(self.onWatchersChanged)

        self.onWatchersChanged(self.wfctrl.count())

        self.hbox = QHBoxLayout()
        self.btnDetect = QPushButton("Check")
        self.btnDetect.clicked.connect(self.checkForChanges)
        self.btnSync   = QPushButton("Sync")
        self.btnSync.clicked.connect(self.syncDirtyFiles)
        self.hbox.addWidget(self.btnDetect)
        self.hbox.addWidget(self.btnSync)
        self.vbox.addLayout(self.hbox)

        self.rule_dirty = lambda row: self.data[row][3]
        self.addRowTextColorComplexRule(self.rule_dirty,  QColor(200,32,48))

    def initColumns(self):
        self.columns.append( TableColumn(self,1,"Name") )
        self.columns[-1].setWidthByCharCount(12)

    def onWatchersChanged(self,count):
        if count == 0:
            self.container.setHidden(True)
        else:
            self.container.setHidden(False)

        data = []
        for wf in self.wfctrl.iter():
            _,name = wf.remoteSource.split(wf.remotePath)
            d = [wf, name, wf.localPath, wf.hasChanged()]
            data.append(d)
        self.setData(data)

    def mouseDoubleClick(self,row,col,event=None):

        if event is None or event.button() == Qt.LeftButton:
            if 0<= row < len(self.data):
                item = self.data[row]
                wf = item[0]
                self.action_open(wf)

    def mouseReleaseRight(self,event):

        ctxtmenu = QMenu(self.container)

        sel = self.getSelection()
        if len(sel)==1:
            item = sel[0]
            wf = item[0]

            ctxtmenu.addAction("Sync",lambda : self.action_sync([wf,]))
            ctxtmenu.addAction("Edit",lambda : self.action_open(wf))

            ctxtmenu.addAction("Close",lambda : self.action_close([wf,]))

        else:
            wfs = [ item[0] for item in sel ]
            ctxtmenu.addAction("Sync Selection",lambda : self.action_sync(wfs))
            ctxtmenu.addAction("Close Selection",lambda : self.action_sync(wfs))

        ctxtmenu.addAction("Open Local Cache",self.action_open_local_directory)

        action = ctxtmenu.exec_( event.globalPos() )

    def action_close(self,wfs):
        for wf in wfs:
            self.wfctrl.closeFile(wf.localPath)

    def action_sync(self,wfs):
        for wf in wfs:
            wf.sync()

    def action_open(self,wf):

        path = wf.localPath
        # todo: get pwd, pass to proc_exec
        cmdstr = Settings.instance()['cmd_edit_text']

        proc_exec(cmdstr%(path))

    def action_open_local_directory(self):
        # TODO !! local source
        ftemp = os.path.join(Settings.instance()['database_directory'],"remote")
        self.changeDirectory.emit(ftemp)

    def checkForChanges(self):
        files = self.wfctrl.getDirtyFiles();
        self.onWatchersChanged(self.wfctrl.count())

    def syncDirtyFiles(self):
        for wf in self.wfctrl.getDirtyFiles():
            wf.sync();
        self.onWatchersChanged(self.wfctrl.count())








