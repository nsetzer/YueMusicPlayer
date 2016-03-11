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
from yue.client.widgets.SongTable import SongTable
from yue.client.widgets.LineEdit import LineEdit
from yue.client.widgets.TableEditColumn import EditColumn

from yue.client.ui.rename_dialog import RenameDialog
from yue.client.ui.openpl_dialog import OpenPlaylistDialog
from yue.client.ui.plexport_dialog import ExportM3uDialog
from yue.client.ui.plimport_dialog import ImportM3uDialog
from yue.client.ui.sync_dialog import SyncProfileDialog, SyncDialog

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from .library_view import LineEdit_Search

class EditTable(SongTable):
    # todo I may want to further specialize, since this is cloned from
    # the library view
    def __init__(self, parent = None):
        super(EditTable, self).__init__(parent)
        self.selection_changed.connect(self.on_selection_change)

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

        menu = QMenu(self)

        items = self.getSelection()

        act = menu.addAction("Play",lambda:self.action_play_next(items,True))
        act.setDisabled( len(items) != 1 )

        menu.addAction("Play next",lambda:self.action_play_next(items))
        act.setDisabled( len(items) == 0 )

        if isinstance(self.columns[cur_c],EditColumn):

            menu.addSeparator()
            menu.addAction("Edit Song \"%s\""%self.columns[cur_c].name, \
                lambda:self.action_edit_column(row,cur_c))

        action = menu.exec_( event.globalPos() )

    def action_play_next(self, songs, play=False):
        uids = [ song[Song.uid] for song in songs ]
        self.parent().set_playlist.emit(uids,play)

    def action_edit_column(self, row, col):
        opts = self.columns[col].get_default_opts(row)
        if opts:
            self.columns[col].editor_start(*opts)

class PlayListEditTable(EditTable):
    """docstring for SongTable"""
    def __init__(self, parent = None):
        super(PlayListEditTable, self).__init__(parent)

        self.showColumnHeader( True )
        self.showRowHeader( False )

        self.sibling = None

    def setSibling(self, sib):
        self.sibling = sib

    def processDropEvent(self,source,row,data):

        # allow drops from the current playlist because why not
        if source is not None:
            for song in data:
                if isinstance(song,dict):
                    self.parent().playlist_data.add( song[Song.uid] )
                    self.parent().dirty = True
            self.parent().refresh()

    def mouseDoubleClick(self,row,col,event):

        for song in self.getSelection():
            self.parent().playlist_data.remove( song[Song.uid] )
            self.parent().dirty = True
        self.parent().refresh()

class LibraryEditTable(EditTable):
    """docstring for SongTable"""
    def __init__(self, parent = None):
        super(LibraryEditTable, self).__init__(parent)
        self.showColumnHeader( True )
        self.showRowHeader( False )

        self.sibling = None

    def setSibling(self, sib):
        self.sibling = sib

    def processDropEvent(self,source,row,data):

        if source is self.sibling:
            for song in data:
                if isinstance(song,dict):
                    self.parent().playlist_data.remove( song[Song.uid] )
                    self.parent().dirty = True
            self.parent().refresh()

    def mouseDoubleClick(self,row,col,event):

        for song in self.getSelection():
            self.parent().playlist_data.add( song[Song.uid] )
            self.parent().dirty = True
        self.parent().refresh()

class PlaylistEditView(QWidget):
    """docstring for MainWindow"""

    on_rename = pyqtSignal(QWidget,str)
    set_playlist = pyqtSignal(list,bool)
    notify = pyqtSignal(str)
    set_playlist = pyqtSignal(list)

    def __init__(self, playlist_name):
        super(PlaylistEditView, self).__init__()

        self.dirty = False

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.hbox1 = QHBoxLayout()
        self.hbox1.setContentsMargins(0,0,0,0)
        self.hbox2 = QHBoxLayout()
        self.hbox2.setContentsMargins(0,0,0,0)

        self.hbox3 = QHBoxLayout()
        self.lbll=QLabel("Library")
        self.lbll.setAlignment(Qt.AlignHCenter)
        self.lblp=QLabel("Playlist")
        self.lblp.setAlignment(Qt.AlignHCenter)
        self.hbox3.addWidget(self.lbll)
        self.hbox3.addWidget(self.lblp)
        self.hbox3.setContentsMargins(0,0,0,0)

        self.toolbar = QToolBar(self)
        self.toolbar.addAction(QIcon(':/img/app_save.png'),"save", self.save)
        self.toolbar.addAction(QIcon(':/img/app_open.png'),"load", self.load)
        self.toolbar.addAction(QIcon(':/img/app_export.png'),"Export", self.export_playlist)
        self.toolbar.addAction(QIcon(':/img/app_import.png'),"Import", self.import_playlist)
        self.toolbar.addAction(QIcon(':/img/app_newlist.png'),"Play",self.create_playlist)
        self.toolbar.addAction(QIcon(':/img/app_sync.png'),"sync", self.sync)

        self.tbl_lib = LibraryEditTable( self )
        self.tbl_pl = PlayListEditTable( self )

        self.tbl_lib.setSibling(self.tbl_pl)
        self.tbl_pl.setSibling(self.tbl_lib)

        #self.tbl_pl.update_data.connect(self.onUpdate)

        self.txt_search = LineEdit_Search(self,self.tbl_pl,placeholder="Search Playlist")
        self.txt_search.textEdited.connect(self.onTextChanged)
        self.lbl_search = QLabel("/")
        self.lbl_error  = QLabel("")

        self.hbox1.addWidget( self.txt_search )
        self.hbox1.addWidget( self.lbl_search )

        self.hbox2.addWidget( self.tbl_lib.container )
        self.hbox2.addWidget( self.tbl_pl.container )

        self.vbox.addWidget( self.toolbar )
        self.vbox.addLayout( self.hbox1 )
        self.vbox.addWidget( self.lbl_error )
        self.vbox.addLayout( self.hbox3 )
        self.vbox.addLayout( self.hbox2 )

        self.lbl_error.hide()

        self.playlist_name = playlist_name
        self.playlist = PlaylistManager.instance().openPlaylist(self.playlist_name)
        self.playlist_data = set(self.playlist.iter())
        self.refresh()

    def isDirty(self):
        return self.dirty

    #def onUpdate(self):
    #    text = self.txt_search.text()
    #    print(text)
    #    #self.run_search(text)

    def onTextChanged(self,text,update=0):
        self.run_search(text)

    def refresh(self):
        # todo: ability to scroll to the index of a recently dropped song

        self.run_search(self.txt_search.text())

    def run_search(self, text, setText=False):
        """
        setText: if true set the text box to contain text
        """
        try:
            # search the entire library for songs that match the query
            lib = Library.instance()
            songs = lib.search( text, \
                orderby=self.tbl_pl.sort_orderby,
                reverse=self.tbl_pl.sort_reverse )

            # filter results into two sets, in the playlist and not
            ldata = []
            rdata = []
            for song in songs:
                if song[Song.uid] in self.playlist_data:
                    rdata.append( song )
                else:
                    ldata.append( song )

            self.tbl_lib.setData(ldata)
            self.tbl_pl.setData(rdata)
            self.lbl_search.setText("%d/%d"%(len(rdata), len(lib)))

            if not self.lbl_error.isHidden():
                self.txt_search.setStyleSheet("")
                self.lbl_error.hide()

            if setText:
                self.txt_search.setText( text )

                self.tbl_lib.scrollTo( 0 )
                self.tbl_pl.scrollTo( 0 )
        except ParseError as e:
            self.txt_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()
        except Exception as e:
            raise e

    def save_warning(self):
        title="Save"
        text="Save Changes?"
        window = QMessageBox(QMessageBox.Question,title,text)
        window.addButton(QMessageBox.Save)
        window.addButton(QMessageBox.Discard)
        window.addButton(QMessageBox.Cancel)
        result = window.exec_()
        if result == QMessageBox.Save:
            return self.save()
        return result;

    def save(self):
        dialog = RenameDialog(self.playlist_name,"Save As")

        if dialog.exec_():
            name = dialog.text().strip()
            if name:
                self.playlist_name = dialog.text()
                self.playlist = PlaylistManager.instance().openPlaylist(self.playlist_name)
                self.playlist.set( list(self.playlist_data) )
                self.on_rename.emit(self,self.playlist_name)
                self.parent().dirty = False
                return QMessageBox.Save
        return QMessageBox.Cancel

    def load(self):
        dialog = OpenPlaylistDialog(self)
        if dialog.exec_():
            self.playlist_name = dialog.text()
            self.playlist = PlaylistManager.instance().openPlaylist(self.playlist_name)
            self.playlist_data = set(self.playlist.iter())
            self.on_rename.emit(self,self.playlist_name)
            self.refresh()
            return QMessageBox.Save
        return QMessageBox.Cancel

    def sync(self):
        pdialog = SyncProfileDialog(self)
        if pdialog.exec_():
            s = pdialog.export_settings()
            # feeling lazy right now, trusing no one will try to start
            # two sync dialogs at the same time.
            self.sdialog = SyncDialog(self.playlist_data,s,self)
            self.sdialog.start()
            self.sdialog.show()

    def export_playlist(self):

        caption = "Export Playlist"
        directory = os.path.join(os.getcwd(),self.playlist_name+".m3u")
        filter = "M3U (*.m3u)"
        filepath,filter = QFileDialog.getSaveFileName(self, caption, directory, filter)

        dialog = ExportM3uDialog(self.playlist_data,filepath,self)
        dialog.start()
        dialog.exec_()

    def import_playlist(self):

        caption = "Import Playlist"
        directory = os.getcwd()
        filter = "M3U (*.m3u)"
        filepath,filter = QFileDialog.getOpenFileName(self, caption, directory, filter)

        dialog = ImportM3uDialog(filepath,self)
        dialog.start()
        dialog.exec_()

        self.playlist_data = dialog.getData()
        self.playlist_name = os.path.splitext(os.path.split(filepath)[1])[0]
        self.on_rename.emit(self,self.playlist_name)
        self.refresh()

    def create_playlist(self):

        if len(self.playlist_data) > 0:
            self.set_playlist.emit(list(self.playlist_data))