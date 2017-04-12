

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.client.widgets.explorer.source import LazySourceListView
from yue.client.widgets.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, Dashboard, JobWidget

from yue.core.settings import Settings
from yue.client.widgets.Tab import Tab

from yue.explor.display import ExplorModel


class ExplorerView(Tab):

    primaryDirectoryChanged = pyqtSignal(str)
    secondaryDirectoryChanged = pyqtSignal(str)
    submitJob = pyqtSignal(Job)

    openAsTab = pyqtSignal(object,str)  # view, path
    openRemote = pyqtSignal(object,str)  # model, path

    directoryInfo = pyqtSignal(bool,int) # signature for now...

    def __init__(self, source, controller, parent=None):
        super(ExplorerView, self).__init__(parent)

        self.source = source
        self.controller = controller

        self.ex_main = ExplorModel( None, self.controller, self )
        self.ex_secondary = ExplorModel( None, self.controller, self )
        self.ex_secondary.btn_split.setIcon(QIcon(":/img/app_join.png"))

        self.ex_main.toggleSecondaryView.connect(self.onToggleSecondaryView)
        self.ex_secondary.toggleSecondaryView.connect(self.onToggleSecondaryView)

        self.ex_main.directoryChanged.connect(self.primaryDirectoryChanged)
        self.ex_secondary.directoryChanged.connect(self.secondaryDirectoryChanged)

        self.ex_main.submitJob.connect(self.onSubmitJob)
        self.ex_secondary.submitJob.connect(self.onSubmitJob)

        self.ex_main.infoNumFiles.connect(lambda n : self.onInfoNumFiles(True,n))
        self.ex_secondary.infoNumFiles.connect(lambda n : self.onInfoNumFiles(False,n))

        self.ex_main.openAsTab.connect(self.onOpenAsTab)
        self.ex_secondary.openAsTab.connect(self.onOpenAsTab)

        self.ex_main.openRemote.connect(self.onOpenRemote)
        self.ex_secondary.openRemote.connect(self.onOpenRemote)

        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(0,0,0,0)
        self.hbox.addWidget(self.ex_main)
        self.hbox.addWidget(self.ex_secondary)

        self.ex_main.showSplitButton(True)
        self.ex_secondary.hide()

    def onEnter(self):

        # delay creating the views until the tab is entered for the first
        # time, this slightly improves startup performance
        if self.ex_main.view is None:
            print("++ExplorerView onEnter", self.source.__class__.__name__)

            show_hidden = Settings.instance()['view_show_hidden']
            view1 = LazySourceListView(self.source,self.source.root(),show_hidden=show_hidden)
            view2 = LazySourceListView(self.source,self.source.root(),show_hidden=show_hidden)

            view1.loadDirectory.connect(lambda : self.onLazyLoadDirectory(self.ex_main))
            view2.loadDirectory.connect(lambda : self.onLazyLoadDirectory(self.ex_secondary))

            self.ex_main.setView(view1)
            self.ex_secondary.setView(view2)

            print("--ExplorerView onEnter", self.source.__class__.__name__)

    def onLazyLoadDirectory(self,model):

        job = LoadDirectoryJob(model)
        self.submitJob.emit(job)

    def chdir(self, path):

        # chdir can be called from another Tab, prior to onEnter,
        # if that happens run the onEnter first time setup.
        self.onEnter()

        self.ex_main.chdir(path)

    def chdir_r(self,path):

        self.onEnter()

        self.ex_secondary.chdir(path)

        if self.ex_secondary.isHidden():
            self.ex_secondary.show()
            self.ex_main.showSplitButton(False)
            self.ex_secondary.showSplitButton(True)

    def pwd(self):
        return self.ex_main.view.pwd()

    def pwd_r(self):
        return self.ex_secondary.view.pwd()

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

    def onSubmitJob(self,job):
        self.submitJob.emit(job)

    def onOpenAsTab(self,view,path):

        self.openAsTab.emit(view,path)

    def onOpenRemote(self,model,path):

        self.openRemote.emit(model,path)

    def onInfoNumFiles(self,onLeft,nFiles):

        self.directoryInfo.emit(onLeft,nFiles)
