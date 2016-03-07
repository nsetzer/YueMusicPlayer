#! python34 $this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import os, sys, time
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
        self.parent().playlist.delete( sel )
        self.setSelection([min(sel),])
        self.parent().updateData()

    def processDropEvent(self,source,row,data):

        if source is self:
            sel = self.getSelectionIndex()

            s,e = self.parent().playlist.reinsertList(sel, row)

            self.setSelection( list(range(s,e)) )
        else:
            # dropped data from other source must all be songs
            if not all( [ isinstance(item,dict) and Song.uid in item for item in data ] ):
                return

            row = min(row, len(self.data))
            ids = [ song[Song.uid] for song in data ]
            self.parent().playlist.insert( row, ids)
            self.setSelection( list(range(row,row+len(ids))) )

        self.parent().updateData()

    def shuffleList(self):
        self.parent().playlist.shuffle_range()
        self.parent().updateData()

    def shuffleSelection(self):
        self.parent().playlist.shuffle_selection( self.getSelectionIndex() )
        self.parent().updateData()

    def mouseDoubleClick(self,row,col,event):

        if event is None or event.button() == Qt.LeftButton:
            self.parent().play_index.emit( row )

    def mouseReleaseRight(self,event):

        items = self.getSelection()

        menu = QMenu(self)

        if len(items) == 1 and self.parent().menu_callback is not None:
            self.parent().menu_callback(menu,items[0])

        menu.addSeparator()

        if len(items) <= 1:
            menu.addAction( "Shuffle Playlist", self.shuffleList )
        else:
            menu.addAction( "Shuffle Selection", self.shuffleSelection)

        action = menu.exec_( event.globalPos() )


class PlayListViewWidget(QWidget):
    """docstring for MainWindow"""

    play_index = pyqtSignal( int )

    # signal that is emitted whenever the playlist duration changes.
    # (total duration, time remaining)
    # time remaining includes current song
    playlist_duration = pyqtSignal(int,int)

    def __init__(self, parent=None):
        super(PlayListViewWidget, self).__init__(parent)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.tbl = PlaylistTable(self)
        self.tbl.addRowHighlightComplexRule( self.rowIsCurrentSong , QColor(220,220,120))

        self.vbox.addWidget( self.tbl.container )

        self.playlist = None
        self.current_index = -1
        self.menu_callback = None


    def rowIsCurrentSong(self,idx):
        return idx == self.current_index

    def setPlaylist(self,library,playlist):

        self.library  = library
        self.playlist = playlist

        self.updateData()

    def scrollToCurrent(self):
        try:
            if self.playlist is not None:
                idx,_ = self.playlist.current()
                self.tbl.scrollTo( idx )
        except IndexError:
            pass
        self.update()

    def updateData(self):
        #s = time.clock()
        songs = self.library.songFromIds( self.playlist.iter() )


        try:
            if self.playlist is not None:
                self.current_index,_ = self.playlist.current()
        except IndexError:
            pass


        #print("plload",time.clock()-s)
        self.tbl.setData( songs )
        self.update()

    def update(self):
        """
        this must be called after making any changes to the playlist
        """

        self.current_index = -1;

        try:
            if self.playlist is not None:
                self.current_index,_ = self.playlist.current()
        except IndexError:
            pass

        duration = 0
        remaining = 0
        for idx,song in enumerate(self.tbl.data):
            duration += song[Song.length]
            if idx >= self.current_index:
                remaining += song[Song.length]
        #print(duration,remaining)
        self.playlist_duration.emit(duration,remaining)

        super(PlayListViewWidget,self).update()

        self.tbl.update()

    def sizeHint(self):
        # the first number width, is the default initial size for this widget
        return QSize(300,400)

    def setMenuCallback(self,cbk):
        """
        callback as a function which accepts a menu and a song
        and returns nothing. the function should add actions to
        the given song
        """
        self.menu_callback = cbk