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
from yue.client.widgets.LineEdit import LineEdit
from yue.client.widgets.FlatPushButton import FlatPushButton
from yue.client.widgets.Tab import Tab

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

    def __init__(self, view, parent=None):
        super(ExplorerFileTable,self).__init__(parent)
        self.view = view

        self.position_stack = []

    def initColumns(self):

        self.columns.append( TableColumnImage(self,'isDir',"Icon") )
        self.columns[-1].setShortName("")
        self.columns[-1].setTextTransform( lambda item,_ : self.item2img(item) )
        self.columns[-1].width = ResourceManager.instance().width() + 4 # arbitrary pad, image is centered

        self.columns.append( TableDualColumn(self,'name',"File Name") )
        self.columns[-1].setSecondaryTextTransform(lambda r,item : format_bytes(r['size']))

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
        return tbl

    def setView(self,view):
        self.view = view
        self.tbl_file.view = view
        self.tbl_file.setData(view)
        self.txt_path.setText(view.pwd())

        self.directory_history.append(view.pwd())

    def showSplitButton(self):
        self.btn_split.setHidden(False)

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

    def action_open_file(self, path):
        pass

    def action_rename(self, item):
        name=item['name']
        diag = RenameDialog(name,parent=self)
        if diag.exec_():
            new_name=diag.text()
            if new_name == name:
                return
            src = self.view.join( self.view.pwd(), name)
            tgt = self.view.join( self.view.pwd(), new_name)
            self.do_move.emit(self, tgt, src)
        return

    def action_newfolder(self):

        diag = RenameDialog("New Folder","Create Folder",parent=self)
        if diag.exec_():
            path = self.view.join(self.view.pwd(),diag.text())
            self.view.mkdir( path )
            self.chdir(self.view.pwd())

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

class YueExplorerModel(ExplorerModel):

    do_ingest = pyqtSignal(list) # list of absolute paths
    do_move   = pyqtSignal(object,object,object)

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

    def action_paste(self):
        # TODO why is this reimplemented
        if self.canPaste():
            tgt = self.view.pwd()
            src = self.controller.cut_items
            self.do_move.emit(self, tgt, src)

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

    forceReload = pyqtSignal()

    def __init__(self, parent):
        super(ExplorerController, self).__init__()

        self.dialog = None
        self.cut_items = None
        self.cut_root = ""
        self.copy_items = None
        self.copy_root = ""
        self.parent = parent

    def contextMenu(self, event, model, items):

        is_files = all(not item['isDir'] for item in items)

        contextMenu = QMenu(model)

        # file manipulation options

        act = contextMenu.addAction("Rename", lambda : model.action_rename( items[0] ))
        act.setDisabled( len(items)!=1 )

        act = contextMenu.addAction("New Folder", lambda : model.action_newfolder())
        act.setDisabled( len(items)!=1 )


        contextMenu.addAction("Cut", lambda : model.action_cut( items ))
        act = contextMenu.addAction("Paste", lambda : model.action_paste( ))
        act.setDisabled( not model.canPaste() )

        contextMenu.addSeparator()
        act = contextMenu.addAction("Refresh",model.action_refresh)
        contextMenu.addSeparator()

        # library options

        if len(items) == 1 and not is_files:
            act = contextMenu.addAction(QIcon(":/img/app_import.png"),"Import Directory", lambda : model.action_ingest( items ))
            act.setDisabled( not model.canIngest() )
        else:
            act = contextMenu.addAction(QIcon(":/img/app_import.png"),"Import", lambda : model.action_ingest( items ))
            act.setDisabled( not is_files or not model.canIngest())

        if len(items) == 1:
            act = contextMenu.addAction("Play Song", lambda: model.action_open_file( items[0] ))
            ext = os.path.splitext(items[0]['name'])[1].lower()
            if not model.supportedExtension( ext ):
                act.setDisabled( True )

        contextMenu.addSeparator()
        contextMenu.addAction(QIcon(":/img/app_open.png"),"Open in Explorer",model.action_open)

        #if self.secondaryHidden():
        #    act = contextMenu.addAction("Open Secondary View", self.action_open_view)
        #else:
        #    act = contextMenu.addAction("Close Secondary View", self.action_close_view)

        if len(items) == 1 and is_files:
            contextMenu.addSeparator()
            act = contextMenu.addAction("update/replace *", lambda: model.action_update_replace(items[0]))

        action = contextMenu.exec_( event.globalPos() )

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

    #def action_open_view(self):
    #    self.parent.ex_secondary.show()
    #    # self.parent().ex_secondary.chdir( self.view.pwd() )

    #def action_close_view(self):
    #    self.parent.ex_secondary.hide()

    def action_open_file(self, path):
        print(path)
        self.parent.play_file.emit( path )

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

    def action_paste(self,view,dir_path):
        """
        view: a wrapper around the source for paths
        dir_path: absolute path existing in view

        paste can copy across difference sources
        a cut or copy -> paste on the same DIRECTORY is a noop
        a cut -> paste on the same source is a move
        a cut -> paste across different sources is a copy
        a copy -> paste is always a copy, even on the same source
        """
        print("paste into",dir_path)

    #def secondaryHidden(self):
    #    return self.parent.ex_secondary.isHidden()

class ExplorerView(Tab):
    """docstring for ExplorerView"""

    play_file = pyqtSignal(str)
    ingest_finished = pyqtSignal()

    primaryDirectoryChanged = pyqtSignal(str)
    secondaryDirectoryChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super(ExplorerView, self).__init__(parent)

        self.controller = ExplorerController( self )

        self.source = DirectorySource()

        self.ex_main = YueExplorerModel( None, self.controller, self )
        self.ex_secondary = YueExplorerModel( None, self.controller, self )

        self.ex_main.toggleSecondaryView.connect(self.onToggleSecondaryView)

        self.ex_main.directoryChanged.connect(self.primaryDirectoryChanged)
        self.ex_secondary.directoryChanged.connect(self.secondaryDirectoryChanged)

        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(0,0,0,0)
        self.hbox.addWidget(self.ex_main)
        self.hbox.addWidget(self.ex_secondary)

        self.ex_main.showSplitButton()
        self.ex_secondary.hide()

        self.ex_main.do_ingest.connect(self.controller.showIngestDialog)
        self.ex_secondary.do_ingest.connect(self.controller.showIngestDialog)

        self.ex_main.do_move.connect(self.controller.showMoveFileDialog)
        self.ex_secondary.do_move.connect(self.controller.showMoveFileDialog)

        self.xcut_exec = QShortcut(QKeySequence("F5"), self)
        self.xcut_exec.activated.connect(self.refresh)

    def onEnter(self):

        # delay creating the views until the tab is entered for the first
        # time, this slightly improves startup performance
        if (self.ex_main.view is None):
            view1 = SourceListView(self.source,self.source.root())
            view2 = SourceListView(self.source,self.source.root())

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
        else:
            self.ex_secondary.hide()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = ExplorerView()
    window.show()
    window.resize(640,480)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()