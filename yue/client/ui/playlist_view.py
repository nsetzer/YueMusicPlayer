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
from yue.client.widgets.LargeTable import LargeTable, TableColumn
from yue.client.widgets.SongTable import SongTable
from yue.client.widgets.LineEdit import LineEdit, LineEditHistory

from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library


from ...core.playlist import PlaylistManager, PlayListView
from ...core.library import Library

class PlaylistTable(LargeTable):
    """
        This is the default implementation for representing Songs in a Table Layout

        This is an extention to the LargeTable class, where each row of the table is a Song.
        And a Song has been implemented as a special type of List, this yeilds
        that the data for the table is still a 2d array of strings or integers

        This class initilizes a new LargeTable with all of the required
        columns to display information about a Song.

        It includes a way to highlight the DateStamp, but is turned off by default

        It also includes a way to edit the rating of a song by clicking within the row
        column, this can be turned off
    """

    def __init__(self, parent=None):
        super(PlaylistTable,self).__init__(parent)

        self.setLastColumnExpanding( True )
        self.showColumnHeader( False )
        self.showRowHeader( True )

    def initColumns(self):
        self.columns.append( TableColumn(self,Song.artist   ,"Song") )
        self.columns[-1].setWidthByCharCount(30)
        self.columns[-1].text_transform = lambda item,cell: "%s - %s"%(item[Song.artist],item[Song.title]);

    def keyPressDelete(self,event):
        sel = self.getSelectionIndex()
        self.data.delete( sel )
        self.setSelection([min(sel),])

        self.parent().update()

    def processDropEvent(self,source,row,data):

        if source is self:
            sel = self.getSelectionIndex()

            s,e = self.data.reinsertList(sel, row)

            self.setSelection( list(range(s,e)) )
        else:
            # dropped data from other source must all be songs
            if not all( [ isinstance(item,dict) and Song.uid in item for item in data ] ):
                return

            row = min(row, len(self.data))
            ids = [ song[Song.uid] for song in data ]
            self.data.insert( row, ids)

            self.setSelection( list(range(row,row+len(ids))) )

        self.parent().update()

    def shuffleSelection(self):
        sel = self.getSelectionIndex()
        if len(sel)<=1:
            self.data.shuffle_range()
        else:
            self.data.shuffle_selection( sel )
        self.parent().update()

class PlayListViewWidget(QWidget):
    """docstring for MainWindow"""
    def __init__(self):

        super(PlayListViewWidget, self).__init__()
        self.vbox = QVBoxLayout(self)

        self.tbl = PlaylistTable(self)
        self.tbl.addRowHighlightComplexRule( self.rowIsCurrentSong , QColor(255,0,0))

        self.btn_shuffle = QPushButton("Shuffle",self)
        self.btn_shuffle.clicked.connect( self.tbl.shuffleSelection )

        self.vbox.addWidget( self.tbl.container )
        self.vbox.addWidget( self.btn_shuffle )

        self.playlist = None
        self.current_index = -1

    def rowIsCurrentSong(self,idx):
        return idx == self.current_index

    def setPlaylist(self,library,playlist):

        self.playlist = playlist

        pl = playlist.getDataView( library )

        self.tbl.setData( pl )

        self.update()

    def update(self):
        """
        this must be called after making any changes to the playlist
        """

        if self.playlist is not None:
            self.current_index,_ = self.playlist.current()
        else:
            self.current_index = -1;

        super(PlayListViewWidget,self).update()


        self.tbl.update()

    def sizeHint(self):
        # the first number width, is the default initial size for this widget
        return QSize(300,400)