

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

    def hasChanged(self):
        """ return True if the file has changed on disk """
        st = self.localSource.stat(self.localPath)
        return st['mtime'] != self.st['mtime'] or st['size'] != self.st['size']


    def sync(self):

        st = self.localSource.stat(self.localPath)

        with self.localSource.open(self.localPath,"rb") as rf:
            self.remoteSource.putfo(self.remotePath,rf)

        st_r = self.remoteSource.stat(self.remotePath)

        if st_r['size'] != st['size']:
            sys.stderr.write("error syncing file: %s"%self.remotePath)

        self.st = st

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


