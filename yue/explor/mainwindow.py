
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import os

from yue.core.settings import Settings

from yue.client.widgets.Tab import TabWidget

from yue.core.explorer.source import DirectorySource,SourceListView
from yue.core.explorer.ftpsource import parseFTPurl, FTPSource
from yue.core.explorer.zipfs import ZipFS,isArchiveFile

#from yue.core.util import format_date, format_bytes, format_mode
#from yue.client.widgets.LargeTable import TableColumn, TableColumnImage
#from yue.client.widgets.TableEditColumn import EditColumn

from yue.client.widgets.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, Dashboard, JobWidget

from yue.explor.quicklist import ShortcutEditDialog, QuickAccessTable
from yue.explor.tabview import ExplorerView
from yue.explor.controller import ExplorController
from yue.explor.assoc import FileAssoc

class SettingsDialog(QDialog):
    """docstring for SettingsDialog"""
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,8,16,8)

        self.grid = QGridLayout()

        self.edit_tools =[]
        for i,(s,n) in enumerate([ ("cmd_edit_text","Text Editor"),
                                   ("cmd_edit_image","Image Editor"),
                                   ("cmd_open_native","Open Native"),
                                   ("cmd_launch_terminal","Open Terminal"),
                                   ("cmd_diff_files","Diff Tool")]):
            edit = QLineEdit(self)
            edit.setText(Settings.instance()[s])
            edit.setCursorPosition(0)
            self.grid.addWidget(QLabel(n,self),i,0)
            self.grid.addWidget(edit,i,1)

        self.btn_accept = QPushButton("Save",self)
        self.btn_cancel = QPushButton("Cancel",self)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.hbox_btns = QHBoxLayout()
        self.hbox_btns.setContentsMargins(0,0,0,0)
        self.hbox_btns.addStretch(1)
        self.hbox_btns.addWidget(self.btn_accept)
        self.hbox_btns.addWidget(self.btn_cancel)

        self.vbox.addLayout(self.grid)
        self.vbox.addLayout(self.hbox_btns)

class MainWindow(QMainWindow):
    """docstring for MainWindow"""
    def __init__(self,defaultpath,defaultpath_r=""):
        """
        defaultpath: if empty default to the users home
        """
        super(MainWindow, self).__init__()

        self.splitter = QSplitter(self)

        self.pain_main = Pane(self)

        self.btn_newTab = QToolButton(self)
        self.btn_newTab.clicked.connect(self.newTab)
        self.btn_newTab.setIcon(QIcon(":/img/app_plus.png"))

        self.quickview = QuickAccessTable(self)
        self.quickview.changeDirectory.connect(self.onChangeDirectory)
        self.quickview.changeDirectoryRight.connect(self.onChangeDirectoryRight)

        self.tabview = TabWidget( self )
        self.tabview.setCornerWidget(self.btn_newTab)
        self.tabview.tabCloseRequested.connect(self.onTabCloseRequest)
        self.tabview.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)


        self.dashboard = Dashboard(self)

        self.pain_main.addWidget(self.tabview)
        self.pain_main.addWidget(self.dashboard)

        self.splitter.addWidget(self.quickview.container)
        self.splitter.addWidget(self.pain_main)

        self.setCentralWidget(self.splitter)

        # controller maintains state between tabs
        self.source = DirectorySource()
        self.controller = ExplorController( )
        self.controller.forceReload.connect(self.refresh)

        self.controller.submitJob.connect(self.dashboard.startJob)

        # create the first tab
        self.newTab(defaultpath,defaultpath_r)

        self.xcut_refresh = QShortcut(QKeySequence(Qt.Key_Escape),self)
        self.xcut_refresh.activated.connect(self.refresh)

        self.initMenuBar()
        self.initStatusBar()

    def initMenuBar(self):

        menubar = self.menuBar()

        menu = menubar.addMenu("File")
        act = menu.addAction("Preferences")
        act.triggered.connect(self.openSettings)

        menu.addSeparator()
        act = menu.addAction("Open FTP")
        act.triggered.connect(self.newFtpTabTest)

        menu.addAction("Open SMB")
        menu.addSeparator()
        menu.addAction("Exit")

    def initStatusBar(self):

        statusbar = self.statusBar()

        self.sbar_lbl_p_nfiles = QLabel()
        self.sbar_lbl_s_nfiles = QLabel()

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
        w.chdir(path)

    def onChangeDirectoryRight(self,path):
        w = self.tabview.currentWidget()
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

class Pane(QWidget):
    """docstring for Pane"""
    def __init__(self, parent):
        super(Pane, self).__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

    def addWidget(self,widget):
        self.vbox.addWidget(widget)

