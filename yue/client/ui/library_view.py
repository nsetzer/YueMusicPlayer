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

class LineEdit_Search(LineEdit):

    def __init__(self,parent,table, placeholder="Search Library"):
        super(LineEdit_Search,self).__init__(parent)
        self.parent = parent
        self.table = table

        self.setPlaceholderText(placeholder)

    def keyReleaseEvent(self,event=None):
        super(LineEdit_Search,self).keyReleaseEvent(event)
        if event.key() == Qt.Key_Down:
            self.table.clearSelection( )
            self.table.setSelection( [0,] )
            self.table.updateTable(0)
            self.table.setFocus()

class LibraryView(QWidget):
    """docstring for MainWindow"""
    def __init__(self):

        super(LibraryView, self).__init__()
        #self.cwidget = QWidget()
        #self.setCentralWidget(self.cwidget);
        self.vbox = QVBoxLayout(self)

        self.hbox = QHBoxLayout()

        self.tbl_song = SongTable( self )
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



        self.run_search("")

    def onUpdate(self):
        text = self.txt_search.text()
        self.run_search(text)

    def onTextChanged(self,text,update=0):
        self.run_search(text)

    def run_search(self, text):
        try:
            lib = Library.instance()
            data = lib.search( text, \
                orderby=self.tbl_song.sort_orderby,
                reverse = self.tbl_song.sort_reverse )
            self.tbl_song.setData(data)
            self.lbl_search.setText("%d/%d"%(len(data), len(lib)))

            self.txt_search.setStyleSheet("")
            self.lbl_error.hide()

        except ParseError as e:
            self.txt_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()
        except Exception as e:
            raise e

