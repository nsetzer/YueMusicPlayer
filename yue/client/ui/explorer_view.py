#! python34 $this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

import yue
from yue.client.widgets.LargeTable import LargeTable, TableDualColumn, TableColumnImage
from yue.client.widgets.LineEdit import LineEdit

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library

from yue.client.ui.ingest_dialog import IngestProgressDialog
from yue.client.ui.movefile_dialog import MoveFileProgressDialog
from yue.client.ui.rename_dialog import RenameDialog
from yue.client.explorer.source import DirectorySource,SourceListView

"""
TODO:
    ability for smart file renaming / moving

    changing the name of a directory, or renaming a file
    requires updating the database if the file is in the data base

    on linux this is easy since paths are case sensitive, and slashes
    always go one direciton

    on windows paths are not case sensitive and slashes can go either
    direction

    in sql, i can run a wildcard search by executing, for example:
        SELECT * FROM table WHERE 'D:_Music%'

        % : 0 or more characters
        _ : 1 character
        [\\/] : match a set of characters

    I need to introduce a Library search function which queries files
    that have paths which match a string. The semantics are different
    per platform.

    there is an additional filter, files exactly in a directory,
    or paths that start with a directory prefix. this could mean a total
    of one or two functions, depending on implementation

"""

byte_labels = ['B','KB','MB','GB']
def format_bytes(b):
    for label in byte_labels:
        if b < 1024:
            return "%d%s"%(b,label)
        b /= 2014
    return "%d%s"%(b,byte_labels[-1])

def explorerOpen( url ):

    if os.name == "nt":
        os.startfile(url);
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
        self.parent().chdir( self.text(), True )

class ResourceManager(object):
    """docstring for ResourceManager"""
    _instance = None

    DIRECTORY = 1
    FILE = 2
    SONG = 3

    def __init__(self):
        super(ResourceManager, self).__init__()
        self.resources = {}
        self.resources[ResourceManager.FILE]      = QPixmap(':/img/app_file.png')
        self.resources[ResourceManager.SONG]      = QPixmap(':/img/app_song.png')
        self.resources[ResourceManager.DIRECTORY] = QPixmap(':/img/app_folder.png')

    def get(self,kind):
        return self.resources[kind]

    def width(self):
        return self.resources[ResourceManager.FILE].width()

class FileTable(LargeTable):
    """
    """

    def __init__(self, view, parent=None):
        self.rm = ResourceManager()

        super(FileTable,self).__init__(parent)

        self.setLastColumnExpanding( True )
        self.showColumnHeader( False )
        self.showRowHeader( False )

        self.view = view

        self.position_stack = []

    def initColumns(self):

        self.columns.append( TableColumnImage(self,'isDir') )
        self.columns[-1].setTextTransform( self.item2img )
        self.columns[-1].width = self.rm.width() + 4 # arbitrary pad, image is centered

        self.columns.append( TableDualColumn(self,'name',"File Name") )
        self.columns[-1].setSecondaryTextTransform(lambda r,item : format_bytes(r['size']))

    def mouseReleaseRight(self,event):

        items = self.getSelection()

        is_files = all(not item['isDir'] for item in items)


        contextMenu = QMenu(self)

        # file manipulation options

        act = contextMenu.addAction("Rename", lambda : self.parent().action_rename( items[0] ))
        act.setDisabled( len(items)!=1 )

        act = contextMenu.addAction("New Folder", lambda : self.parent().action_newfolder())
        act.setDisabled( len(items)!=1 )


        contextMenu.addAction("Cut", lambda : self.parent().action_cut( items ))
        act = contextMenu.addAction("Paste", lambda : self.parent().action_paste( ))
        act.setDisabled( not self.parent().canPaste() )

        contextMenu.addSeparator()

        # library options

        if len(items) == 1 and not is_files:
            act = contextMenu.addAction(QIcon(":/img/app_import.png"),"Import Directory", lambda : self.parent().action_ingest( items ))
            act.setDisabled( not self.parent().canIngest() )
        else:
            act = contextMenu.addAction(QIcon(":/img/app_import.png"),"Import", lambda : self.parent().action_ingest( items ))
            act.setDisabled( not is_files or not self.parent().canIngest())


        if len(items) == 1:
            act = contextMenu.addAction("Play Song", lambda : self.parent().action_play( items[0] ))
            ext = os.path.splitext(items[0]['name'])[1].lower()
            if not self.parent().supportedExtension( ext ):
                act.setDisabled( True )

        contextMenu.addSeparator()
        contextMenu.addAction(QIcon(":/img/app_open.png"),"Open in Explorer",self.parent().action_open)

        action = contextMenu.exec_( event.globalPos() )

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

    def item2img(self,item,isDir):
        if isDir:
            return self.rm.get(ResourceManager.DIRECTORY)
        ext = os.path.splitext(item['name'])[1].lower()
        if self.parent().supportedExtension( ext ):
            return self.rm.get(ResourceManager.SONG)
        return self.rm.get(ResourceManager.FILE)

class ExplorerView(QWidget):
    """docstring for MainWindow"""

    play_file = pyqtSignal(str)
    execute_search = pyqtSignal(str,bool)

    def __init__(self, parent=None):

        super(ExplorerView, self).__init__(parent)
        self.vbox = QVBoxLayout(self)

        self.source = DirectorySource()
        self.view = SourceListView(self.source,self.source.root())

        self.tbl_file = FileTable( self.view, self )
        self.tbl_file.addRowHighlightComplexRule( self.indexInLibrary , QColor(128,128,224))

        self.txt_path = LineEdit_Path(self,self.tbl_file)
        #self.txt_path.textEdited.connect(self.onTextChanged)

        self.vbox.addWidget( self.txt_path )
        self.vbox.addWidget( self.tbl_file.container )

        self.tbl_file.setData(self.view)
        self.txt_path.setText(self.view.pwd())

        self.dialog = None
        self.cut_items = None
        self.cut_root = ""

        self.list_library_files = set()

    def indexInLibrary(self,idx):
        return self.view[idx]['name'] in self.list_library_files

    def chdir(self,path, clear_stack=False):
        pwd = self.view.pwd()

        try:
            if clear_stack:
                self.tbl_file.position_stack=[]
            self.view.chdir(path)

        except OSError as e:
            sys.stderr.write(str(e))
            QMessageBox.critical(self,"Access Error","Error Opening `%s`"%path)
            # reopen the original current directory.
            self.view.chdir( pwd )

        songs = Library.instance().searchDirectory(self.view.pwd(),False)
        self.list_library_files = set( os.path.split(song[Song.path])[1] \
                                       for song in songs )

        self.txt_path.setText(self.view.pwd())
        self.tbl_file.update()

    def supportedExtension(self,ext):
        return ext in Song.supportedExtensions()

    def action_open(self):

        explorerOpen( self.view.pwd() )

    def action_rename(self, item):
        name=item['name']
        diag = RenameDialog(name,parent=self)
        if diag.exec_():
            new_name=diag.text()
            if new_name == name:
                return
            src = self.view.join( self.view.pwd(), name)
            tgt = self.view.join( self.view.pwd(), new_name)
            self.dialog = MoveFileProgressDialog(self.view, tgt, src, self)
            self.dialog.setOnCloseCallback(self.onDialogExit)
            self.dialog.start()
            self.dialog.show()
        return

    def action_newfolder(self):

        diag = RenameDialog("New Folder","Create Folder",parent=self)
        if diag.exec_():
            print(diag.text())

    def action_ingest(self, items):

        paths = [ self.view.realpath(item['name']) for item in items ]
        self.dialog = IngestProgressDialog(paths, self)
        self.dialog.setOnCloseCallback(self.onDialogExit)
        self.dialog.start()
        self.dialog.show()

    def action_play(self, item):
        self.play_file.emit( self.view.realpath(item['name']) )

    def onDialogExit(self):
        if isinstance(self.dialog,IngestProgressDialog):
            self.execute_search.emit("added = today",False)
        self.dialog = None
        # reload current directory
        self.chdir( self.view.pwd() )

    def canIngest( self ):
        return self.dialog is None

    def action_cut(self, items):
        self.cut_items = [ self.view.realpath(item['name']) for item in items ]
        self.cut_root = self.view.pwd()

    def action_paste(self):
        # TODO: create a progress dialog to initiate the move

        if self.canPaste():
            self.dialog = MoveFileProgressDialog(self.view, self.view.pwd(), self.cut_items, self)
            self.dialog.setOnCloseCallback(self.onDialogExit)
            self.dialog.start()
            self.dialog.show()

    def canPaste( self ):
        return self.cut_items is not None and self.cut_root != self.view.pwd()