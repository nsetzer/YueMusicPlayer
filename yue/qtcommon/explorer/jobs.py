
import os,sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from enum import Enum
import traceback

from yue.core.explorer.source import DirectorySource,SourceListView
from yue.core.explorer.fsutil import generateUniquePath, \
    walk_files, iter_copy, source_copy, \
    iter_remove
from yue.core.util import format_bytes

from yue.core.song import Song
from yue.core.library import Library
import time

class JobMessageBox(QDialog):
    """docstring for JobMessage"""
    def __init__(self, arg):
        super(JobMessageBox, self).__init__()
        self.arg = arg

class AbortJob(Exception):
    pass

class JobRunner(QObject):

    def __init__(self, parent):
        super(JobRunner, self).__init__(parent)

        self.jobs = []

    def startJob(self,job):

        job.showMessageBox.connect(lambda t,m,o: self.handleMessageBox(job,t,m,o))
        job.finished.connect(lambda : self.jobFinished(job))

        self.jobs.append(job)

        job.start()

    def handleMessageBox(self,job,title,msg,options):

        mbox = QMessageBox(QMessageBox.Question,title,msg)
        if not options:
            options = ["ok"]

        for text in options:
            mbox.addButton(text,QMessageBox.AcceptRole)

        result = mbox.exec_()

        job.notifyMessageBoxResult(result)

    def jobFinished(self,job):

        self.jobs.remove(job)

class Job(QThread):
    """docstring for Job

    A Job is a long running task which performs some file IO

    A job can be canceled and can display dialogs
    to the user. A job can also report progress which is displayed
    in a progress bar in the main gui
    """

    # type, message
    showMessageBox = pyqtSignal(str,str,object)

    progressChanged = pyqtSignal(int)

    def __init__(self):
        super(Job, self).__init__()

        #print("create",self.__class__.__name__)
        self.msgbox_result = None

        self.cond = QWaitCondition()
        self.mutex = QMutex()

        self._progress = -2
        self._alive = True

    def run(self):
        print("start",self.__class__.__name__)

        try:
            self.doTask()
        except AbortJob as e:
            print("job aborted")
        except Exception as e:
            traceback.print_exc()
            print(e)

        print("complete",self.__class__.__name__)

    def doTask(self):
        """ reimplement this function to perform your task

        periodically call setProgress or checkAbort to ensure
        the task can be responsively stopped
        """
        pass

    def checkAbort(self):

        with QMutexLocker(self.mutex):
            return self._alive

    def abort(self):

        with QMutexLocker(self.mutex):
            self._alive = True

    def setProgress(self,iValue):
        """
        set the current progress (0-100)
        or busy indicator (-1)

        to prevent too many signals being emitted, this only emits
        a notification to the system if the actual progress changes.
        """

        self.checkAbort()

        if iValue != self._progress:

            self.progressChanged.emit(iValue)
            self._progress = iValue

    def getInput(self,title,message,options=None):
        """
        display a dialog and wait for the result (user accept/reject)

        Dialogs must be started in the main thread. emit a signal
        back to the main thread to show a dialog. then wait for the
        main thread to notify us with the result.
        """

        with QMutexLocker(self.mutex):

            self.showMessageBox.emit(title,message,options)

            if not self._alive:
                raise AbortJob()

            self.cond.wait(self.mutex)

            if not self._alive:
                raise AbortJob()

            return self.msgbox_result

    def notifyMessageBoxResult(self,result):
        with QMutexLocker(self.mutex):
            self.msgbox_result = result
            self.cond.wakeOne()

def move_one_lib(src,lib,src_path,dst_path):
    """
    Library aware file move

    if the move from src_path to dst_path would effect a song
    in the library, the database is updated to reflect the song
    """
    if src.isdir(src_path):
        songs = lib.searchDirectory( src_path ,True)
        src.move(src_path,dst_path)
        for song in songs:
            tmp = tgt + song[Song.path][len(src_path):]
            lib.update(song[Song.uid],path=tmp)
            self.updated_count += 1
    else:
        songs = lib.searchPath( src_path )
        src.move(src_path,dst_path)
        for song in songs: # this will update duplicate songs by path
            lib.update(song[Song.uid],path=dst_path)

class RenameJob(Job):
    """docstring for RenameJob"""
    def __init__(self, view, args):
        """ args as list of 2-tuple (src,tgt)

        rename the set of files in the cwd.
        """
        super(RenameJob, self).__init__()
        self.view = view
        self.wd = view.pwd()
        self.args = args
        self.lib = None

    def doTask(self):

        if Library.instance():
            self.lib = Library.instance().reopen()

        for i,(src,dst) in enumerate(self.args):
            src=self.view.normpath(src,self.wd)
            dst=self.view.normpath(dst,self.wd)

            if self.lib:
                move_one_lib(self.view,self.lib,src,dst)
            else:
                self.view.move(src,dst)
            self.setProgress(100*(i+1)/len(self.args))

class CopyJob(Job):
    def __init__(self, src_view, src_paths, dst_view, dst_path):
        """ args as list of 2-tuple (src,tgt)

        rename the set of files in the cwd.
        """
        super(CopyJob, self).__init__()
        self.src_view = src_view
        self.src_paths = src_paths
        self.dst_view = dst_view
        self.dst_path = dst_path

        self.tot_size  = 0
        self.tot_size_copied = 0
        self.num_files = 0

        self.chunksize = 1024*32

    def doTask(self):

        self.setProgress(0)
        self.calculate_totals()

        print(self.tot_size,self.num_files)

        if self.tot_size > 10*1024:
            self.getInput("title",format_bytes(self.tot_size),["ok","cancel"])

        nfiles = 0
        for src_path,dst_path in iter_copy(self.src_view,self.src_paths,
                                         self.dst_view,self.dst_path):
            self.copy_one(src_path,dst_path)
            nfiles += 1
            self.setProgress(100*nfiles/self.num_files)

    def calculate_totals(self):

        for path,_ in walk_files(self.src_view,self.src_paths):
            st = self.src_view.stat_fast(path)
            self.tot_size += st["size"]
            self.num_files += 1

    def copy_one(self,src_path,dst_path):
        dst_dir,_ = self.dst_view.split(dst_path)
        if self.dst_view.exists(dst_path):
            src_dir,_ = self.dst_view.split(src_path)

            if src_dir == dst_dir:
                idx = 1
            else:
                options = ["Replace","Keep Both","Skip"]
                title = "Confirm Overwrite"
                text = "input file \"%s\" already exists.\n" \
                       "Overwrite?" % (dst_path)
                idx = self.getInput(title,text,options)

            if idx == 2:
                return
            elif idx == 1:
                dst_path = generateUniquePath(self.dst_view,dst_path)

        print("cp",src_path,dst_path)
        self.source_copy(src_path, dst_path)

    # TODO: eventually. refactor source_copy and source_copy_file
    # and merge with the functions in fsutil. this will require providing
    # a callback mechanism.

    def source_copy(self, input, target):

        for src,dst in iter_copy(self.src_view, input, self.dst_view, target):
            dname,_ = self.dst_view.split(dst)
            self.dst_view.mkdir( dname )
            self.source_copy_file(src, dst)

    def source_copy_file(self, pathA, pathB):
        """
        Perform file copy from one source to another.
        chunksize is the number of bytes to read/write at one time.
        """
        st = self.src_view.stat(pathA)
        if st['isLink']:
            target = self.src_view.readlink(pathA)
            self.dst_view.mklink(target,pathB)
            self.tot_size_copied += st['size']
            self.setProgress(100*self.tot_size_copied/self.tot_size)
            return

        # 4 possible casses
        #   assuming at least one ove open or get/put is supported
        # | src     | dst     |
        # | open    | open    | open -> open
        # | open    | get/put | open -> put
        # | get/put | open    | get  -> open
        # | get/put | get/put | get / put : requires a temporary file.
        # the 4th case can be implemented in the future

        so = self.src_view.isOpenSupported()
        do = self.dst_view.isOpenSupported()
        sg = self.src_view.isGetPutSupported()
        dg = self.dst_view.isGetPutSupported()
        print(so,sg,do,dg)
        if so and do:

            with self.src_view.open(pathA,"rb") as rb:
                with self.dst_view.open(pathB,"wb") as wb:
                    buf = rb.read(self.chunksize)
                    while buf:
                        wb.write(buf)# TODO: write should return len buf
                        self.tot_size_copied += len(buf)
                        self.setProgress(100*self.tot_size_copied/self.tot_size)
                        buf = rb.read(self.chunksize)

        elif so and dg:
            print("open/put")
            with self.src_view.open(pathA,"rb") as rb:
                self.dst_view.putfo(pathB,rb,self.fo_cbk)
            self.tot_size_copied += self.src_view.stat_fast(pathA)['size']
            self.setProgress(100*self.tot_size_copied/self.tot_size)

        elif sg and do:
            print("get/open")
            with self.dst_view.open(pathB,"wb") as wb:
                self.src_view.getfo(pathA,wb,self.fo_cbk)
            self.tot_size_copied += self.src_view.stat_fast(pathB)['size']
            self.setProgress(100*self.tot_size_copied/self.tot_size)

        elif sg and dg:
            sys.stderr.write("copy not implemented between %s and %s"%(
                self.src_view.__class__.__name__,
                self.dst_view.__class__.__name__))

        else:
            sys.stderr.write("copy not supported between %s and %s"%(
                self.src_view.__class__.__name__,
                self.dst_view.__class__.__name__))

    def fo_cbk(self,tr,to):
        self.setProgress(100*(self.tot_size_copied+tr)/self.tot_size)

class MoveJob(Job):
    def __init__(self, src_view, src_paths, dst_path):
        """ args as list of 2-tuple (src,tgt)

        rename the set of files in the cwd.
        """
        super(MoveJob, self).__init__()
        self.view = src_view
        self.src_paths = src_paths
        self.dst_path = dst_path
        self.lib = None

    def doTask(self):
        """
        TODO: make this library aware. If not library is configured
        (instance returns none) thn don't bother.
        Rename also needs to be away
        Rename Should be removed entirely
        """

        # get a thread local copy of the library
        # must compare to None, otherwise when it is a DB instance,
        # a thread access violation is thrown
        if Library.instance() is not None:
            self.lib = Library.instance().reopen()

        for i,path in enumerate(self.src_paths):

            name = self.view.split(path)[1]
            dst_path = self.view.join(self.dst_path,name)
            dst_path = generateUniquePath(self.view,dst_path)

            if self.lib:
                move_one_lib(self.view,self.lib,path,dst_path)
            else:
                self.move_one(path,dst_path)

            self.setProgress(100*(i+1)/len(self.src_paths))

    def move_one(self,src_path,dst_path):
        self.view.move(src_path,dst_path)

class DropRequestJob(Job):
    def __init__(self, src_view, urls, dst_view, dst_path):
        """ args as list of 2-tuple (src,tgt)

        rename the set of files in the cwd.
        """
        super(DropRequestJob, self).__init__()

        if src_view is None:
            src_view = DirectorySource()

        self.src_view = src_view
        self.src_urls = urls
        self.dst_view = dst_view
        self.dst_path = dst_path

        self.chunksize = 1024*32

    def doTask(self):


        print(self.src_view)
        print(self.src_urls)

        paths = []
        for url in self.src_urls:
            if url.isLocalFile():
                paths.append( url.toLocalFile() )

        print(paths)

        for i,path in enumerate(paths):

            name = self.src_view.split(path)[1]
            dst_path = self.src_view.join(self.dst_path,name)
            dst_path = generateUniquePath(self.src_view,dst_path)

            self.move_one(path,dst_path)

            self.setProgress(100*(i+1)/len(paths))


    def move_one(self,src_path,dst_path):
        """ this could be reimplented, say to update a database? """

        if self.src_view.equals(self.dst_view):
            self.dst_view.move(src_path,dst_path)
        else:
            source_copy(self.src_view,src_path, \
                        self.dst_view,dst_path,self.chunksize)

class DeleteJob(Job):
    """docstring for RenameJob"""
    def __init__(self, view, paths):
        """ paths as list of str

        delete the set of files or directories in the cwd.

        there are two phases to this task

            1. discovery - determine set of files to delete
            2. remove each file one at a time
                2.a attempt to remove empty directories.
        """
        super(DeleteJob, self).__init__()
        self.view = view
        self.paths = paths

    def doTask(self):

        self.setProgress(-1)

        # first, lets quickly  scan the selection to get an idea
        # of how much work needs to be done. its arbitrary
        # but >100 is "a lot of work"

        idx = self.getInput("Confirm Delete","are you serious?",["Delete","Cancel"])

        if idx != 0:
            return

        for path in iter_remove(self.view,self.paths):
            self.view.delete(path)

class LoadDirectoryJob(Job):
    """docstring for LoadDirectoryJob"""

    loadComplete = pyqtSignal(list)

    def __init__(self, model):
        super(LoadDirectoryJob, self).__init__()
        self.model = model
        self.view = model.view

        self.loadComplete.connect(self.model.onLoadComplete)

    def doTask(self):

        try:
            data = self.view.source.listdir(self.view.path)

            if not self.view.show_hidden:
                data =  [ x for x in data if not self.view.source.hidden(x) ]

            st = self.view.stat
            if self.view.sort_column_name in {"name","size"}:
                st = self.view.stat_fast

            # stat all the files, emit progress for slow directories
            items = []
            for idx,name in enumerate(data):
                self.setProgress( int(100*(idx+1)/len(data)) )
                items.append(st(name))
            # on windows, stat uncovers additional hidden resources
            if sys.platform == "win32" and not self.view.show_hidden:
                items = [ x for x in items if "isHidden" not in x]

            items = self.view._sort(items)

            data = [ x['name'] for x in items ]

        except OSError as e:
            data = []
            traceback.print_exc()
            self.getInput("Access Error",str(e)+"\n"+self.view.pwd(), ["Ok"])


        self.loadComplete.emit(data)

class Dashboard(QWidget):
    """the Dashboard is where long running jobs are displayed

    A job is started and displayed with a progress bar in the dashboard.
    this allows the user to cancel the job if needed. when the job
    completes it is removed from the dashboard.
    """
    def __init__(self, parent):
        super(Dashboard, self).__init__(parent)

        self.job_runner = JobRunner(self)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.widgets = []

        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Minimum)

    def startJob(self,job):

        jw = JobWidget(job,self)
        jw.deleteJob.connect(self.onDeleteJob)
        self.widgets.append(jw)
        self.vbox.addWidget(jw)

        self.job_runner.startJob(job)

    def onDeleteJob(self,jw):
        self.vbox.removeWidget(jw)
        jw.setParent(None)
        jw.deleteLater()

class JobWidget(QWidget):
    """docstring for JobWidget"""

    deleteJob = pyqtSignal(QWidget)

    def __init__(self, job, parent):
        super(JobWidget, self).__init__(parent)
        self.job = job

        self.label = QLabel(job.__class__.__name__,self)
        self.pbar = QProgressBar(self)
        self.job.progressChanged.connect(self.setProgress)

        # delay showing this widget
        # quick jobs will not appear in the gui
        self.timer_show = QTimer(self)
        self.timer_show.setSingleShot(True)
        self.timer_show.setInterval(500)
        self.timer_show.timeout.connect(self.onShowTimerEnd)

        # delay hiding the result from the job.
        # if the job ran long enough to be shown
        # we want to see what it did.
        self.timer_delete = QTimer(self)
        self.timer_delete.setSingleShot(True)
        self.timer_delete.setInterval(2000)
        self.timer_delete.timeout.connect(self.onDeleteTimerEnd)

        self.job.finished.connect(self.onJobFinished)

        self.hbox = QHBoxLayout(self)
        self.hbox.addWidget(self.label)
        self.hbox.addWidget(self.pbar)

        self.setVisible(False)
        self.timer_show.start()

    def setProgress(self,iValue):
        self.pbar.setValue(iValue)

    def onJobFinished(self):
        if isinstance(self.job,LoadDirectoryJob):
            self.deleteJob.emit(self)
        elif self.isHidden():
            self.timer_show.stop()
        else:
            self.timer_delete.start()

    def onShowTimerEnd(self):
        self.setVisible(True)

    def onDeleteTimerEnd(self):
        self.deleteJob.emit(self)