

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

"""

from yue.client.widgets.explorer.jobs import Job


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


class WatchFiles(QObject):
    """docstring for WatchFiles"""

    submitJob = pyqtSignal(Job)
    def __init__(self,localSource):
        """
        localSouce is any source that implements the file open API
        if it is a directory source, a per platform notify system
        will be attached.
        """
        super(WatchFiles, self).__init__()

        self.source = localSource

        self watch_list = []

    def addFile(self,localPath,source,remotePath)

        wf = WatchFile(self.source,localPath,source,remotePath)
        self.watch_list.append(wf)

    def onPostAll(self):
        """
        iterate through all watch files, if the mtime has changed
        queue a job for
        """
        pass

    def onChange(self,localPath):
        pass


