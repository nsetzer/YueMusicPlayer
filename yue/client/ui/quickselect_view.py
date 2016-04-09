#! python34 $this

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from enum import IntEnum

import os, sys
dirpath = os.path.dirname(os.path.abspath(__file__))
dirpath = os.path.dirname(dirpath)
sys.path.insert(0,dirpath)

isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

import yue
from yue.client.widgets.LargeTable import LargeTable, TableColumn
from yue.client.widgets.LineEdit import LineEdit

from yue.core.util import format_delta, string_quote
from yue.core.song import Song
from yue.core.search import ParseError
from yue.core.sqlstore import SQLStore
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from collections import namedtuple

class Record(IntEnum):
    key=0 # data key
    cnt=1 # song count
    ply=2 # total play count
    skp=3 # total skip count
    len=4 # total play time
    tme=5 # total listen time
    frq=6 # average frequency
    SIZE=7

# convert enum to pretty string
RecordMap = {
    Record.key:"Key",
    Record.cnt:"Song Count",
    Record.ply:"Play Count",
    Record.skp:"Skip Count",
    Record.len:"Play Time",
    Record.tme:"Listen Time",
    Record.frq:"Average Frequency",
}

def buildQuickList(songs,minimum,key_index,text_transform):

    """
    build a quick list given a set of songs
    An array of lists is return, with each index corresponding
    to the Record enum. This produces statistics based on either
    a artist or genre.

    minimum : records are dropped if they do not mean the minimum song
        count requirment.

    key_index : either Song.artist or Song.album

    text_transform:
        for key_index=Song.artist use text_transform=lambda x:[x,]
        for Song.album, split on ',' or ';'
    """
    data = {}

    for song in songs:
        skey = song[key_index]
        key_list = text_transform(skey)
        for key in key_list :
            if key not in data:
                data[key] = [0]*(int(Record.SIZE))
                data[key][Record.key] = key
            data[key][Record.cnt] += 1
            data[key][Record.ply] += song[Song.play_count]
            data[key][Record.skp] += song[Song.skip_count]
            data[key][Record.len] += song[Song.length]
            data[key][Record.tme] += song[Song.play_count] * song[Song.length]
            data[key][Record.frq] += song[Song.frequency]
            #data[key][c_rte] += song[Song.rating]
            #if song[MpMusic.RATING] > 0:
            #    data[key][c_rct] += 1

    records = []
    for key, record in data.items():
        if record[Record.cnt] >= minimum:
            record[Record.frq] = int(record[Record.frq]/record[Record.cnt])
            records.append( record )

    return records

class QuickSelectView(QWidget):
    """docstring for MainWindow"""

    # signal to emit when a playlist a new playlist is requested.
    create_playlist = pyqtSignal( str )

    def __init__(self,parent=None):
        super(QuickSelectView, self).__init__(parent)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.lbl_info = QLabel(self)
        self.table = QuickTable( self )

        #self.vbox.addLayout( self.hbox )
        self.vbox.addWidget( self.lbl_info )
        self.vbox.addWidget( self.table.container )

        self.col_count = 1

        self.favorites = {
            Song.artist:set(),
            Song.genre:set(),
        }

        self.selected = set()

        self.sort_reverse=True
        self.sort_index = Record.cnt
        self.display_index = Record.cnt
        self.display_class = Song.artist

        self.generateData();

    def setData(self, data):
        self.data = data
        self.formatData()

    def getDataRowCount(self):
        """ the total number of rows needed to display data in columns of 1,2, or 3"""
        return (len(self.data)//self.col_count) + (1 if len(self.data)%self.col_count else 0)

    def generateData(self):
        songs = Library.instance().search(None)
        text_transform = lambda x : [x,]
        if self.display_class == Song.genre:
            text_transform = lambda x : [ x.strip().title() for x in (x.replace(",",";").split(";")) if x.strip() ]
        data = buildQuickList(songs,2,self.display_class,text_transform)
        self.setData(data)

    def setFavorites(self,kind,favorites):
        self.favorites[kind] = set(favorites)

    def formatData(self):
        """
        organize records returned from buildQuickList to fit into the current table
        """

        self.data = sorted(self.data,key=lambda r:r[self.sort_index],reverse=self.sort_reverse)
        l = self.getDataRowCount()
        d = []
        for i in range(l):
            d.append( ["","","","","",""] )
        for i,record in enumerate(self.data):
            c = i // l # which column to place the item into
            r = i - l*c # which row to place the item into
            if self.display_index in (Record.len,Record.tme):
                d[r][ (c*2)     ] = format_delta(record[self.display_index])
            else:
                d[r][ (c*2)     ] = record[self.display_index]
            d[r][ (c*2) + 1 ] = record[0]
        self.table.setData( d )

        di = RecordMap[self.display_index]
        si = RecordMap[self.sort_index]
        txt="Showing %s for %s, sorted by %s."%(di,self.display_class.title(),si)
        self.lbl_info.setText(txt)

    def indexToRowCol(self,index):
        """ for a given index in the self.data list, return the row column for where it would
            be placed in a l-row tall by 3 column grid.
            the actual grid used is l-rows by 6 columns, where each grouping of two columns
            represent the same data: a data value and then the associated artist"""
        l = self.getDataRowCount()
        c = index // l # which column to place the item into
        r = index - l*c # which row to place the item into
        return (r,c)

    def rowColToIndex(self,row,col):
        """
            for a given row and column return the index the item belongs to.
            column should be either 1,2, or 3. as would be returned from indexToRowCol
            dervived from indexToRowCol
        """
        l = self.getDataRowCount()
        i = col*l
        j = row + i
        if j >= len(self.data): return -1 # chance of producing an error for unbalanced lists
        return j

    def isSelected(self,index):
        if 0 <= index < len(self.data):
            return self.data[index][Record.key] in self.selected
        return False

    def toggleSelect(self,key):

        if key in self.selected:
            self.selected.remove( key )
        else:
            self.selected.add( key )

    def isFavorite(self,index):
        if 0 <= index < len(self.data):
            return self.data[index][Record.key] in self.favorites[self.display_class]
        return False

    def toggleFavorite(self,index):
        if 0 <= index < len(self.data):
            record = self.data[index]
            favs = self.favorites[self.display_class]
            key = record[Record.key]
            if key in favs:
                favs.remove( key )
            else:
                favs.add(key)

    def setDisplayClass(self,idx):
        self.display_class = idx
        self.selected = set() # clear current selection
        self.generateData()

    def setDisplayIndex(self,idx):
        self.display_index = idx
        self.formatData()
        self.table.setColumnWidths()

    def setSortIndex(self,idx):
        self.sort_index = idx
        self.formatData()

    def reverseSort(self):
        self.sort_reverse = not self.sort_reverse
        self.formatData()

    def clearSelection(self):
        self.selected = set()

    def createPlaylist(self):

        terms = []
        for sel in self.selected:
            term = "%s=%s"%(self.display_class,string_quote(sel))
            terms.append(term)
        query = ' || '.join(terms)

        self.create_playlist.emit( query )

        self.selected = set()

    def getFavoriteArtists(self):
        return self.favorites[Song.artist]

    def getFavoriteGenres(self):
        return self.favorites[Song.genre]

    def getRecord(self,index):
        if 0 <= index < len(self.data):
            return self.data[index]

class QuickTable(LargeTable):
    """
        Quick Selection

        The quick selection tab allows you to select from the list of artists in your library. It also allows you to view statistics on each artist, and sort the list by these values.

        \\<table\\>
        Song Count | Displays the number of songs by that artist
        Playcount  | Displays the number of plays for that artist, equal to the sum of all plays of songs by that artist.
        Play Time  | Displays how long it would take to listen to each song by an artist once.
        Listen Time| This is the sum of Playcount * Length for each song by an artist
        Frequency  | This is the average frequency for all songs by the artist
        Rating Count | The sum of rated values for each song
        Count of Ratings | the number of songs rated by an artist
        \\</table\\>

        By clicking "Create" a new playlist will be made from the artists selected.

        By default an artist only appears in the list if there are at least 2 songs by that artist.

        use the build command to change the minimum value of songs per artist, "build 6" will set the minimum song count to 6.
    """
    def __init__(self,parent=None):

        super(QuickTable, self).__init__(parent)

        self.color_fav = QColor(200,0,0)
        self.color_sel = QColor(0,0,200)

        self.setAlwaysHideScrollbar(True,False)

        self.setSelectionRule(LargeTable.SELECT_NONE)
        self.showRowHeader(False)
        self.showColumnHeader(False)

        self.mouse_hover_index = -1; # tracks row hover, for highlighting, disabled currently

    def initColumns(self):

        self.columns.append( QuickTableColumn(self,0, "") )
        self.columns[-1].setTextAlign(Qt.AlignRight)
        #self.columns[-1].setWidthByCharCount(13)
        self.columns.append( QuickTableColumn(self,1, "") )

        self.columns.append( QuickTableColumn(self,2, "") )
        self.columns[-1].setTextAlign(Qt.AlignRight)
        #self.columns[-1].setWidthByCharCount(13)
        self.columns.append( QuickTableColumn(self,3, "") )

        self.columns.append( QuickTableColumn(self,4, "") )
        self.columns[-1].setTextAlign(Qt.AlignRight)
        #self.columns[-1].setWidthByCharCount(13)
        self.columns.append( QuickTableColumn(self,5, "") )

    def setData(self,data):
        super(QuickTable,self).setData(data)

    def resizeEvent(self,event):
        super(QuickTable, self).resizeEvent(event)
        self.setColumnWidths();

    def setColumnWidths(self):
        char_width = QFontMetrics(self.font()).width("X")

        preferred_width = char_width
        if len(self.data):
            preferred_width *= (2 + max( len(unicode(row[0])) for row in self.data) )

        self.columns[0].width = preferred_width
        self.columns[2].width = preferred_width
        self.columns[4].width = preferred_width
        w = self.width()
        min_width = char_width * 20
        # the minimum width for one column
        _p = preferred_width+min_width
        t=1 # set t to the minimum number of columns that could be shown
        for i in range(3,0,-1):
            if w >= _p*i:
                t = i
                break;
        # the new width to use
        s = ((w/t)-preferred_width)+1
        self.columns[1].width = s
        self.columns[3].width = s
        self.columns[5].width = s
        if t != self.parent().col_count:
            self.parent().col_count = t
            self.parent().formatData()
        return t # number of columns

    def getRow(self,col,row):
        """
            convert a column and row into an index into the main data
            array
        """
        if self.parent.col_count == 2:
            return self.parent.data[row]
        elif self.parent.col_count == 3:
            return self.parent.data[row]
        else:
            return self.parent.data[row]

    def mouseReleaseLeft(self,event):
        row,col = self.positionToRowCol(event.x(),event.y())
        index = self.parent().rowColToIndex(row,col//2)
        if index < len(self.parent().data):
            record = self.parent().data[ index ]
            self.parent().toggleSelect( record[Record.key] )
            #record[Record.sel] = not record[Record.sel]
        return True

    def mouseReleaseRight(self,event):

        row,col = self.positionToRowCol(event.x(),event.y())
        index = self.parent().rowColToIndex(row,col//2)

        contextMenu = QMenu(self)

        fav_text = "clear Favorite" if self.parent().isFavorite(index) else "set Favorite"
        act_fav = contextMenu.addAction(fav_text, lambda : self.parent().toggleFavorite(index))

        contextMenu.addSeparator()

        act = contextMenu.addAction("Create Playlist from Selection", self.parent().createPlaylist)
        act.setDisabled( len(self.parent().selected)==0 )

        act = contextMenu.addAction("Clear Selection", self.parent().clearSelection)
        act.setDisabled( len(self.parent().selected)==0 )


        contextMenu.addSeparator()

        submenu = contextMenu.addMenu("Display Information")
        act=submenu.addAction("Artist",lambda:self.parent().setDisplayClass(Song.artist))
        act.setDisabled( self.parent().display_class is Song.artist)
        act=submenu.addAction("Genre",lambda:self.parent().setDisplayClass(Song.genre))
        act.setDisabled( self.parent().display_class is Song.genre)

        submenu = contextMenu.addMenu("Display Content")
        act=submenu.addAction("Song Count",lambda:self.parent().setDisplayIndex(Record.cnt))
        act.setDisabled( self.parent().display_index is Record.cnt)
        act=submenu.addAction("Play Count",lambda:self.parent().setDisplayIndex(Record.ply))
        act.setDisabled( self.parent().display_index is Record.ply)
        act=submenu.addAction("Skip Count",lambda:self.parent().setDisplayIndex(Record.skp))
        act.setDisabled( self.parent().display_index is Record.skp)
        act=submenu.addAction("Play Time",lambda:self.parent().setDisplayIndex(Record.len))
        act.setDisabled( self.parent().display_index is Record.len)
        act=submenu.addAction("Listen Time",lambda:self.parent().setDisplayIndex(Record.tme))
        act.setDisabled( self.parent().display_index is Record.tme)
        act=submenu.addAction("Average Frequency",lambda:self.parent().setDisplayIndex(Record.frq))
        act.setDisabled( self.parent().display_index is Record.frq)

        submenu = contextMenu.addMenu("Sort Content")

        act=submenu.addAction(self.parent().display_class.title(),lambda:self.parent().setSortIndex(Record.key))
        act.setDisabled( self.parent().sort_index is Record.key)
        act=submenu.addAction("Song Count",lambda:self.parent().setSortIndex(Record.cnt))
        act.setDisabled( self.parent().sort_index is Record.cnt)
        act=submenu.addAction("Play Count",lambda:self.parent().setSortIndex(Record.ply))
        act.setDisabled( self.parent().sort_index is Record.ply)
        act=submenu.addAction("Skip Count",lambda:self.parent().setSortIndex(Record.skp))
        act.setDisabled( self.parent().sort_index is Record.skp)
        act=submenu.addAction("Play Time",lambda:self.parent().setSortIndex(Record.len))
        act.setDisabled( self.parent().sort_index is Record.len)
        act=submenu.addAction("Listen Time",lambda:self.parent().setSortIndex(Record.tme))
        act.setDisabled( self.parent().sort_index is Record.tme)
        act=submenu.addAction("Average Frequency",lambda:self.parent().setSortIndex(Record.frq))
        act.setDisabled( self.parent().sort_index is Record.frq)

        act=contextMenu.addAction("Reverse Sort", self.parent().reverseSort)
        if self.parent().sort_reverse:
            act.setIcon(QIcon(":/img/app_check.png"))

        contextMenu.addSeparator()

        item = self.parent().getRecord( index )

        act = contextMenu.addAction("Rename",lambda:self.action_rename(item))
        act.setDisabled( act is None )

        contextMenu.addAction("Refresh",self.parent().generateData)

        action = contextMenu.exec_( event.globalPos() )

    def action_edit_genre(self,index):
        pass
        #prompt = "Genres are comma ',' separated."
        #qlist = self.parent.getQuickList()
        #dialog = dialogRename(qlist[index][0],"Rename Genre",prompt)
        #if dialog.exec_():
        #    new_name = dialog.edit.displayText().strip();
        #    self.parent.editGenreName(qlist[index][0],new_name)
        #    buildArtistList()

    def action_edit_artist(self,index):
        pass
        #prompt = "Genres are comma ',' separated."
        #qlist = self.parent.getQuickList()
        #dialog = dialogRename(qlist[index][0],"Rename Artist")
        #if dialog.exec_():
        #    new_name = dialog.edit.displayText().strip();
        #    self.parent.editArtistName(qlist[index][0],new_name)
        #    buildArtistList()

    def action_rename(self, record):

        print(record)

    def leaveEvent(self,event):
        super(QuickTable,self).leaveEvent(event)
        self.mouse_hover_index = -1;
        #self.update();
        return

class QuickTableColumn(TableColumn):

    def __init__(self,parent,index,name=None):
        super(QuickTableColumn,self).__init__(parent,index,name)
        self.hover_index = -1;

    def paintItem(self,col,painter,row,item,x,y,w,h):
        col = self.index//2
        index = self.parent.parent().rowColToIndex(row,col)

        sel = self.parent.parent().isSelected( index )
        fav = self.parent.parent().isFavorite( index )

        if sel:
            painter.fillRect(x,y,w,h,self.parent.palette_brush(QPalette.Highlight))

        default_pen = painter.pen()
        if fav:
            painter.setPen(self.parent.color_fav)
        self.paintItem_text(col,painter,row,item,x,y,w,h)
        painter.setPen(default_pen)

