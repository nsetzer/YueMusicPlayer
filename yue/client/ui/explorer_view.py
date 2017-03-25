#! python35 ../../../test/test_client.py $this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import traceback

from yue.core.util import format_date, format_bytes

import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

import yue
from yue.client.widgets.LargeTable import LargeTable, TableColumn, TableDualColumn, TableColumnImage
from yue.client.widgets.TableEditColumn import EditColumn
from yue.client.widgets.LineEdit import LineEdit
from yue.client.widgets.FlatPushButton import FlatPushButton
from yue.client.widgets.Tab import Tab
from yue.client.widgets.explorer.jobs import Job, JobRunner, \
    RenameJob, CopyJob, MoveJob, DeleteJob, LoadDirectoryJob, Dashboard, JobWidget
from yue.core.util import format_date, format_bytes, format_mode
from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library

from yue.client.ui.ingest_dialog import IngestProgressDialog
from yue.client.ui.movefile_dialog import MoveFileProgressDialog
from yue.client.ui.rename_dialog import RenameDialog
from yue.core.explorer.source import DirectorySource,SourceListView
from yue.core.explorer.ftpsource import parseFTPurl, FTPSource

"""
TODO:

    model/controller needs better separation

    there is no reason to have an aciton_* methods on the model
    but then each controller.action_* must be passed the acting view.

"""

def explorerOpen( url ):

    if os.name == "nt":
        os.startfile(url);
    elif sys.platform == "darwin":
        os.system("open %s"%url);
    else:
        # could also use kde-open, gnome-open etc
        # TODO: implement code that tries each one until one works
        #subprocess.call(["xdg-open",filepath])
        sys.stderr.write("open unsupported on %s"%os.name)

class LineEdit_Path(LineEdit):

    def __init__(self,parent,table):
        super(LineEdit_Path,self).__init__(parent)
        self.table = table

    def keyReleaseEvent(self,event=None):
        super(LineEdit_Path,self).keyReleaseEvent(event)
        if event.key() == Qt.Key_Down:
            self.table.clearSelection( )
            self.table.setSelection( [0,] )
            self.table.update(0)
            self.table.setFocus()

    def keyReleaseEnter(self,text):
        self.table.scrollTo(0)
        self.parent().chdir( self.text(), True )

class ResourceManager(object):
    """docstring for ResourceManager"""
    _instance = None

    LINK      = 0x100
    DIRECTORY = 0x001
    FILE      = 0x002
    SONG      = 0x003
    ARCHIVE   = 0x004

    LINK_DIRECTORY = 0x101
    LINK_FILE      = 0x102
    LINK_SONG      = 0x103
    LINK_ARCHIVE   = 0x104

    @staticmethod
    def instance():
        # TODO: not thread safe....
        if ResourceManager._instance is None:
            ResourceManager._instance = ResourceManager()
        return ResourceManager._instance

    def __init__(self):
        super(ResourceManager, self).__init__()
        self.resources = {}
        self.resources[ResourceManager.FILE]      = QPixmap(':/img/app_file.png')
        self.resources[ResourceManager.SONG]      = QPixmap(':/img/app_song.png')
        self.resources[ResourceManager.DIRECTORY] = QPixmap(':/img/app_folder.png')
        self.resources[ResourceManager.ARCHIVE]   = QPixmap(':/img/app_archive.png')

        self.img_link = QPixmap(':/img/app_shortcut.png')

        for res in [ResourceManager.FILE,ResourceManager.SONG,
                    ResourceManager.DIRECTORY,ResourceManager.ARCHIVE]:
            img = self.compose(self.resources[res],self.img_link)
            self.resources[ResourceManager.LINK|res] = img

        self.map_ext = dict()

        for ext in Song.supportedExtensions():
            self.map_ext[ext] = ResourceManager.SONG

        for ext in [".gz",".zip",".7z",".rar",".iz"]:
            self.map_ext[ext] = ResourceManager.ARCHIVE

    def compose(self,imga,imgb):

        imgc = QImage(imga.size(), QImage.Format_ARGB32_Premultiplied);
        painter = QPainter(imgc);

        painter.setCompositionMode(QPainter.CompositionMode_Source);
        painter.fillRect(imgc.rect(), Qt.transparent);

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver);
        painter.drawPixmap(0, 0, imga);

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver);
        painter.drawPixmap(0, 0, imgb);

        painter.end();

        return QPixmap.fromImage(imgc);

    def get(self,kind):
        return self.resources[kind]

    def getExtType(self,ext):
        return self.map_ext.get(ext,ResourceManager.FILE)

    def width(self):
        return self.resources[ResourceManager.FILE].width()

class ExplorerFileTable(LargeTable):
    """
    """
    renamePaths = pyqtSignal(object) # given a list of jobs
    createFile = pyqtSignal(str)
    createDirectory = pyqtSignal(str)


    def __init__(self, view, parent=None):
        super(ExplorerFileTable,self).__init__(parent)
        self.view = view

        self.position_stack = []

        self.xcut_copy = QShortcut(QKeySequence("Ctrl+C"), self)
        self.xcut_copy.setContext(Qt.WidgetShortcut)
        self.xcut_copy.activated.connect(self.onShortcutCopy)

        self.xcut_cut = QShortcut(QKeySequence("Ctrl+X"), self)
        self.xcut_cut.setContext(Qt.WidgetShortcut)
        self.xcut_cut.activated.connect(self.onShortcutCut)

        self.xcut_paste = QShortcut(QKeySequence("Ctrl+V"), self)
        self.xcut_paste.setContext(Qt.WidgetShortcut)
        self.xcut_paste.activated.connect(self.onShortcutPaste)

        self.xcut_refresh = QShortcut(QKeySequence("F5"), self)
        self.xcut_refresh.activated.connect(self.onShortcutRefresh)


    def initColumns(self):

        """
        self.columns.append( TableColumnImage(self,'isDir',"Icon") )
        self.columns[-1].setShortName("")
        self.columns[-1].setTextTransform( lambda item,_ : self.item2img(item) )
        self.columns[-1].width = ResourceManager.instance().width() + 4 # arbitrary pad, image is centered

        self.columns.append( TableDualColumn(self,'name',"File Name") )
        self.columns[-1].setSecondaryTextTransform(lambda r,item : format_bytes(r['size']))
        """
        self.columns.append( TableColumnImage(self,'name',"Icon") )
        self.columns[-1].setShortName("")
        self.columns[-1].setTextTransform( lambda item,_ : self.item2img(item) )
        self.columns[-1].width = ResourceManager.instance().width() + 4 # arbitrary pad, image is centered

        self.columns.append( EditTextColumn(self,'name',"File Name") )
        self.columns[-1].setWidthByCharCount(40)
        self.columns[-1].commitText.connect(self._onCommitText)
        self.columns[-1].createFile.connect(self._onCreateFile)
        self.columns[-1].createDirectory.connect(self._onCreateDirectory)

        self.columns.append( TableColumn(self,'size',"Size") )
        self.columns[-1].setTextTransform( lambda item,_ : format_bytes(item['size']) )
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(9)

        self.columns.append( TableColumn(self,'mtime',"Modified Date") )
        self.columns[-1].setTextTransform( lambda item,_ : self.getFormatedDate(item) )
        self.columns[-1].setShortName("Date")
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(13)

        self.columns.append( TableColumn(self,'mode',"Permissions") )
        self.columns[-1].setTextTransform( lambda _,v : format_mode(v) )
        self.columns[-1].setShortName("Mode")
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setWidthByCharCount(13)

    def onShortcutCopy(self):

        self.parent().action_copy( self.getSelection() )

    def onShortcutCut(self):

        self.parent().action_cut( self.getSelection() )

    def onShortcutPaste(self):

        self.parent().controller.action_paste( self.parent() )

    def onShortcutRefresh(self):

        self.parent().refresh()

    def sortColumn(self,col_index):

        # TODO: this api needs to be refactored somehow
        reverse=self.view.sort(self.columns[col_index].index,True)
        self.setSortColumn(col_index,-1 if reverse else 1)

    def action_edit_column(self, row, col):
        opts = self.columns[col].get_default_opts(row)
        if opts:
            self.columns[col].editor_start(*opts)

    def mouseReleaseRight(self,event):
        self.parent().controller.contextMenu( event, self.parent(), self.getSelection() )

    def mouseReleaseOther(self,event=None):

        # TODO: maintain a history, goback should go to previous
        # directory, and not the parent directory.
        if event is not None:
            if event.button()==Qt.XButton1:
                self.open_parent_directory()
            else:
                print(event.button())

    def mouseDoubleClick(self,row,col,event=None):

        if event is None or event.button() == Qt.LeftButton:
            if 0<= row < len(self.view):
                item = self.view[row]
                if item['name'] == '..':
                    self.open_parent_directory()
                elif item['isDir']:
                    self.position_stack.append(row)
                    self.open_child_directory(item)
                else:
                    # TODO this needs an abstraction
                    self.parent().action_open_file( item )

    def open_parent_directory(self):
        self.parent().chdir( self.view.parent(self.view.pwd()) )
        if self.position_stack:
            idx = self.position_stack.pop()
            self.scrollTo( idx )
            self.setSelection([idx,])

    def open_child_directory(self,item):
        self.scrollTo( 0 )
        self.parent().chdir( item['name'] )
        self.setSelection([])

    def sortColumn(self,*args):
        pass

    def item2img(self,item):
        return self.parent().item2img( item )

    def getFormatedDate(self,item):
        value = self.parent().getSlowData(item,"mtime")
        return format_date(value)

    def _onCommitText(self,jobs):
        self.renamePaths.emit(jobs)

    def _onCreateFile(self,name):
        self.createFile.emit(name)

    def _onCreateDirectory(self,name):
        self.createDirectory.emit(name)

class EditTextColumn(EditColumn,QObject):
    # register a signal to update exif data when editing is done,.
    # this will enable searching on data that has been modified.
    commitText = pyqtSignal(object) # given a list of jobs
    createFile = pyqtSignal(str)
    createDirectory = pyqtSignal(str)

    def __init__(self,parent,index,name=None,data_type=str):
        EditColumn.__init__(self,parent,index,name,data_type)
        QObject.__init__(self,parent)
        #self.cell_modified.connect(self.editing_finished)

    def editor_start(self,rows,text,mode=0):
        self.edit_mode = mode
        super().editor_start(rows,text)

    def editor_save(self):
        """
            save the modified buffer to 'index; of each row in the data set
        """
        #print self.data_type,self.editor.buffer
        try:
            value = self.data_type(str(self.editor.buffer).strip())
        except:
            self.editor_close()
            return

        ## TODO: this is now broken by the Load Dir Job
        ##changed = set()
        ##for row in self.open_editors:
        ##    item = self.parent.data[row]
        ##    if item[self.index] != value:
        ##        changed.add(row)


        # only emits signals if a row changed, and only for rows
        # that did in fact change
        if self.edit_mode == 0:
            self.editing_rename_finished(self.open_editors,value)
        elif self.edit_mode==1:
            self.editing_create_file_finished(self.open_editors,value)
        elif self.edit_mode==2:
            self.editing_create_dir_finished(self.open_editors,value)

        self.parent.update()
        self.editor_close()

        # TODO: also broken for the same reason
        ##if len(changed) > 0:
        ##    self.cell_modified.emit(changed,value)
        return

    def editing_rename_finished(self,rows,new_value):
        # do the commit here,

        # todo: this should be done at a higher level
        jobs = []
        if len(rows) == 1:
            row = list(rows)[0]
            src_name = self.parent.data[row][self.index]
            jobs.append( (src_name,new_value) )
        else:
            # TODO: need to use the view for this....
            # renaming multiple files to the same name is bad mmkay
            base_name, ext = os.path.splitext(new_value)

            for idx,row in enumerate(rows):
                src_name = self.parent.data[row][self.index]
                tgt_name = "%s (%d)%s"%(base_name,idx+1,ext)
                jobs.append( (src_name,tgt_name) )

        # jobs contains a old_name.-> new_name map
        # that a view could act on to move files
        self.commitText.emit(jobs)

    def editing_create_file_finished(self,rows,new_value):
        self.createFile.emit(new_value)

    def editing_create_dir_finished(self,rows,new_value):
        self.createDirectory.emit(new_value)

class ExplorerModel(QWidget):
    """docstring for MainWindow"""

    directoryChanged = pyqtSignal(str)

    toggleSecondaryView = pyqtSignal()

    def __init__(self, view, controller, parent=None):
        super(ExplorerModel, self).__init__(parent)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.hbox = QHBoxLayout()
        self.hbox.setContentsMargins(0,0,0,0)

        self.view = view
        self.controller = controller

        self.tbl_file = self._getNewFileTable(view)

        self.txt_path = LineEdit_Path(self,self.tbl_file)
        self.txt_path.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Minimum)
        #self.txt_path.textEdited.connect(self.onTextChanged)

        self.btn_split = QToolButton(self)
        self.btn_split.setIcon(QIcon(":/img/app_split.png"))
        self.btn_split.setHidden(True)
        self.btn_split.clicked.connect( self.on_splitButton_clicked )

        self.btn_prev = QToolButton(self)
        self.btn_prev.setIcon(QIcon(":/img/app_prev.png"))
        self.btn_prev.clicked.connect( self.chdir_prev )
        self.btn_next = QToolButton(self)
        self.btn_next.setIcon(QIcon(":/img/app_next.png"))
        self.btn_next.clicked.connect( self.chdir_next )

        self.hbox.addWidget(self.btn_prev)
        self.hbox.addWidget(self.btn_next)
        self.hbox.addWidget(self.txt_path)
        self.hbox.addWidget(self.btn_split)
        self.vbox.addLayout( self.hbox )
        self.vbox.addWidget( self.tbl_file.container )

        self.directory_history = []
        self.directory_history_index = 0

        #self.tbl_file.setData(self.view)
        #self.txt_path.setText(self.view.pwd())

        self.slow_data_history = {}

    def _getNewFileTable(self,view):
        tbl =  ExplorerFileTable(view,self)
        tbl.showColumnHeader( False )
        tbl.showRowHeader( False )
        tbl.setLastColumnExpanding( True )

        tbl.renamePaths.connect(self.action_rename)
        tbl.createFile.connect(self.action_touch)
        tbl.createDirectory.connect(self.action_mkdir)
        return tbl

    def setView(self,view):
        self.view = view
        self.tbl_file.view = view
        self.tbl_file.setData(view)
        self.txt_path.setText(view.pwd())

        self.directory_history.append(view.pwd())

    def showSplitButton(self,bShow):
        self.btn_split.setHidden(not bShow)

    def refresh(self):
        self.chdir( self.view.pwd() )

    def clearHistory(self):
        self.directory_history = []
        self.directory_history_index = 0

    def chdir(self,path, clear_stack=False, push=True):

        self._chdir(path,clear_stack,push)

        self.btn_next.setHidden(self.directory_history_index == 0)
        self.btn_prev.setHidden(self.directory_history_index == len(self.directory_history)-1)

        self.txt_path.setText(self.view.pwd())
        self.tbl_file.update()
        self.tbl_file.scrollTo(0)

    def _chdir(self,path,clear_stack,push):
        pwd = self.view.pwd()
        try:

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

            if clear_stack:
                self.tbl_file.position_stack=[]

            self.directoryChanged.emit(self.view.pwd())

            self.slow_data_history = {}

        except OSError as e:
            sys.stderr.write(str(e))
            QMessageBox.critical(self,"Access Error","Error Opening `%s`"%path)
            s='->'.join([s[2] for s in traceback.extract_stack()])
            print("_chdir OS error:",path,name)
            print(s)
            # reopen the original current directory.
            #self.view.chdir( pwd )

    def chdir_prev(self):
        print(self.directory_history_index,self.directory_history)

        if self.directory_history_index < len(self.directory_history):
            self.directory_history_index += 1
            index = len(self.directory_history) - self.directory_history_index - 1
            if 0<=index<len(self.directory_history):
                path = self.directory_history[index]
                self.chdir(path,True,False)

    def chdir_next(self):
        print(self.directory_history_index,self.directory_history)

        if self.directory_history_index > 0:
            self.directory_history_index -= 1
            index = len(self.directory_history) - self.directory_history_index - 1
            if 0<=index<len(self.directory_history):
                path = self.directory_history[index]
                self.chdir(path,True,False)

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

    def action_open(self):
        explorerOpen( self.view.pwd() )

    def action_file(self, item):
        # double click file action
        path = self.view.realpath(item['name'])
        cmdstr = Settings.instance()['cmd_open_native']
        os.system(cmdstr%path)


    def action_open_file(self, path):
        pass

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

        job = RenameJob(self.view,jobs)
        job.finished.connect(self.onJobFinished)
        self.submitJob.emit(job)

    def action_touch_begin(self):
        self.action_create(1)

    def action_touch(self,name):
        # TODO handle OS errors
        self.view.open(name,"w").close()
        self.refresh()
        # TODO: when load completes set selection to name
        #if self.view.exists(name):
        #    idx = self.view.index(name)
        #    self.tbl_file.scrollTo(idx)
        #    self.tbl_file.setSelection([idx,])
        #else:
        #    print("error")

    def action_mkdir_begin(self):
      self.action_create(2)

    def action_mkdir(self,name):
        # TODO handle OS errors
        self.view.mkdir(name)
        self.refresh()
        if self.view.exists(name):
            idx = self.view.index(name)
            self.tbl_file.scrollTo(idx)
            self.tbl_file.setSelection([idx,])
        else:
            print("error")

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

        opts = (set([index,]),name)
        if opts:
            self.tbl_file.columns[col].editor_start(*opts,mode)

    def action_copy_path(self,item):

        path = self.view.realpath(item['name'])
        QApplication.instance().clipboard().setText(path)

    def action_cut(self, items):
        cut_items =  [ self.view.realpath(item['name']) for item in items ]
        self.controller.action_cut(self.view,cut_items)

    def action_copy(self, items):
        copy_items =  [ self.view.realpath(item['name']) for item in items ]
        self.controller.action_copy(self.view,copy_items)

    def action_paste(self):
        self.controller.action_paste(self.view,self.view.pwd())

    def action_refresh(self):
        self.chdir( self.view.pwd() )
        self.tbl_file.scrollTo(0)
        self.tbl_file.setSelection([])

    def action_update_replace(self, item):
        self.controller.action_update_replace( self.view.realpath(item['name']) )

    def on_splitButton_clicked(self):

        #self.btn_split.setHidden( !self.secondaryHidden() )
        #if self.controller.secondaryHidden():
        #    self.controller.action_open_view()
        #else:
        #    self.controller.action_close_view()
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
        self.controller.action_open_file( self.view.realpath(item['name']) )

    def onJobFinished(self):

        self.tbl_file.setSelection([])

        self.refresh()

    def onLoadComplete(self,data):
        self.view.data = data
        self.tbl_file.setData(self.view)
        # -1 for ".."
        self.infoNumFiles.emit(len(data)-1)

class LazySourceListView(SourceListView,QObject):
    """docstring for LazySourceListView"""
    loadDirectory = pyqtSignal(object)

    def load(self):

        self.data = []

        self.loadDirectory.emit(self)

class YueExplorerModel(ExplorerModel):

    do_ingest = pyqtSignal(list) # list of absolute paths

    def __init__(self, view, controller, parent=None):
        super(YueExplorerModel, self).__init__(view, controller, parent)

        self.list_library_files = set()

        self.brush_library = self.tbl_file.addRowHighlightComplexRule( self.indexInLibrary , QColor(128,128,224))

    def indexInLibrary(self,idx):
        return self.view[idx]['name'].lower() in self.list_library_files

    def action_ingest(self,items):
        paths = [ self.view.realpath(item['name']) for item in items ]
        self.do_ingest.emit( paths )

    def canIngest( self ):
        return self.controller.dialog is None

    def supportedExtension(self,ext):
        return ext in Song.supportedExtensions()

    def chdir(self,path, clear_stack=False, push = True):
        self._chdir(path,clear_stack,push)

        self.btn_next.setHidden(self.directory_history_index == 0)
        self.btn_prev.setHidden(self.directory_history_index == len(self.directory_history)-1)

        songs = Library.instance().searchDirectory(self.view.pwd(),False)
        self.list_library_files = set( self.view.split(song[Song.path])[1].lower() \
                                       for song in songs )

        self.txt_path.setText(self.view.pwd())
        self.tbl_file.update()
        self.tbl_file.scrollTo(0)

    def item2img(self,item):

        l = ResourceManager.LINK if item['isLink'] else 0
        if item['isDir']:
            return ResourceManager.instance().get(l|ResourceManager.DIRECTORY)

        _,ext = self.view.splitext(item['name'])
        return ResourceManager.instance().get(l|ResourceManager.instance().getExtType(ext))

class ExplorerDialog(QDialog):
    # display an explorer model inside a popup dialog
    def __init__(self, widget, parent=None):
        super(ExplorerDialog,self).__init__(parent);
        self.setWindowTitle("Explorer")
        self.vbox = QVBoxLayout(self)
        self.vbox.addWidget( widget )

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

        self.dialog = None
        self.cut_items = None
        self.cut_root = ""
        self.copy_items = None
        self.copy_root = ""
        self.act_diff_left_path = None

        #self.parent = parent

    def _ctxtMenu_addFileOperations1(self,ctxtmenu,model,items):

        is_files = all(not item['isDir'] for item in items)
        is_dirs  = all(item['isDir'] for item in items)

        # file manipulation options
        menu = ctxtmenu.addMenu("New")
        menu.addAction("Empty File",lambda : model.action_touch_begin())
        menu.addAction("Folder", lambda : model.action_mkdir_begin())

        menu = ctxtmenu.addMenu("Archive")
        if len(items) > 1:
            menu.addAction("Add to 7z")
            menu.addAction("Add to zip")
        elif not is_dirs:
            menu.addAction("Extract to *")

        ctxtmenu.addSeparator()

        act = ctxtmenu.addAction("Rename", lambda : model.action_rename_begin(items))
        #act.setDisabled( len(items)!=1 )

        if len(items) == 1 and items[0]['isLink']:
            if items[0]['name'] != "..":
                ctxtmenu.addAction("Edit Link")

        act=ctxtmenu.addAction("Copy", lambda : model.action_copy( items ))
        act.setShortcut(QKeySequence("Ctrl+C"))
        act=ctxtmenu.addAction("Cut", lambda : model.action_cut( items ))
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

        if model.view.islocal():
            ctxtmenu.addAction(QIcon(":/img/app_open.png"),"Open in Explorer",model.action_open)
            ctxtmenu.addAction("Open in Terminal",model.action_open_term)

    def contextMenu(self, event, model, items):

        ctxtmenu = QMenu(model)

        self._ctxtMenu_addFileOperations1(ctxtmenu,model,items)
        ctxtmenu.addSeparator()
        self._ctxtMenu_addFileOperations2(ctxtmenu,model,items)

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
    """

    def onDialogExit(self):
        if isinstance(self.dialog,IngestProgressDialog):
            self.parent.ingest_finished.emit()
        self.dialog = None
        # reload current directory
        self.parent.ex_main.refresh()
        self.parent.ex_secondary.refresh()

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

    def action_compare_set_left(self,model,item):
        self.act_diff_left_path = model.view.realpath(item['name'])

    def action_compare(self,model,item):
        self.act_diff_left_path = None

    def action_open_file(self, path):
        print(path)
        self.parent.play_file.emit( path )

    def action_delete(self,model,items):

        view = model.view
        paths = [ view.realpath(item['name']) for item in items ]
        job = DeleteJob(view,paths)
        job.finished.connect(model.onJobFinished)
        self.submitJob.emit(job)

    def action_cut(self,view,fpaths):
        """
        view : a wrapper around the source for paths in fpaths
        fpaths: list of absolute paths
        """
        self.cut_items = fpaths
        self.cut_root = view.pwd()
        self.cut_view = view

    def action_copy(self,view,fpaths):
        """
        todo, there is an internal and external expectation for copy
            Allow copy within Yue by storing meta data (source, list)
            for local source (Directory) also place on the clipboard
        QMimeData* mimeData = new QMimeData();
        mimeData->setData("text/uri-list", "file:///C:/fileToCopy.txt");
        clipboard->setMimeData(mimeData);
        """
        self.copy_items = fpaths
        self.copy_root = view.pwd()
        self.copy_view = view

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
            job = self.createMoveJob()
            job.finished.connect(model.onJobFinished)
            self.submitJob.emit(job)
            self.cut_items = None
            self.cut_root = ""

        elif self.copy_items is not None:
            job = CopyJob(self.copy_view,self.copy_items,view,dir_path)
            job.finished.connect(model.onJobFinished)
            self.submitJob.emit(job)

            self.copy_items = None
            self.copy_root = ""

    def createMoveJob(self,view):
        if self.cut_view is not view:
            job = CopyJob(self.cut_view,self.cut_items,view,dir_path)
        else:
            job = MoveJob(self.cut_view,self.cut_items,dir_path)
        return job

    def createCopyJob(self):
        job = CopyJob(self.copy_view,self.copy_items,view,dir_path)
        return job

class ExplorerView(Tab):
    """docstring for ExplorerView"""

    play_file = pyqtSignal(str)
    ingest_finished = pyqtSignal()

    primaryDirectoryChanged = pyqtSignal(str)
    secondaryDirectoryChanged = pyqtSignal(str)

    submitJob = pyqtSignal(Job)


    def __init__(self, parent=None):
        super(ExplorerView, self).__init__(parent)

        self.controller = ExplorerController( )

        self.source = DirectorySource()

        self.dashboard = Dashboard(self)

        self.ex_main = YueExplorerModel( None, self.controller, self )
        self.ex_secondary = YueExplorerModel( None, self.controller, self )
        self.ex_secondary.btn_split.setIcon(QIcon(":/img/app_join.png"))

        self.ex_main.toggleSecondaryView.connect(self.onToggleSecondaryView)
        self.ex_secondary.toggleSecondaryView.connect(self.onToggleSecondaryView)

        self.ex_main.directoryChanged.connect(self.primaryDirectoryChanged)
        self.ex_secondary.directoryChanged.connect(self.secondaryDirectoryChanged)

        self.ex_main.showSplitButton(True)
        self.ex_secondary.hide()

        self.hbox = QHBoxLayout()
        self.hbox.setContentsMargins(0,0,0,0)
        self.hbox.addWidget(self.ex_main)
        self.hbox.addWidget(self.ex_secondary)

        self.vbox = QVBoxLayout(self)

        self.vbox.addLayout(self.hbox)
        self.vbox.addWidget(self.dashboard)

    def onEnter(self):

        # delay creating the views until the tab is entered for the first
        # time, this slightly improves startup performance
        if (self.ex_main.view is None):
            view1 = LazySourceListView(self.source,self.source.root())
            view2 = LazySourceListView(self.source,self.source.root())

            view1.submitJob.connect(self.dashboard.startJob)
            view2.submitJob.connect(self.dashboard.startJob)

            # this is a hack, source views are currently in flux
            view1.chdir(view1.pwd())
            view2.chdir(view2.pwd())

            self.ex_main.setView(view1)
            self.ex_secondary.setView(view2)

    def chdir(self, path):

        # chdir can be called from another Tab, prior to onEnter,
        # if that happens run the onEnter first time setup.
        self.onEnter()

        self.ex_main.chdir(path,True)

        print("expview chdir",path)

    def refresh(self):
        print(self.ex_main.view.pwd())
        self.ex_main.refresh()
        if self.ex_secondary.isVisible():
            print(self.ex_secondary.view.pwd())
            self.ex_secondary.refresh()

    def openFtp(self):

        url = "ftp://nsetzer:password@192.168.0.9:2121//Music"
        p = parseFTPurl(url)
        try:
            src=FTPSource(p['hostname'],p['port'],p['username'],p['password'])
        except ConnectionRefusedError as e:
            sys.stderr.write("error: %s\n"%e)
        else:
            print("...")
            view=SourceListView(src,p['path'])
            mdl = YueExplorerModel( view , DummyController(), self )

            self.ftpdialog = ExplorerDialog( mdl, self )
            self.ftpdialog.show()

    def onToggleSecondaryView(self):
        if self.ex_secondary.isHidden():
            self.ex_secondary.show()
            self.ex_main.showSplitButton(False)
            self.ex_secondary.showSplitButton(True)
        else:
            self.ex_secondary.hide()
            self.ex_main.showSplitButton(True)
            self.ex_secondary.showSplitButton(False)

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = ExplorerView()
    window.show()
    window.resize(640,480)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()