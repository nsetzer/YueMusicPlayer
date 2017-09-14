#! python ../../explor.py C:\\Users\\Nick\\Documents\\playground C:\\Users\\Nick\\Documents\\playground


from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import os
import traceback
import math

from yue.core.settings import Settings

from yue.qtcommon.Tab import TabWidget
from yue.qtcommon.LineEdit import LineEditHistory

from yue.core.explorer.source import DirectorySource,SourceListView
from yue.core.explorer.sshsource import SSHClientSource
from yue.core.explorer.ftpsource import parseFTPurl, FTPSource
from yue.core.explorer.zipfs import ZipFS,isArchiveFile

from yue.qtcommon.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, Dashboard, JobWidget

from yue.explor.ui.quicklist import ShortcutEditDialog, QuickAccessTable
from yue.explor.ui.tabview import ExplorerView
from yue.explor.controller import ExplorController
from yue.explor.assoc import FileAssoc
from yue.explor.watchfile import WatchFileController, WatchFileTable
from yue.explor.dialog.sshcred import SshCredentialsDialog
from yue.explor.dialog.settings import SettingsDialog
from yue.explor.vagrant import getVagrantInstances,getVagrantSSH

""""
FTP protocol
    server:port
    url: ftp://server:port
    username
    password
    [] anonymous login -> ftp://anonymous@server:port
    ssh private key

File watcher protocol
    inotify too hard this early.
    create a list of files to watch,
    add a sync button that is only visible
    when there are remote files opened locally.

remote ssh directories
    export path, should return an ssh command that
    will cd into that directory. open a terminal
    and execute that command.

open terminal here
    hide this if the directory is not local or ssh

mount -t vboxsf -o uid=0,gid=0 vagrant /vagrant


copy jobs (and similar) need to clone the source/view.
    ordinarily this wouldnt be an issue
    ssh sources can lock up when one thread is fully
    utilizing the channel. Further more it is an assumption
    that sources are single threaded only -- so i am violating
    a basic assumption from the get go.
    clone needs to copy crednetials to establish a new one
    which incurs a heavy delay in some cases (blocking main thread)
    and some sources may not be cloneable at all. is there
    a way to get copy jobs to play fair?

    adding a thread safe layer to all sources may
    impact performance, but may be required

implement a find in files type feature...
    find . -name "*.java" | xargs grep -i "compute"
    maybe only for the local file system, or only for systems
    that implement the open API. need to solve the threading
    problem before this can be implementeds

copy paste a directory within  a directory fails...
    duplicates internal items instead of creating a new directory.


"""

class NewVagrantTabJob(Job):
    """docstring for NewVagrantTabJob"""

    newSource = pyqtSignal(object)

    def __init__(self, mainwindow, vagrant_dir):

        super(NewVagrantTabJob, self).__init__()
        self.mainwindow = mainwindow
        self.vagrant_dir = vagrant_dir

    def doTask(self):
        #vagrant_dir = "/Users/nsetzer/git/vagrant/cogito"
        #vagrant_dir = "/Users/nsetzer/git/Cogito/Product/EnterpriseCommonServices"


        cfg = getVagrantSSH(self.vagrant_dir)
        try:
            print("++create")
            src = SSHClientSource.fromPrivateKey(cfg['host'],cfg['port'],
                    cfg['user'],cfg['password'],cfg['key'])
            print("--create")
            self.newSource.emit(src)
        except ConnectionRefusedError as e:
            sys.stderr.write("error: %s\n"%e)

class Calculator(QWidget):
    """docstring for Calculator"""
    def __init__(self, parent=None):
        super(Calculator, self).__init__(parent)

        self.layout = QVBoxLayout(self);
        self.layout.setContentsMargins(16,0,16,0)
        self.input = LineEditHistory(self)
        self.output = QLabel(self);
        self.output.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.output.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed);

        self.input.accepted.connect(self.evaluate)
        self.layout.addWidget(self.input);
        self.layout.addWidget(self.output);

        self.globals = {"__builtins__":None}
        self.locals = {}
        for key in dir(math):
            if not key.startswith("_"):
                self.locals[key] = getattr(math,key);
        self.locals['ans'] = 0
        self.locals['abs'] = abs
        self.locals['ascii'] = ascii
        self.locals['bin'] = bin
        self.locals['bool'] = bool
        self.locals['chr'] = chr
        self.locals['complex'] = complex
        self.locals['divmod'] = divmod
        self.locals['float'] = float
        self.locals['hex'] = hex
        self.locals['int'] = int
        self.locals['max'] = max
        self.locals['min'] = min
        self.locals['oct'] = oct
        self.locals['ord'] = ord
        self.locals['pow'] = pow
        self.locals['round'] = round
        self.locals['str'] = str
        self.locals['sum'] = sum
        self.locals['fold'] = lambda initial,seq: sum(seq,initial)
        self.locals['sign'] = lambda x: 1 if x>=0 else -1
        self.locals['j'] = complex(0,1)
        #print(' '.join(list(self.locals.keys())))

    def evaluate(self,text):

        text=text.strip()
        if not text:
            return;

        try:
            result = eval(text,self.globals,self.locals);
            self.output.setText(str(result));
            self.locals["ans"] = result;
        except Exception as e:
            self.output.setText(str(e))

class MainWindow(QMainWindow):
    """docstring for MainWindow"""
    def __init__(self,defaultpath,defaultpath_r=""):
        """
        defaultpath: if empty default to the users home
        """
        super(MainWindow, self).__init__()

        self.splitter = QSplitter(self)

        self.pain_main = Pane(self)

        self.dashboard = Dashboard(self)

        # controller maintains state between tabs
        self.source = DirectorySource()
        self.controller = ExplorController( self )
        self.controller.forceReload.connect(self.refresh)
        self.controller.submitJob.connect(self.dashboard.startJob)

        self.btn_newTab = QToolButton(self)
        self.btn_newTab.clicked.connect(self.newTab)
        self.btn_newTab.setIcon(QIcon(":/img/app_plus.png"))

        self.quickview = QuickAccessTable(self)
        self.quickview.changeDirectory.connect(self.onChangeDirectory)
        self.quickview.changeDirectoryRight.connect(self.onChangeDirectoryRight)

        self.wfctrl = WatchFileController(self.source)
        self.wfctrl.watchersChanged.connect(self.onWatchersChanged)

        self.wfview = WatchFileTable(self.wfctrl,self)
        self.wfview.changeDirectory.connect(self.onChangeDirectory)

        self.tabview = TabWidget( self )
        self.tabview.tabBar().setMovable(True)
        self.tabview.setCornerWidget(self.btn_newTab)
        self.tabview.tabCloseRequested.connect(self.onTabCloseRequest)
        self.tabview.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)

        self.pain_main.addWidget(self.tabview)
        self.pain_main.addWidget(self.dashboard)

        self.calculator = Calculator(self)

        self.wview = QWidget()
        self.vbox_view = QVBoxLayout(self.wview)
        self.vbox_view.setContentsMargins(0,0,0,0)
        self.vbox_view.addWidget(self.quickview.container)
        self.vbox_view.addWidget(self.wfview.container)
        self.vbox_view.addWidget(self.calculator)
        self.splitter.addWidget(self.wview)
        self.splitter.addWidget(self.pain_main)

        self.setCentralWidget(self.splitter)

        # create the first tab
        self.newTab(defaultpath,defaultpath_r)

        self.xcut_refresh = QShortcut(QKeySequence(Qt.Key_Escape),self)
        self.xcut_refresh.activated.connect(self.refresh)

        self.initMenuBar()
        self.initStatusBar()

    def initMenuBar(self):

        menubar = self.menuBar()

        # each time the file menu is opened, invalidate
        # the vagrant menu. the vagrant menu results are cached
        # until the file menu is closed -- increasing resonse time
        self.invalidate_vagrant_menu = True

        self.file_menu = menubar.addMenu("File")
        self.file_menu.aboutToShow.connect(self.onAboutToShowFileMenu)

        act = self.file_menu.addAction("Preferences")
        act.triggered.connect(self.openSettings)

        act = self.file_menu.addAction("Open FTP")
        act.triggered.connect(self.newFtpTabTest)

        act = self.file_menu.addAction("Open SSH")
        act.triggered.connect(self.newSshTabTest)

        self.file_menu.addSeparator()

        if Settings.instance()['cmd_vagrant']:
            self.vagrant_menu = self.file_menu.addMenu("Vagrant SSH")
            self.vagrant_menu.aboutToShow.connect(self.initVagrantMenuBar)

        self.file_menu.addSeparator()


        act = self.file_menu.addAction("Sync")
        act.triggered.connect(self.onSyncRemoteFiles)

        act = self.file_menu.addAction("Clear Watch List")
        act.triggered.connect(self.onWatchersDelete)

        #act = menu.addAction("Open SSH+FTP")
        #act.triggered.connect(self.newSshTabTest)

        #act = menu.addAction("Open AWS")
        #act.triggered.connect(self.newSshTabTest)

        self.file_menu.addAction("Open SMB")
        self.file_menu.addSeparator()
        self.file_menu.addAction("Exit")

    def onAboutToShowFileMenu(self):
        self.invalidate_vagrant_menu = True

    def initVagrantMenuBar(self):

        if not self.invalidate_vagrant_menu:
            return

        self.vagrant_menu.clear()

        for dir in getVagrantInstances():
            _,n = os.path.split(dir)
            act = self.vagrant_menu.addAction(n)
            act.triggered.connect(lambda : self.newVagrantTab(dir))
            self.invalidate_vagrant_menu = False

    def initStatusBar(self):

        statusbar = self.statusBar()

        self.sbar_lbl_w_nfiles = QLabel() #watchers
        self.sbar_lbl_p_nfiles = QLabel() # delete me
        self.sbar_lbl_s_nfiles = QLabel() # delete me

        statusbar.addWidget(self.sbar_lbl_w_nfiles)
        statusbar.addWidget(self.sbar_lbl_p_nfiles)
        statusbar.addWidget(self.sbar_lbl_s_nfiles)

    def openSettings(self):

        dlg = SettingsDialog(self)
        dlg.exec_()

    def newFtpTabTest(self):

        url = "ftp://nsetzer:password@192.168.1.9:2121//"
        #url = "ftp://cogito:!bbn_kws#@e-ftp-02.bbn.com//"
        p = parseFTPurl(url)
        p['hostname'] = p['hostname'].replace("/","")

        print(p)
        try:
            print("enter")
            source=FTPSource(p['hostname'],p['port'],p['username'],p['password'])
            print("exit")
        except ConnectionRefusedError as e:
            sys.stderr.write("error: %s\n"%e)
        else:
            view = self._newTab(source)

            view.chdir(p['path'])

    def newVagrantTab(self,vagrant_dir):

        job = NewVagrantTabJob(self,vagrant_dir)
        job.newSource.connect(self.newTabFromSource)
        self.dashboard.startJob(job)

    def newTabFromSource(self,src):

        view = self._newTab(src)
        view.chdir(src.root())

    def newSshTabTest(self):

        dlg = SshCredentialsDialog()

        print("set")
        dlg.setConfig({
            "host":"192.168.1.9",
            "port":2222,
            "user":"admin",
            "password":"admin",
            })

        if not dlg.exec_():
            return;

        cfg = dlg.getConfig()

        try:
            print("++create")
            print(cfg)
            src = SSHClientSource.fromPrivateKey(cfg['host'],cfg['port'],
                    cfg['user'],cfg['password'],cfg['key'])
            print("--create")
        except Exception as e:
            for line in traceback.format_exception(exc_type,exc_value,exc_traceback):
                print(line)

            #sys.stderr.write("error: %s\n"%e)
            QMessageBox.critical(None,"Connection Error",str(e))
        else:
            view = self._newTab(src)
            view.chdir(src.root())
            return

    def newArchiveTab(self,view,path):

        name=view.split(path)[1]
        #zfs = ZipFS(view.open(path,"rb"),name)
        zfs = ZipFS(path,name)
        view = self._newTab(zfs,':/img/app_archive.png')
        view.chdir("/")

    def newTab(self,defaultpath="~",defaultpath_r=""):
        view = self._newTab(self.source)

        view.ex_main.clearHistory()
        if defaultpath:
            view.chdir(defaultpath)
        else:
            view.chdir("~")

        if defaultpath_r:
            view.chdir_r(defaultpath_r)
        else:
            view.ex_secondary.chdir(view.pwd_r())

    def _newTab(self,source,icon_path=':/img/app_folder.png'):
        view = ExplorerView(source,self.controller,self)

        view.primaryDirectoryChanged.connect(lambda path: self.onDirectoryChanged(view,path))
        view.submitJob.connect(self.dashboard.startJob)
        view.openAsTab.connect(self.newArchiveTab)
        view.openRemote.connect(lambda model,path :self.onOpenRemote(view,model,path))
        view.directoryInfo.connect(self.onUpdateStatus)

        self.tabview.addTab(view,QIcon(icon_path),"temp name")

        self.tabview.setTabsClosable(self.tabview.count()>1)

        self.tabview.setCurrentWidget(view)

        return view

    def showWindow(self):

        geometry = QDesktopWidget().screenGeometry()
        sw = geometry.width()
        sh = geometry.height()
        # calculate default values
        dw = int(sw*.6)
        dh = int(sh*.6)
        dx = sw//2 - dw//2
        dy = sh//2 - dh//2
        # use stored values if they exist
        cw = 0#s.getDefault("window_width",dw)
        ch = 0#s.getDefault("window_height",dh)
        cx = -1#s.getDefault("window_x",dx)
        cy = -1#s.getDefault("window_y",dy)
        # the application should start wholly on the screen
        # otherwise, default its position to the center of the screen
        if cx < 0 or cx+cw>sw:
            cx = dx
            cw = dw
        if cy < 0 or cy+ch>sh:
            cy = dy
            ch = dh
        if cw <= 0:
            cw = dw
        if ch <= 0:
            ch = dh
        self.resize(cw,ch)
        self.move(cx,cy)
        self.show()

        # somewhat arbitrary
        # set the width of the quick access view to something
        # reasonable
        lw = 200
        if cw > lw*2:
            self.splitter.setSizes([lw,cw-lw])

    def onDirectoryChanged(self,view,path):

        index = self.tabview.indexOf(view)
        _,name = view.source.split(path)
        if name :
            self.tabview.setTabText(index,name)
        else:
            self.tabview.setTabText(index,"root")

    def onChangeDirectory(self,path):
        w = self.tabview.currentWidget()
        if not isinstance(w.source,DirectorySource):
            # open a new tab to display the given path
            # TODO consider passing a source allong with the path in the signal
            self.newTab(path)
        else:
            w.chdir(path)

    def onChangeDirectoryRight(self,path):
        w = self.tabview.currentWidget()
        if not isinstance(w.source,DirectorySource):
            # open a new tab to display the given path
            # TODO consider passing a source allong with the path in the signal
            self.newTab("~",path)
        else:
            w.chdir_r(path)

    def onTabCloseRequest(self,idx):
        self.tabview.removeTab(idx)
        self.tabview.setTabsClosable(self.tabview.count()>1)

    def refresh(self):
        w = self.tabview.currentWidget()
        w.refresh()

    def onShowSecondaryWindow(self,bShow):

        w = self.tabview.currentWidget()
        if bShow:
            w.ex_secondary.show()
            w.ex_main.showSplitButton(False)
            w.ex_secondary.showSplitButton(True)
        else:
            w.ex_secondary.hide()
            w.ex_main.showSplitButton(True)
            w.ex_secondary.showSplitButton(False)

    def onUpdateStatus(self,onLeft,nFiles):
        if onLeft:
            self.sbar_lbl_p_nfiles.setText("nfiles: %d"%nFiles)
        else:
            self.sbar_lbl_s_nfiles.setText("nfiles: %d"%nFiles)

    def onOpenRemote(self, tab, display, path):

        src = DirectorySource()
        view = display.view
        dtemp = src.join(Settings.instance()['database_directory'],"remote")
        src.mkdir(dtemp)

        remote_dname,remote_fname = view.split(path)
        ftemp = src.join(dtemp,remote_fname)

        with src.open(ftemp,"wb") as wb:
            view.getfo(path,wb)

        display._action_open_file_local(src,ftemp)

        self.wfctrl.addFile(ftemp,view,path)

    def onWatchersChanged(self,nfiles):

        self.sbar_lbl_w_nfiles.setText("watching: %d"%nfiles)

    def onWatchersDelete(self):
        self.wfctrl.clear()

    def onSyncRemoteFiles(self):

        self.wfctrl.onPostAll()

class Pane(QWidget):
    """docstring for Pane"""
    def __init__(self, parent):
        super(Pane, self).__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

    def addWidget(self,widget):
        self.vbox.addWidget(widget)

