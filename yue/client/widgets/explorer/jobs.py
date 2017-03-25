
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from enum import Enum

from yue.core.explorer.source import DirectorySource,SourceListView
from yue.core.explorer.fsutil import generateUniquePath, \
    walk_files, iter_copy, source_copy, \
    iter_remove
from yue.core.util import format_bytes

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

    def doTask(self):

        for i,(src,dst) in enumerate(self.args):
            src=self.view.normpath(src,self.wd)
            dst=self.view.normpath(dst,self.wd)
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


        self.calculate_totals()

        print(self.tot_size,self.num_files)

        self.getInput("title",format_bytes(self.tot_size))

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

        print("copy",dst_path)
        self.dst_view.mkdir( dst_dir )
        source_copy(self.src_view,src_path, \
                    self.dst_view,dst_path,self.chunksize)

        #print(self.showDialog(JobMessageType.Question,"hello world"))

class MoveJob(Job):
    def __init__(self, src_view, src_paths, dst_path):
        """ args as list of 2-tuple (src,tgt)

        rename the set of files in the cwd.
        """
        super(MoveJob, self).__init__()
        self.view = src_view
        self.src_paths = src_paths
        self.dst_path = dst_path

    def doTask(self):
        for i,path in enumerate(self.src_paths):

            name = self.view.split(path)[1]
            dst_path = self.view.join(self.dst_path,name)
            dst_path = generateUniquePath(self.view,dst_path)

            self.move_one(path,dst_path)

            self.setProgress(100*(i+1)/len(self.src_paths))

    def move_one(self,src_path,dst_path):
        """ this could be reimplented, say to update a database? """

        self.view.move(src_path,dst_path)

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
    def __init__(self, model):
        super(LoadDirectoryJob, self).__init__()
        self.model = model
        self.view = model.view

    def doTask(self):

        try:
            data = self.view.source.listdir(self.view.path)

            if self.view.show_hidden:
                data =  [ x for x in data ]
            else:
                data =  [ x for x in data if not self.view.source.hidden(x) ]

            data = self.view._sort(data) # and assignt to this instance

            if self.view.path != self.view.root():
                data.insert(0,"..")

        except OSError as e:
            data = []
            self.getInput("Access Error",str(e), ["Ok"])

        self.model.onLoadComplete(data)



class Dashboard(QWidget):
    """the Dashboard is where long running jobs are displayed

    A job is started and displayed with a progress bar in the dashboard.
    this allows the user to cancel the job if needed. when the job
    completes it is removed from the dashboard.
    """
    def __init__(self, parent):
        super(Dashboard, self).__init__(parent)

        self.job_runner = JobRunner(self)

        #self.setHidden(True)

        self.vbox = QVBoxLayout(self)

        self.widgets = []

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

        self.timer_delete = QTimer(self)
        self.timer_delete.setSingleShot(True)
        self.timer_delete.setInterval(2000)
        self.timer_delete.timeout.connect(self.onTimerEnd)

        self.job.finished.connect(self.onJobFinished)

        self.hbox = QHBoxLayout(self)
        self.hbox.addWidget(self.label)
        self.hbox.addWidget(self.pbar)

    def setProgress(self,iValue):
        print(iValue)
        self.pbar.setValue(iValue)

    def onJobFinished(self):
        if isinstance(self.job,LoadDirectoryJob):
            self.deleteJob.emit(self)
        else:
            print("start timer")
            self.timer_delete.start()

    def onTimerEnd(self):
        print("delete job (timer)")

        self.deleteJob.emit(self)