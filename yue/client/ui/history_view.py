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
from yue.client.widgets.Tab import Tab

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.history import History
from yue.core.util import format_date, format_time

from yue.client.ui.library_view import LineEdit_Search

class HistoryTable(LargeTable):

    update_data = pyqtSignal()

    def __init__(self,parent=None):
        super(HistoryTable,self).__init__(parent)

        self.sort_orderby = [("date",Song.desc),]
        self.sort_reverse = False
        self.sort_limit = 3 # this limit controls maximum number of fields passed to ORDER BY

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

    def sortColumn(self,col_index):
        column = self.columns[col_index]
        index  =  column.index
        self.sort_reverse = self.setSortColumn(col_index) == -1
        if self.sort_orderby:

            if self.sort_orderby[0][0] == index:
                dir = Song.desc if self.sort_orderby[0][1] == Song.asc else Song.asc
                self.sort_orderby[0] = (index,dir)
            else:
                # remove copies of sort index, if any
                i=1;
                while i < len(self.sort_orderby):
                    if self.sort_orderby[1][0] == index or i+1 >= self.sort_limit:
                        self.sort_orderby.pop(i)
                        continue
                    i+=1
                dir = Song.desc if column.column_sort_default==-1 else Song.asc
                self.sort_orderby.insert(0,(index,dir))
        self.update_data.emit()


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

class HistoryView(Tab):
    """docstring for MainWindow"""

    def __init__(self, parent=None):
        super(HistoryView, self).__init__(parent)

        self.vbox_main = QVBoxLayout(self)
        self.vbox_main.setContentsMargins(0,5,0,0)

        self.hbox = QHBoxLayout()

        self.tbl_history = HistoryTable(self)
        self.tbl_history.showColumnHeader( True )
        self.tbl_history.showRowHeader( False )
        self.tbl_history.update_data.connect( self.refresh )

        self.cbox_action = QComboBox(self)
        self.txt_search = LineEdit_Search(self,self.tbl_history, "Search History")
        self.txt_search.textEdited.connect(self.onTextChanged)
        self.lbl_search = QLabel("/")
        self.lbl_error  = QLabel("")

        self.hbox.addSpacing( 5 )
        self.hbox.addWidget( self.cbox_action )
        self.hbox.addWidget( self.txt_search )
        self.hbox.addWidget( self.lbl_search )
        self.hbox.addSpacing( 5 )

        self.vbox_main.addLayout( self.hbox )
        self.vbox_main.addWidget( self.lbl_error )
        self.vbox_main.addWidget( self.tbl_history.container )

        self.lbl_error.hide()

    def onTextChanged(self,text,update=0):
        self.run_search(text)

    def refresh(self):
        self.run_search( self.txt_search.text() , refresh=True)

    def run_search(self, text, setText=False, refresh = False):
        """
        setText: if true set the text box to contain text
        """
        try:
            hist = History.instance()
            data = hist.search(text, \
                orderby = self.tbl_history.sort_orderby,
                reverse = self.tbl_history.sort_reverse )
            self.tbl_history.setData(data)

            self.txt_search.setStyleSheet("")
            self.lbl_search.setText("%d/%d"%(len(data), len(hist)))
            self.lbl_error.hide()

        except ParseError as e:
            self.txt_search.setStyleSheet("background: #CC0000;")
            self.lbl_error.setText("%s"%e)
            self.lbl_error.show()
        except Exception as e:
            raise e
