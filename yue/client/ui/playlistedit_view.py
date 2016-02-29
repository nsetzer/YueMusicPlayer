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

from yue.client.ui.rename_dialog import RenameDialog
from yue.client.ui.openpl_dialog import OpenPlaylistDialog

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from .library_view import LineEdit_Search

class PlayListEditTable(SongTable):
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
            self.parent().refresh()

class LibraryEditTable(SongTable):
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
            self.parent().refresh()

class PlaylistEditView(QWidget):
    """docstring for MainWindow"""

    on_rename = pyqtSignal(QWidget,str)

    def __init__(self, playlist_name):
        super(PlaylistEditView, self).__init__()
        self.vbox = QVBoxLayout(self)

        self.hbox1 = QHBoxLayout()
        self.hbox2 = QHBoxLayout()

        self.toolbar = QToolBar(self)
        self.toolbar.addAction(QIcon(':/img/app_save.png'),"save", self.save)
        self.toolbar.addAction(QIcon(':/img/app_open.png'),"load", self.load)
        self.toolbar.addAction(QIcon(':/img/app_export.png'),"Export")
        self.toolbar.addAction(QIcon(':/img/app_play.png'),"Play")

        self.tbl_lib = LibraryEditTable( self )
        self.tbl_pl = PlayListEditTable( self )

        self.tbl_lib.setSibling(self.tbl_pl)
        self.tbl_pl.setSibling(self.tbl_lib)

        self.tbl_pl.update_data.connect(self.onUpdate)

        self.txt_search = LineEdit_Search(self,self.tbl_pl)
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
        self.vbox.addLayout( self.hbox2 )

        self.lbl_error.hide()

        self.playlist_name = playlist_name
        self.playlist = PlaylistManager.instance().openPlaylist(self.playlist_name)
        self.playlist_data = set(self.playlist.iter())
        self.refresh()


    def onUpdate(self):
        text = self.txt_search.text()
        print(text)
        #self.run_search(text)

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

    def save(self):
        dialog = RenameDialog(self.playlist_name,"Save As")

        if dialog.exec_():
            name = dialog.text().strip()
            if name:
                self.playlist_name = dialog.text()
                self.playlist = PlaylistManager.instance().openPlaylist(self.playlist_name)
                self.playlist.set( list(self.playlist_data) )
                self.on_rename.emit(self,self.playlist_name)

    def load(self):
        dialog = OpenPlaylistDialog(self)
        if dialog.exec_():
            self.playlist_name = dialog.text()
            self.playlist = PlaylistManager.instance().openPlaylist(self.playlist_name)
            self.playlist_data = set(self.playlist.iter())
            self.on_rename.emit(self,self.playlist_name)
            self.refresh()

    def export(self):
            pass