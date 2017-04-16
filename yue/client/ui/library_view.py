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
from yue.qtcommon.TableEditColumn import EditColumn
from yue.qtcommon.SongTable import SongTable
from yue.qtcommon.LibraryTree import LibraryTree
from yue.qtcommon.LineEdit import LineEdit
from yue.qtcommon.FlatPushButton import FlatPushButton
from yue.qtcommon.Tab import Tab

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.settings import Settings
from yue.core.playlist import PlaylistManager

class LineEdit_Search(LineEdit):

    def __init__(self,parent,table, placeholder="Search Library"):
        super(LineEdit_Search,self).__init__(parent)
        self.table = table

        self.setPlaceholderText(placeholder)

    def keyReleaseEvent(self,event=None):
        super(LineEdit_Search,self).keyReleaseEvent(event)
        if event is not None and event.key() == Qt.Key_Down:
            self.table.clearSelection( )
            self.table.setSelection( [0,] )
            self.table.update(0)
            self.table.setFocus()

class LibraryTable(SongTable):


    def __init__(self,parent):
        super(LibraryTable,self).__init__(parent)

        self.current_uid = -1
        self.addRowTextColorComplexRule(self.currentSongRule,self.color_text_played_recent)

        self.selection_changed.connect(self.on_selection_change)
        self.editRowChange.connect(self.onEditRowChange)

    def currentSongRule(self,row):
        return self.data[row][Song.uid] == self.current_uid

    def onEditRowChange(self,row):
        # update the display path when the editor row changes
        self.parent().notify.emit(self.data[row][Song.path])

    def on_selection_change(self,event=None):

        items = self.getSelection()
        if len(items) == 1:
            song = items[0]
            self.parent().notify.emit( song[Song.path] )

    def mouseReleaseRight(self,event):

        mx = event.x()
        my = event.y()
        cx,cy = self._mousePosToCellPos(mx,my)
        row,cur_c = self.positionToRowCol(mx,my)

        items = self.getSelection()

        closeEditor=False

        for col in self.columns:
            if isinstance(col,EditColumn) and col.editor_isOpen():
                closeEditor = True;
                break;

        menu = QMenu(self)

        if closeEditor:

            act = menu.addAction("Save Changes",lambda:self.action_close_editors(EditColumn.editor_save))
            act = menu.addAction("Discard Changes",lambda:self.action_close_editors(EditColumn.editor_close))

        else:

            act = menu.addAction("Play",lambda:self.action_play_next(items,True))
            act.setDisabled( len(items) != 1 )

            menu.addAction("Play next",lambda:self.action_play_next(items))
            act.setDisabled( len(items) == 0 )

            act = menu.addAction("Show in Tree View",lambda:self.action_show_in_tree_view(items[0]))
            act.setDisabled( len(items) != 1 )

            if isinstance(self.columns[cur_c],EditColumn): # if it is an editable column give the option
                menu.addAction("Edit Song \"%s\""%self.columns[cur_c].name, \
                    lambda:self.action_edit_column(row,cur_c))

            menu.addSeparator()
            menu.addAction(QIcon(":/img/app_trash.png"),"Delete from Library",lambda:self.action_delete(items))

            if any(not song[Song.blocked] for song in items):
                menu.addAction(QIcon(":/img/app_x.png"),"Bannish", lambda:self.action_bannish(items,True))
            else:
                menu.addAction("Restore", lambda:self.action_bannish(items,False))

            if len(items) == 1 and self.parent().menu_callback is not None:
                menu.addSeparator()
                self.parent().menu_callback(menu,items[0])

        action = menu.exec_( event.globalPos() )

    def mouseDoubleClick(self,row,col,event):

        cx,cy = (0,0)
        if event:
            cx,cy = self._mousePosToCellPos(event.x(),event.y())
        if 0<=col<len(self.columns) and self.columns[col].index == Song.rating:
            self.columns[col].mouseDoubleClick(row,cx,cy)
        else:
            items = self.getSelection()
            self.action_play_next(items)

    def action_delete(self, songs):
        # emit a signal, with a set of songs to delete
        # these songs must be addded to a set so that undo delete
        # can be implemented.
        # display a warning message before emiting any signal
        sys.stderr.write("delete not implemented\n");

    def action_bannish(self, songs, state):
        """ bannish or restore a set of songs """
        lib = Library.instance()
        for song in songs:
            lib.update(song[Song.uid],**{Song.blocked:state})
            song[Song.blocked] = state # for ui, prevent rerunning search
        self.update()

    def action_play_next(self, songs, play=False):
        uids = [ song[Song.uid] for song in songs ]
        self.parent().insert_playlist.emit(uids,play)

    def action_edit_column(self, row, col):
        opts = self.columns[col].get_default_opts(row)
        if opts:
            self.columns[col].editor_start(*opts)

    def action_show_in_tree_view(self, song):
        self.parent().tree_lib.showArtist(song[Song.artist])

    def action_close_editors(self,func):
        for col in self.columns:
            if isinstance(col,EditColumn) and col.editor_isOpen():
                func(col)


class LibTree(LibraryTree):

    def __init__(self,parent):
        super(LibTree,self).__init__(parent)

        self.selection_changed.connect(self.on_selection_change)

    def mouseReleaseRight(self,event):

        mx = event.x()
        my = event.y()
        cx,cy = self._mousePosToCellPos(mx,my)
        row,cur_c = self.positionToRowCol(mx,my)

        menu = QMenu(self)

        act = menu.addAction("Create Playlist",self.action_create_playlist)
        act = menu.addAction("Clear Checked", self.clear_checked)

        menu.addSeparator()

        act = menu.addAction("Expand All",self.expand_all)
        act = menu.addAction("Collapse All",self.collapse_all)

        menu.addSeparator()

        act = menu.addAction("Refresh",self.refreshData)

        action = menu.exec_( event.globalPos() )

    def action_create_playlist(self):
        rule = self.formatCheckedAsQueryRule()
        songs = Library.instance().search(rule)
        uids = [ song[Song.uid] for song in songs ]
        self.parent().set_playlist.emit( uids )

    def on_selection_change(self,event=None):
        q = self.formatSelectionAsQueryString()
        self.parent().run_search(q,True)

class LibraryView(Tab):
    """docstring for MainWindow"""

    # emit this signal to create a new playlist from a given query string
    create_playlist = pyqtSignal(str)

    insert_playlist = pyqtSignal(list,bool)
    set_playlist = pyqtSignal(list)

    notify = pyqtSignal(str)

    def __init__(self, parent=None):
        super(LibraryView, self).__init__(parent)

        self.vbox_main = QVBoxLayout(self)
        self.vbox_main.setContentsMargins(0,0,0,0)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.tree_lib = LibTree( self )
        self.tree_lib.showColumnHeader( False )
        self.tree_lib.showRowHeader( False )

        self.cwidget = QWidget()
        self.splitter.addWidget( self.tree_lib.container )
        self.splitter.addWidget( self.cwidget )
        self.vbox_main.addWidget(self.splitter)
        self.vbox = QVBoxLayout(self.cwidget)
        self.vbox.setContentsMargins(0,5,0,0)

        self.hbox = QHBoxLayout()
        self.hbox.setContentsMargins(0,0,0,0)

        self.tbl_song = LibraryTable( self )
        self.tbl_song.showColumnHeader( True )
        self.tbl_song.showRowHeader( False )

        # needed for song sort
        self.tbl_song.update_data.connect(self.onUpdate)

        self.btn_quick = QToolButton(self)
        self.btn_quick.setIcon(QIcon(":/img/app_newlist.png"))
        self.btn_quick.clicked.connect(self.showQuickMenu)
        #self.btn_quick.setFlat(True)

        self.txt_search = LineEdit_Search(self,self.tbl_song)
        self.txt_search.textEdited.connect(self.onTextChanged)
        self.lbl_search = QLabel("/")
        self.lbl_error  = QLabel("")

        self.btn_newlist = QToolButton(self)
        self.btn_newlist.setIcon(QIcon(":/img/app_newlist.png"))
        self.btn_newlist.clicked.connect(lambda:self.create_playlist.emit(self.txt_search.text()))
        #self.btn_newlist.setFlat(True)

        self.hbox.addWidget( self.btn_quick )
        self.hbox.addWidget( self.txt_search )
        self.hbox.addWidget( self.lbl_search )
        self.hbox.addWidget( self.btn_newlist )

        self.vbox.addLayout( self.hbox )
        self.vbox.addWidget( self.lbl_error )
        self.vbox.addWidget( self.tbl_song.container )

        self.lbl_error.hide()

        self.menu_callback = None

    def setColumnState(self, order):
        if len(order) > 0:
            self.tbl_song.columns_setOrder( order )

    def getColumnState(self):
        """ returns a list-of-strings representing the current visible columns """
        return self.tbl_song.columns_getOrder( )

    def onUpdate(self):
        text = self.txt_search.text()
        self.run_search(text)

    def onTextChanged(self,text,update=0):
        self.run_search(text)

    def refresh(self):
        self.run_search( self.txt_search.text() , refresh=True)

    def run_search(self, text, setText=False, refresh = False):
        """
        setText: if true set the text box to contain text
        """

        if self.tbl_song.isEditorOpen():
            return # TODO, should do something

        try:
            songs = Library.instance().search( text, \
                orderby=self.tbl_song.sort_orderby,
                reverse = self.tbl_song.sort_reverse )

        except ParseError as e:
            self.txt_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()
        except Exception as e:
            raise e

        else:
            self.displaySongs(songs)

            if setText:
                self.txt_search.setText( text )

            if not refresh:
                self.tbl_song.scrollTo( 0 )
                self.tbl_song.setSelection([])

    def displaySongs(self,songs):

        self.tbl_song.setData(songs)
        self.lbl_search.setText("%d/%d"%(len(songs), len(Library.instance())))

        if not self.lbl_error.isHidden():
            self.txt_search.setStyleSheet("")
            self.lbl_error.hide()

    def setCurrentSongId( self, uid ):
        self.tbl_song.current_uid = uid
        self.tbl_song.update()

    def setMenuCallback(self,cbk):
        """
        callback as a function which accepts a menu and a song
        and returns nothing. the function should add actions to
        the given song
        """
        self.menu_callback = cbk

    def showQuickMenu(self, event):
        pos = self.btn_quick.mapToGlobal(self.btn_quick.pos())

        menu = QMenu(self)

        d=Settings.instance().getMulti("playlist_preset_names",
                                       "playlist_presets")
        dp=list(zip(d["playlist_preset_names"],d["playlist_presets"]))

        for name,query in sorted(dp):
            menu.addAction(name).setData(query)

        action = menu.exec_( pos )

        if action is not None:
            self.run_search(action.data(),setText=True)