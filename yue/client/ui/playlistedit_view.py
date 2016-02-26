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

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from .library_view import LineEdit_Search

class PlaylistEditView(QWidget):
    """docstring for MainWindow"""
    def __init__(self, playlist_name):
        super(PlaylistEditView, self).__init__()
        self.vbox = QVBoxLayout(self)

        self.hbox1 = QHBoxLayout()
        self.hbox2 = QHBoxLayout()

        self.tbl_lib = SongTable( self )
        self.tbl_lib.showColumnHeader( True )
        self.tbl_lib.showRowHeader( False )

        self.tbl_pl = SongTable( self )
        self.tbl_pl.showColumnHeader( True )
        self.tbl_pl.showRowHeader( False )

        self.tbl_pl.update_data.connect(self.onUpdate)

        self.txt_search = LineEdit_Search(self,self.tbl_pl)
        self.txt_search.textEdited.connect(self.onTextChanged)
        self.lbl_search = QLabel("/")
        self.lbl_error  = QLabel("")

        self.hbox1.addWidget( self.txt_search )
        self.hbox1.addWidget( self.lbl_search )

        self.hbox2.addWidget( self.tbl_lib.container )
        self.hbox2.addWidget( self.tbl_pl.container )

        self.vbox.addLayout( self.hbox1 )
        self.vbox.addWidget( self.lbl_error )
        self.vbox.addLayout( self.hbox2 )

        self.lbl_error.hide()

        self.playlist = PlaylistManager.instance().openPlaylist(playlist_name)

        self.playlist_name = playlist_name

    def onUpdate(self):
        text = self.txt_search.text()
        self.run_search(text)

    def onTextChanged(self,text,update=0):
        self.run_search(text)

    def run_search(self, text, setText=False):
        """
        setText: if true set the text box to contain text
        """
        try:
            lib = Library.instance()
            data = list(lib.searchPlaylist( self.playlist_name, text, \
                orderby=self.tbl_pl.sort_orderby,
                reverse = self.tbl_pl.sort_reverse ))
            self.tbl_pl.setData(data)

            self.lbl_search.setText("%d/%d"%(len(data), len(lib)))

            data = list(lib.searchPlaylist( self.playlist_name, text, \
                invert = True,
                orderby=self.tbl_pl.sort_orderby,
                reverse = self.tbl_pl.sort_reverse ))
            self.tbl_lib.setData(data)

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

