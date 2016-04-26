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
from yue.client.widgets.TableEditColumn import EditColumn
from yue.client.widgets.SongTable import SongTable, SongDateColumn
from yue.client.widgets.LargeTable import TableColumn, LargeTable
from yue.client.widgets.LibraryTree import LibraryTree
from yue.client.widgets.LineEdit import LineEdit
from yue.client.widgets.FlatPushButton import FlatPushButton

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.history import History

from yue.client.ui.library_view import LineEdit_Search

class HistoryTable(LargeTable):

    def initColumns(self):

        self.columns.append( TableColumn(self,"date","Date") )
        self.columns[-1].setWidthByCharCount(30)
        self.columns.append( TableColumn(self,"value","Action") )
        self.columns[-1].setWidthByCharCount(30)
        self.columns.append( TableColumn(self,"artist","Artist") )
        self.columns[-1].setWidthByCharCount(30)
        self.columns.append( TableColumn(self,"title","Title") )
        self.columns[-1].setWidthByCharCount(30)

class HistoryView(QWidget):
    """docstring for MainWindow"""

    def __init__(self, parent=None):
        super(HistoryView, self).__init__(parent)

        self.vbox_main = QVBoxLayout(self)

        self.tbl_history = HistoryTable(self)
        self.txt_search = LineEdit_Search(self,self.tbl_history, "Search History")

        self.vbox_main.addWidget( self.txt_search )
        self.vbox_main.addWidget( self.tbl_history.container )

        self.run_search("")

    def run_search(self, text, setText=False, refresh = False):
        """
        setText: if true set the text box to contain text
        """
        try:
            lib = Library.instance()
            data = list(History.instance().search(""))
            self.tbl_history.setData(data)
        except ParseError as e:
            self.txt_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()
        except Exception as e:
            raise e
