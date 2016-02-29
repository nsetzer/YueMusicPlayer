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
from yue.core.settings import Settings
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

class LineEdit_Search(LineEdit):

    def __init__(self,parent,table, placeholder="Search Library"):
        super(LineEdit_Search,self).__init__(parent)
        self.table = table

        self.setPlaceholderText(placeholder)

    def keyReleaseEvent(self,event=None):
        super(LineEdit_Search,self).keyReleaseEvent(event)
        if event.key() == Qt.Key_Down:
            self.table.clearSelection( )
            self.table.setSelection( [0,] )
            self.table.updateTable(0)
            self.table.setFocus()

class LibraryTable(SongTable):

    def __init__(self,parent):
        super(LibraryTable,self).__init__(parent)

        self.current_uid = -1
        self.addRowTextColorComplexRule(self.currentSongRule,self.color_text_played_recent)

    def currentSongRule(self,row):
        return self.data[row][Song.uid] == self.current_uid

    def mouseReleaseRight(self,event):

        items = self.getSelection()

        menu = QMenu(self)

        act = menu.addAction("Play",lambda:self.action_play_next(items,True))
        act.setDisabled( len(items) != 1 )

        menu.addAction("Play next",lambda:self.action_play_next(items))
        menu.addSeparator()
        menu.addAction(QIcon(":/img/app_trash.png"),"Delete from Library")
        menu.addAction(QIcon(":/img/app_x.png"),"Bannish")

        if len(items) == 1:
            menu.addSeparator()
            self.parent().root.addSongActions(menu,items[0])

        action = menu.exec_( event.globalPos() )

    def action_play_next(self, songs, play=False):

        uids = [ song[Song.uid] for song in songs ]

        pl = PlaylistManager.instance().openCurrent()
        pl.insert_next( uids )
        #todo: i really need to find a better way to do this

        if play:
            self.parent().root.controller.device.next()

        self.parent().root.plview.updateData()

class LibraryView(QWidget):
    """docstring for MainWindow"""
    def __init__(self,root, parent=None):
        super(LibraryView, self).__init__(parent)
        self.root = root# see comment for root in playlist view

        #self.cwidget = QWidget()
        #self.setCentralWidget(self.cwidget);
        self.vbox = QVBoxLayout(self)

        self.hbox = QHBoxLayout()

        self.tbl_song = LibraryTable( self )
        self.tbl_song.showColumnHeader( True )
        self.tbl_song.showRowHeader( False )

        self.tbl_song.update_data.connect(self.onUpdate)

        self.txt_search = LineEdit_Search(self,self.tbl_song)
        self.txt_search.textEdited.connect(self.onTextChanged)
        self.lbl_search = QLabel("/")
        self.lbl_error  = QLabel("")

        self.hbox.addWidget( self.txt_search )
        self.hbox.addWidget( self.lbl_search )

        self.vbox.addLayout( self.hbox )
        self.vbox.addWidget( self.lbl_error )
        self.vbox.addWidget( self.tbl_song.container )

        self.lbl_error.hide()

        order = Settings.instance()["ui_library_column_order"]
        if len(order):
            self.tbl_song.columns_setOrder(order)
        self.run_search("")

    def getColumnState(self):
        return self.tbl_song.columns_getOrder( )

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
            data = lib.search( text, \
                orderby=self.tbl_song.sort_orderby,
                reverse = self.tbl_song.sort_reverse )
            self.tbl_song.setData(data)
            self.lbl_search.setText("%d/%d"%(len(data), len(lib)))

            if not self.lbl_error.isHidden():
                self.txt_search.setStyleSheet("")
                self.lbl_error.hide()

            if setText:
                self.txt_search.setText( text )

            self.tbl_song.scrollTo( 0 )
        except ParseError as e:
            self.txt_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()
        except Exception as e:
            raise e

    def setCurrentSongId( self, uid ):
        self.tbl_song.current_uid = uid
        self.tbl_song.update()

