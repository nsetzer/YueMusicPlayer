

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback

from yue.qtcommon.LineEdit import LineEdit
from yue.core.explorer.source import DirectorySource
from yue.core.util import format_date, format_bytes, format_mode

from yue.qtcommon.explorer.ContextBar import ContextBar

from yue.qtcommon.explorer.filetable import ResourceManager
from yue.qtcommon.explorer.jobs import Job, \
    RenameJob, CopyJob, MoveJob, DeleteJob, DropRequestJob

from yue.core.settings import Settings

from yue.qtcommon.explorer.source import LazySourceListView

class LineEdit_Path(LineEdit):

    def __init__(self,parent,table):
        super(LineEdit_Path,self).__init__(parent)
        self.table = table

    def keyReleaseEvent(self,event=None):
        super(LineEdit_Path,self).keyReleaseEvent(event)
        if event.key() == Qt.Key_Down:
            self.table.clearSelection( )
            self.table.setSelection( [0,] )
            self.table.scrollTo(0)
            self.table.update()
            self.table.setFocus()

    def keyReleaseEnter(self,text):
        self.table.scrollTo(0)
        self.parent().chdir( self.text() )

class ContextBarPath(ContextBar):

    #  http://doc.qt.io/qt-5/qcombobox.html#lineEdit

    def __init__(self,parent,controller,table):
        super(ContextBarPath,self).__init__(parent)
        self.table = table
        self.controller = controller

        self.installEventFilter(self)

    def keyReleaseEvent(self,event=None):
        super(ContextBarPath,self).keyReleaseEvent(event)
        if event.key() == Qt.Key_Down:
            self.table.clearSelection( )
            self.table.setSelection( [0,] )
            self.table.scrollTo(0)
            self.table.update()
            self.table.setFocus()

    def keyReleaseEnter(self,text):
        self.table.scrollTo(0)
        self.parent().chdir( self.text() )

    def eventFilter(self,target,event):
        if target == self and event.type() == QEvent.MouseButtonPress:
            self.fillComboBox()
        return False

    def fillComboBox(self):
        text = self.text()
        views = self.controller.getContextPaths();

        # todo, build a unique set of directory source views
        # and build the list of non-directory source views
        # and their paths.
        self.clear();
        self.addItem(text,None)
        for i,view in enumerate(views):
            self.addItem(view.pwd(),view)

class ExplorerModel(QWidget):
    """docstring for MainWindow"""

    # TODO: ExplorerModel should be renamed "ExplorerDisplayBase"
    # an ExplorerDisplayBase combines the source/view (model) of the directory
    # with a set of qt widgets (view on the model)

    directoryChanged = pyqtSignal(str)

    toggleSecondaryView = pyqtSignal()

    submitJob = pyqtSignal(Job)

    infoNumFiles = pyqtSignal(int)

    filterFiles = pyqtSignal(str)

    # emitted when the source for the current view is changed
    viewSourceChanged = pyqtSignal(object)

    def __init__(self, view, controller, parent=None):
        super(ExplorerModel, self).__init__(parent)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.hbox = QHBoxLayout()
        self.hbox.setContentsMargins(0,0,0,0)

        self.view = view
        self.controller = controller

        self.tbl_file = self._getNewFileTable(view)

        self.tbl_file.focusUp.connect(self.onTableFocusUp)

        self.tbl_file.selection_changed.connect(self.onTableSelectionChanged)
        self.tbl_file.deletePaths.connect(lambda lst:self.controller.action_delete(self,lst))

        self.txt_path = ContextBarPath(self, controller, self.tbl_file)

        self.lbl_viewName = QLabel("");
        self.lbl_viewName.setAlignment(Qt.AlignCenter)

        self.txt_path.currentIndexChanged.connect(self.onContextIndexChanged)

        self.txt_path.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Minimum)
        #self.txt_path.textEdited.connect(self.onTextChanged)

        self.txt_filter = LineEdit(self)
        self.txt_filter.setPlaceholderText("filter")
        self.txt_filter.setText("")
        self.txt_filter.textEdited.connect(self.onFilterTextChanged)

        self.tbl_file.focusQuery.connect(lambda:self.txt_filter.setFocus(Qt.ShortcutFocusReason))

        self.btn_split = QToolButton(self)
        self.btn_split.setIcon(QIcon(":/img/app_split.png"))
        self.btn_split.setHidden(True)
        self.btn_split.clicked.connect( self.on_splitButton_clicked )

        self.btn_prev = QToolButton(self)
        self.btn_prev.clicked.connect( self.chdir_prev )
        self.btn_prev.setStyleSheet("""
            QToolButton {
                background:url(":/img/app_prev.png");
                background-repeat: no-repeat;
                background-position: center;
            }
            QToolButton::disabled {
                background:url(":/img/app_prev_disabled.png");
                background-repeat: no-repeat;
                background-position: center;
            }
        """)
        self.btn_next = QToolButton(self)
        self.btn_next.clicked.connect( self.chdir_next )
        self.btn_next.setStyleSheet("""
            QToolButton {
                background:url(":/img/app_next.png");
                background-repeat: no-repeat;
                background-position: center;
            }
            QToolButton::disabled {
                background:url(":/img/app_next_disabled.png");
                background-repeat: no-repeat;
                background-position: center;
            }
        """)

        self.btn_parent = QToolButton(self)
        self.btn_parent.clicked.connect( self.chdir_parent )
        self.btn_parent.setStyleSheet("""
            QToolButton {
                background:url(":/img/app_up.png");
                background-repeat: no-repeat;
                background-position: center;
            }
            QToolButton::disabled {
                background:url(":/img/app_up_disabled.png");
                background-repeat: no-repeat;
                background-position: center;
            }
        """)

        self.btn_refresh = QToolButton(self)
        self.btn_refresh.clicked.connect( self.action_refresh )
        #self.btn_refresh.setIcon(QIcon(':/img/app_plus.png'))
        self.btn_refresh.setStyleSheet("""
            QToolButton {
                background:url(":/img/app_refresh.png");
                background-repeat: no-repeat;
                background-position: center;
            }
        """)

        self.lbl_st_nfiles = QLabel("",self)
        self.lbl_st_nsel   = QLabel("",self)
        #self.lbl_st_src    = QLabel("",self)
        self.hbox_st = QHBoxLayout()
        #self.hbox_st.addWidget(self.lbl_st_src)
        self.hbox_st.addWidget(self.lbl_st_nfiles)
        self.hbox_st.addWidget(self.lbl_st_nsel)
        self.hbox_st.addStretch(1)

        self.hbox.addWidget(self.btn_refresh)
        self.hbox.addWidget(self.btn_parent)
        self.hbox.addWidget(self.btn_prev)
        self.hbox.addWidget(self.btn_next)
        self.hbox.addStretch(1)
        self.hbox.addWidget(self.txt_filter)
        self.hbox.addWidget(self.btn_split)
        self.vbox.addLayout( self.hbox )
        self.vbox.addWidget( self.lbl_viewName )
        self.vbox.addWidget( self.txt_path )
        self.vbox.addWidget( self.tbl_file.container )
        self.vbox.addLayout( self.hbox_st )

        self.directory_history = []
        self.directory_history_index = 0

        #self.tbl_file.setData(self.view)
        #self.txt_path.setText(self.view.pwd())

        self.slow_data_history = {}

        # this is set to a name that should be selected after a load completes
        self.chdir_on_load_select = None

        self.viewSourceChanged.connect(self.onViewSourceChanged)

    def _getNewFileTable(self,view):
        raise NotImplementedError("return a table in a subclass")

    def setView(self,view):
        self.view = view
        self.tbl_file.view = view
        self.tbl_file.setData(view)
        self.txt_path.setText(view.pwd())

        self.directory_history = [view.pwd(),]

        self.viewSourceChanged.emit(view)

    def showSplitButton(self,bShow):
        self.btn_split.setHidden(not bShow)

    def refresh(self,resetScroll=True):
        self.chdir( self.view.pwd() ,resetScroll)

    def clearHistory(self):
        self.directory_history = []
        self.directory_history_index = 0

    def chdir(self,path,resetScroll=True):
        return self._chdir(path,True,resetScroll)

    def _chdir(self,path,push,resetScroll=True):
        pwd = self.view.pwd()
        success = False
        try:

            if not self.view.exists(path):
                print(type(self.view),path)
                QMessageBox.critical(self,"Access Error","Error Opening:\n`%s`\nDirectory Does Not Exist"%path)
                return;


            self.view.chdir(path)

            # only push if the path is valid
            if push:
                if self.directory_history_index > 0:
                    index = len(self.directory_history) - self.directory_history_index
                    if 0<=index<len(self.directory_history):
                        self.directory_history = self.directory_history[:index]
                    self.directory_history_index = 0
                path = self.view.pwd()
                # dont push if the path is the same
                if len(self.directory_history)==0 or \
                    path != self.directory_history[-1]:
                    self.directory_history.append(self.view.pwd())

                if len(self.directory_history)>20:
                    self.directory_history = self.directory_history[-20:]

            self.directoryChanged.emit(self.view.pwd())

            self.slow_data_history = {}

            success = True

        except OSError as e:
            sys.stderr.write(str(e))
            QMessageBox.critical(self,"Access Error","Error Opening\n:`%s`\nOS Error"%path)
            s='->'.join([s[2] for s in traceback.extract_stack()])
            print("_chdir OS error:",path,name)
            print(s)

        self.btn_next.setDisabled(self.directory_history_index == 0)
        self.btn_prev.setDisabled(self.directory_history_index == len(self.directory_history)-1)

        self.txt_path.setText(self.view.pwd())

        self.tbl_file.update()
        if resetScroll:
            self.tbl_file.scrollTo(0)

        return success

    def chdir_prev(self):
        if self.directory_history_index < len(self.directory_history):
            self.directory_history_index += 1
            index = len(self.directory_history) - self.directory_history_index - 1
            if 0<=index<len(self.directory_history):
                path = self.directory_history[index]
                self._chdir(path,False)

    def chdir_next(self):
        if self.directory_history_index > 0:
            self.directory_history_index -= 1
            index = len(self.directory_history) - self.directory_history_index - 1
            if 0<=index<len(self.directory_history):
                path = self.directory_history[index]
                self._chdir(path,False)

    def chdir_parent(self):
        # change to the parent directory then select
        # this directory in the file listing
        cwd = self.view.pwd()
        _,cwn = self.view.split(cwd)
        path=self.view.parent(self.view.pwd())
        self._chdir(path,True)

        self.chdir_on_load_select = cwn

    def dropEvent(self,model,src_view,urls):
        # model and src_view can be none if drop comes from outside
        # the application
        job=DropRequestJob(src_view,urls,self.view,self.view.pwd())
        job.finished.connect(self.action_refresh)
        if model:
            job.finished.connect(model.action_refresh)
        self.controller.submitJob.emit(job)

    def getSlowData(self,item,field):
        #cache slow data for pwd to prevent hitting the disk
        name = item['name']
        if name not in self.slow_data_history:
            try:
                self.slow_data_history[name] = self.view.stat(name)
            except (FileNotFoundError,OSError) as e:
                self.slow_data_history[name] = {
                                                "isDir" : item['isDir'],
                                                "isLink" : False,
                                                "mtime" : 0,
                                                "ctime" : 0,
                                                "size"  : 0,
                                                "name"  : name,
                                                "mode"  : 0,
                                            }
        return self.slow_data_history[name][field]

    def showHiddenFiles(self):
        return self.view.show_hidden

    def action_set_hidden_visible(self,bVisible):
        self.view.setShowHidden(bVisible)
        self.refresh()

    def action_open_directory(self):
        pass

    def action_file(self, item):
        # double click file action
        path = self.view.realpath(item['name'])
        cmdstr = Settings.instance()['cmd_open_native']
        os.system(cmdstr%path)

    def action_rename_begin(self, items):

        row = list(self.tbl_file.selection)[0]
        col = -1
        for idx,column in enumerate(self.tbl_file.columns):
            if column.name == "File Name":
                col = idx
        if col < 0:
            return;

        opts = self.tbl_file.columns[col].get_default_opts(row)
        if opts:
            self.tbl_file.columns[col].editor_start(*opts)

    def action_rename(self,jobs):

        # a move on a SourceListView updates in place, requiring
        # only to repaint the table.
        # reunning the job in this thread enables editing multiple
        # files by using the arrow keys
        job = RenameJob(self.view,jobs)
        # job will not emit finished if run directly
        job.doTask()
        self.onRenameFinished()
        self.tbl_file.update()
        #job.finished.connect(self.onJobFinished)
        #self.submitJob.emit(job)

    def action_touch_begin(self):
        self.action_create(1)

    def action_touch(self,name):
        try:
            self.view.open(name,"w").close()
            self.chdir_on_load_select = name
        finally:
            self.refresh()

    def action_mkdir_begin(self):
      self.action_create(2)

    def action_mkdir(self,name):
        try:
            self.view.mkdir(name)
            self.chdir_on_load_select = name
        finally:
            self.refresh()

    def action_create(self,mode):

        isDir = mode==2
        name = "Empty File" if mode == 1 else "New Directory"
        index,name = self.view.new(name,isDir)
        col = -1
        for idx,column in enumerate(self.tbl_file.columns):
            if column.name == "File Name":
                col = idx
        if col < 0:
            return;

        self.tbl_file.scrollTo(index)

        self.tbl_file.columns[col].editor_start(set([index,]),name,mode)

    def action_copy_path(self,item):

        path = self.view.realpath(item['name'])
        QApplication.instance().clipboard().setText(path)

    def action_copy_path_name(self,item):
        QApplication.instance().clipboard().setText(item['name'])

    def action_paste(self):
        self.controller.action_paste(self.view,self.view.pwd())

    def action_refresh(self):

        self.chdir( self.view.pwd() )
        self.tbl_file.scrollTo(0)
        self.tbl_file.setSelection([])

    def action_update_replace(self, item):
        self.controller.action_update_replace( self.view.realpath(item['name']) )

    def on_splitButton_clicked(self):
        self.toggleSecondaryView.emit()

    def canPaste( self ):
        return self.controller.canPaste( self.view.pwd() )

    def item2img(self,item):

        l = ResourceManager.LINK if item['isLink'] else 0
        if item['isDir']:
            return ResourceManager.instance().get(l|ResourceManager.DIRECTORY)

        _,ext = self.view.splitext(item['name'])
        return ResourceManager.instance().get(l|ResourceManager.instance().getExtType(ext))

    def action_open_file(self, item):
        # TODO this function seems inappropriate
        self.controller.action_open_file( self.view.realpath(item['name']) )

    def onJobFinished(self):

        self.tbl_file.setSelection([])

        self.refresh(resetScroll=False)

    def onDeleteJobFinished(self):

        self.tbl_file.setSelection([])

        self.tbl_file.update()

    def onLoadComplete(self,data):
        self.view.setData(data)
        self.tbl_file.setData(self.view)

        self._update_status_text()

        if self.chdir_on_load_select:
            try:
                index = self.view.index(self.chdir_on_load_select)

                self.tbl_file.setSelection({index,})
                self.tbl_file.scrollTo(index)
            except ValueError:
                pass

            self.chdir_on_load_select = None

    def onFilterTextChanged(self,text):
        self.filterFiles.emit(text)
        self.view.setTextFilter(text)
        self.tbl_file.update()
        self.tbl_file.scrollTo(0)

        self._update_status_text()

    def onTableSelectionChanged(self):
        nsel = len(self.tbl_file.selection)
        if nsel > 0:
            self.lbl_st_nsel.setText("%d selected"%nsel)
        else:
            self.lbl_st_nsel.setText("")

    def _update_status_text(self):
        nd = 0
        for item in self.view:
            if item['isDir']:
                nd += 1
        nf0= len(self.view.data)-nd
        nf1= len(self.view.data_filtered)-nd

        ntxt = []
        if nd > 0:
            ntxt.append("%d dirs"%nd)
        if nf1 < nf0:
            ntxt.append("%d of %d files"%(nf1,nf0))
        else:
            ntxt.append("%d files"%(nf0))

        self.lbl_st_nfiles.setText(' | '.join(ntxt))

        #n = self.view.name()
        #self.lbl_st_src.setText(n)

        return

    def onRenameFinished(self):
        pass

    def onTableFocusUp(self):
        self.txt_path.setFocus()

    def onContextIndexChanged(self,index):
        # todo expand support for different view types
        # I need to build out a way for views to be closed
        # when there are no more references.
        view = self.txt_path.itemData(index)

        if view is not None:
            # bit of a hack here
            # replace the source, then change directories
            # this preserves any signals attached to the view.
            # anything dependant on the old source must be reset to
            # the factory default

            # TODO: this may need to clear copy/cut/paste buffers
            #
            self.view.source = view.source
            self.directory_history = []
            self.chdir(view.pwd())

            self.viewSourceChanged.emit(self.view)

    def onViewSourceChanged(self,view):

        if not isinstance(view.source,DirectorySource):
            self.lbl_viewName.setText(view.name())
            self.lbl_viewName.setHidden(False)
        else:
            self.lbl_viewName.setHidden(True)

