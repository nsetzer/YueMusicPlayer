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
from yue.core.util import format_date, format_time

from yue.client.ui.library_view import LineEdit_Search

class HistoryTable(LargeTable):

    def initColumns(self):

        self.columns.append( TableColumn(self,"date","Date") )
        self.columns[-1].setWidthByCharCount(16)
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].text_transform = lambda r,c : format_date(c)
        self.columns.append( TableColumn(self,"column","Action") )
        self.columns[-1].text_transform = lambda r,c : "%s %s"%(r["column"],r["value"])
        self.columns[-1].setWidthByCharCount(15)
        self.columns.append( TableColumn(self,"artist","Artist") )
        self.columns[-1].setWidthByCharCount(25)
        self.columns.append( TableColumn(self,"title","Title") )
        self.columns[-1].setWidthByCharCount(30)
        self.columns.append( TableColumn(self,"album","Album") )
        self.columns[-1].setWidthByCharCount(20)

    def mouseReleaseRight(self,event):

        mx = event.x()
        my = event.y()
        cx,cy = self._mousePosToCellPos(mx,my)
        row,cur_c = self.positionToRowCol(mx,my)

        items = self.getSelection()

        menu = QMenu(self)

        menu.addAction("Refresh",self.parent().refresh)
        menu.addAction(QIcon(":/img/app_trash.png"),"Delete",lambda:self.action_delete(items))

        action = menu.exec_( event.globalPos() )

    def action_delete(self, records):
        # emit a signal, with a set of songs to delete
        # these songs must be addded to a set so that undo delete
        # can be implemented.
        # display a warning message before emiting any signal
        History.instance().delete(records)
        self.parent().refresh()

class HistoryView(QWidget):
    """docstring for MainWindow"""

    def __init__(self, parent=None):
        super(HistoryView, self).__init__(parent)

        self.vbox_main = QVBoxLayout(self)

        self.tbl_history = HistoryTable(self)
        self.tbl_history.showColumnHeader( True )
        self.tbl_history.showRowHeader( False )

        self.txt_search = LineEdit_Search(self,self.tbl_history, "Search History")

        self.vbox_main.addWidget( self.txt_search )
        self.vbox_main.addWidget( self.tbl_history.container )

        self.run_search("")

    def refresh(self):
        self.run_search( self.txt_search.text() , refresh=True)

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
