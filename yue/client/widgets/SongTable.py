#! python34 $this

import os
import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from functools import lru_cache

from ...core.library import Library
from ...core.song import Song
from ...core.util import format_date, format_time
from .LargeTable import LargeTable, TableColumn
from .TableEditColumn import EditColumn

from yue.client.SymTr import SymTr

import time

class SongTable(LargeTable):
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
    color_text_played_recent = QColor(200,0,200)
    color_text_played_not_recent = QColor(200,0,0)
    color_text_banish = QColor(128,128,128)

    date_mark_1 = 0 # time corresponding to the start of the day as integer time stamp
    date_mark_2 = 0 # time corresponding to 14 days ago or (whatever needs to be defined.

    rating_mouse_tracking = True;

    modify_song = pyqtSignal(dict)      # emitted whenever the table updates a row value
                                        # since each row is a reference to a Song
                                        # this is a modification of Song Data
    modify_song_rating = pyqtSignal(dict)

    update_data = pyqtSignal()

    def __init__(self,parent=None):
        super(SongTable,self).__init__(parent)

        self.sort_orderby = [(Song.artist,Song.asc),
                             (Song.album,Song.asc),
                             (Song.title,Song.asc)]
        self.sort_reverse = False
        self.sort_limit = 3 # this limit controls maximum number of fields passed to ORDER BY

        # enable highlighting of the current song
        #self.rule_selected = lambda row: self.data[row][EnumSong.SELECTED]
        self.rule_banish = lambda row: self.data[row][Song.blocked]

        # highlight songs that are selected
        #self.addRowHighlightComplexRule(self.rule_selected,self.color_text_played_recent)

        # change text color for banished songs
        self.addRowTextColorComplexRule(self.rule_banish,self.color_text_banish)

        self.date_mark_1 = time.time() - (24*60*60)
        self.date_mark_2= self.date_mark_1 - (13*24*60*60) # date of two weeks ago

    def setRuleColors(self,rc_recent,rc_not_recent,rc_banish,rc_selected):
        self.color_text_played_recent.setRed(rc_recent.red())
        self.color_text_played_recent.setGreen(rc_recent.green())
        self.color_text_played_recent.setBlue(rc_recent.blue())

        self.color_text_played_not_recent.setRed(rc_not_recent.red())
        self.color_text_played_not_recent.setGreen(rc_not_recent.green())
        self.color_text_played_not_recent.setBlue(rc_not_recent.blue())

        self.color_text_banish.setRed(rc_banish.red())
        self.color_text_banish.setGreen(rc_banish.green())
        self.color_text_banish.setBlue(rc_banish.blue())

        rules = self.getRowHighlightComplexRule()
        for i in range(len(rules)):
            if rule[i][0] == self.rule_selected:
                self.setRowHighlightComplexRule(i,None,rc_selected)

        rules = self.getRowTextColorComplexRule()
        for i in range(len(rules)):
            if rules[i][0] == self.rule_banish:
                self.setRowTextColorComplexRule(i,None,rc_banish)
        self.update()

    def initColumns(self):
        self.columns.append( SongEditColumn(self,Song.play_count     ,"Play Count",int) )
        self.columns[-1].setShortName("#")
        self.columns[-1].setWidthByCharCount(3)
        self.columns[-1].setMinWidthByCharCount(2)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setDefaultSortReversed(True)
        self.columns.append( SongEditColumn(self,Song.artist   ,"Artist") )
        self.columns[-1].setWidthByCharCount(30)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified(r,Self.artist,v))
        self.columns.append( SongEditColumn(self,Song.title    ,"Title") )
        self.columns[-1].setWidthByCharCount(30)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified(r,Self.title,v))
        self.columns.append( SongEditColumn(self,Song.album    ,"Album") )
        self.columns[-1].setWidthByCharCount(20)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified(r,Self.album,v))
        self.columns.append( TableColumn(self,Song.length   ,"Length") )
        self.columns[-1].setWidthByCharCount(7)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].text_transform = lambda row_data,cell_item: format_time(cell_item);
        self.columns.append( TableColumn_Rating(self,Song.rating   ,"Rating") )
        self.columns[-1].setWidthByCharCount(11)
        self.columns[-1].setMinWidthByCharCount(7)
        self.columns[-1].setTextAlign(Qt.AlignCenter)
        self.columns[-1].setDefaultSortReversed(True)
        self.columns.append( SongEditColumn(self,Song.genre    ,"Genre") )
        self.columns[-1].setWidthByCharCount(15)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified(r,Self.genre,v))
        self.columns.append( TableColumn(self,Song.frequency,"Frequency") )
        self.columns[-1].setShortName("Freq")
        self.columns[-1].setWidthByCharCount(4)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns.append( SongDateColumn(self,Song.last_played,"Last Played") )
        self.columns[-1].setWidthByCharCount(16)
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].text_transform = lambda r,c : format_date(c)
        self.columns.append( TableColumn(self,Song.file_size ,"File Size") )
        self.columns[-1].setWidthByCharCount(9)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setDefaultSortReversed(True)
        self.columns.append( SongEditColumn(self,Song.skip_count,"Skip Count") )
        self.columns[-1].setWidthByCharCount(10)
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setTextAlign(Qt.AlignCenter)
        self.columns.append( SongEditColumn(self,Song.comment  ,"Comment") )
        self.columns[-1].setWidthByCharCount(20)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified(r,Self.comment,v))
        self.columns.append( TableColumn(self,Song.date_added,"Date Added") )
        self.columns[-1].setWidthByCharCount(16)
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].text_transform = lambda r,c : format_date(c)
        self.columns.append( SongEditColumn(self,Song.year     ,"Year",int) )
        self.columns[-1].setWidthByCharCount(5)
        self.columns[-1].setDefaultSortReversed(True)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified_int(r,Self.year,v))
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns.append( SongEditColumn(self,Song.album_index,"Album Index",int) )
        self.columns[-1].setShortName("Idx")
        self.columns[-1].setWidthByCharCount(11)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified_int(r,Self.album_index,v))
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns.append( TableColumn(self,Song.uid   ,"ID") )
        #self.columns[-1].text_transform = lambda song,index: unicode(song.id)
        self.columns[-1].setWidthByCharCount(22)
        self.columns.append( PathEditColumn(self,Song.path     ,"Path") )
        self.columns[-1].setWidthByCharCount(30)
        #self.columns[-1].cell_modified.connect(lambda r,v: self.song_modified(r,Self.path,v))
        self.columns.append( TableColumn(self,Song.path     ,"Extension") )
        self.columns[-1].setShortName("Ext")
        self.columns[-1].setWidthByCharCount(6)
        self.columns[-1].text_transform = lambda song,index: (os.path.splitext(song[Song.path])[1].upper())[1:]
        # TODO: this field no longer means anythign when using an sql backed library
        self.columns[-1].setSortUseTextTransform(True)
        self.columns.append( TableColumn(self,Song.equalizer,"Volume Eq") )
        self.columns[-1].setShortName("EQ%")
        self.columns[-1].setWidthByCharCount(10)
        self.columns[-1].setTextAlign(Qt.AlignRight)
        self.columns[-1].setDefaultSortReversed(True)
        #self.columns.append( TableColumn(self,EnumSong.SPECIAL,"Special") )
        #self.columns[-1].setWidthByCharCount(7)
        #self.columns[-1].setTextAlign(Qt.AlignRight)
        #self.columns[-1].setDefaultSortReversed(True)
        #self.columns.append( TableColumn_Score(self,EnumSong.SCORE,"Score") )
        #self.columns[-1].setWidthByCharCount(7)
        #self.columns[-1].setTextAlign(Qt.AlignRight)
        #self.columns[-1].setDefaultSortReversed(True)
        self.columns.append( SongEditColumn(self,Song.lang    ,"Language") )
        self.columns[-1].setShortName("LANG")
        self.columns[-1].setWidthByCharCount(15)
        #self.columns[-1].cell_modified.connect(self.song_modified)
        self.columns.append( SongEditColumn(self,Song.country    ,"Country") )
        self.columns[-1].setShortName("ctry")
        self.columns[-1].setWidthByCharCount(15)
        #self.columns[-1].cell_modified.connect(self.song_modified)
        self.columns.append( SongEditColumn(self,Song.composer    ,"Composer") )
        self.columns[-1].setWidthByCharCount(15)
        #self.columns[-1].cell_modified.connect(self.song_modified)
        #self.columns.append( TableColumn(self,EnumSong.SOURCELIB,"Source Library") )
        #self.columns[-1].setShortName("Src")
        #self.columns[-1].setWidthByCharCount(15)
        title="Onsets Per Minute"
        self.columns.append( TableColumn(self,Song.opm ,title) )
        self.columns[-1].setShortName("OPM")
        self.columns[-1].setDefaultSortReversed(True)
        self.columns[-1].setWidthByCharCount(len(title))
        self.columns[-1].setTextAlign(Qt.AlignRight)

        self.columns_setDefaultOrder( self.columns_getOrder() )

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

    def getColumn(self,song_enum,check_hidden=False):
        """
            return the associated column for a song enum, EnumSong.Artist. EnumSong.Title, etc

            when check_hidden is false:
                returns None when the table is not currently displayed
            otherwise returns the column
        """
        for col in self.columns:
            if col.index == song_enum:
                return col
        if check_hidden:
             for col in self.columns_hidden:
                if col.index == song_enum:
                    return col
        return None

    def setData(self,data):
        super(SongTable,self).setData(data)
        # update time colors when the table is updated
        self.date_mark_1 = time.time() - (24*60*60)
        self.date_mark_2= self.date_mark_1 - (13*24*60*60) # date of two weeks ago

    #def song_modified(self,rows,column,value):
    #    #print rows,text
    #    # value could be an integer or unicode value
    #    for row in rows:
    #        self.modify_song.emit(self.data[row])


class TableColumn_Rating(TableColumn):
    """
        A custom table column for displaying the current rating
        as a collection of stars also handles editing rating
        by clicking with the cell.
    """
    suggested_rating = -1
    suggested_rating_row = -1

    def __init__(self,parent,index,name=""):
        super(TableColumn_Rating,self).__init__(parent,index,name)


        #qc1 = QColor(200,0,0)
        #self.star_brush = QBrush(qc1)

    def paintItem(self,col,painter,row,item,x,y,w,h):

        #if isinstance(item,int):
        #    if self.suggested_rating_row == row:
        #        item = self.suggested_rating
        #    _w = item/5.0 * w
        #    painter.fillRect(x,y,_w,h,self.parent.color_rating);
        #Qt.WindingFill
        if row == self.suggested_rating_row:
            item = self.suggested_rating

        _c = 2          # top/bottom padding constant
        _h = h-(2*_c)   # height is height minus padding
        _w = _h         # 5 point star is fit inside a square
        _step = (w-5*_w)//5 # a step is the distance between each star
        _hstep = _step//2   # half step

        if _step < 0:
            if item == 0:
                self.paintItem_text(col,painter,row,item,x,y,w,h)
            else:
                self.paintItem_text(col,painter,row,item/2.0,x,y,w,h)

            return

        #pf = u"\u2605" # full BLACK STAR
        #ph = u"\u2606" # half WHITE STAR
        #pe = u"\u2022" # empty BLACK DOT
        #text = pf*(item/2) + (ph if item%2==1 else '') + pe*((10-item)/2)
        #self.paintItem_text(col,painter,row,text,x,y,w,h)
        #return

        #if item < 1:
        #    return

        ps = QPointF( 0   , .35*_h   ) # start point

        #    order of points ( 1 is start/finish)
        #           3
        #        12   45
        #          086
        #         9   7
        #painter.setRenderHint( QPainter.Antialiasing )
        star_shape = QPolygonF(
            [
            ps, \
            QPointF(  .4 *_w , .35*_h   ), \
            QPointF(  .5 *_w ,    0     ), \
            QPointF(  .6 *_w , .35*_h   ), \
            QPointF(      _w , .35*_h   ), \

            QPointF(  .65*_w , .55*_h   ), \
            QPointF(  .8 *_w ,     _h   ), \
            QPointF(  .5 *_w , .7 *_h   ), \
            QPointF(  .2 *_w ,     _h   ), \
            QPointF(  .35*_w , .55*_h   ), \

            ps, \
            ]
        )
        #star_shape.toPolygon()

        #star_shape.translate(x+5,y+4)
        #print star_shape.isClosed()
        path = QPainterPath()
        path.addPolygon(star_shape)

        #path.closeSubpath()
        path.translate(x+_hstep,y+2)

        # _hstep then:
        #   _w+_step
        # _c2 = starting offset + # full stars + half star if needed
        _cw = _hstep + (_w+_step)*(item//2) + (_w//2)*(item%2) + 1

        if x < self.parent.data_cell_clip_x:
            _cw = x + _cw - self.parent.data_cell_clip_x
            x = self.parent.data_cell_clip_x

        tmp = painter.pen().color()
        alt_col =  QColor(tmp.red(),tmp.green(),tmp.blue(),64)

        for i in range(5):
            #painter.drawPolygon(star_shape,Qt.WindingFill)
            painter.fillPath(path,alt_col)
            path.translate(_w+_step,0)
        path.translate(-5*(_w+_step),0)

        painter.setClipRect(x,y,_cw,h)
        for i in range((min(10,item)+1) // 2):
            painter.fillPath(path,painter.pen().color())
            path.translate(_w+_step,0)
        #painter.setRenderHint(0) # QPainter.Antialiasing

    def mouseDoubleClick(self,row_index,posx,posy):
        if not self.parent.rating_mouse_tracking:
            return False
        song = self.parent.data[row_index]
        song[Song.rating] = self.suggested_rating

        Library.instance().update(song[Song.uid],**{self.index:self.suggested_rating})

        #self.parent.modify_song.emit(self.parent.data[row_index])
        #self.parent.modify_song_rating.emit(self.parent.data[row_index])
        return True#blocking return

    def mouseHover(self,row_index,posx,posy):
        if not self.parent.rating_mouse_tracking:
            return False

        _c = 2
        _w = self.parent.row_height-(2*_c)
        _step = ((self.width-4)-5*_w)//5
        _hstep = max(_step//2,4) # determines padding for getting zero value
        # the calculation for _cw cannot be reversed
        # therefore a forloop is used to guess and check the value
        value = 0
        for i in range(1,11): # test 1-10
            _cw = _hstep + (_w+_step)*((i-1)//2) + (_w//2)*((i-1)%2)
            if posx > _cw:
                value = i
            else:
                break
        self.suggested_rating = value           #
        self.suggested_rating_row = row_index   # used in drawing
        return True # blocking return

    def mouseHoverExit(self,event):
        self.suggested_rating = -1
        self.suggested_rating_row = -1

class SongDateColumn(TableColumn):
    """
        A custom table column for changing the color of the
        text used when drawing the date for the last
        time the song was played
    """

    def paintItem(self,col,painter,row,item,x,y,w,h):
        default_pen = painter.pen()

        song = self.parent.data[row]
        new_pen = default_pen
        if self.parent.date_mark_1 != 0 and self.parent.date_mark_2 !=0 and not song[Song.blocked]:
            if song[Song.last_played] > self.parent.date_mark_1:
                new_pen = self.parent.color_text_played_recent
            elif song[Song.last_played] < self.parent.date_mark_2:
                new_pen = self.parent.color_text_played_not_recent
        painter.setPen(new_pen)
        self.paintItem_text(col,painter,row,item,x,y,w,h)
        painter.setPen(default_pen)

class SongEditColumn(EditColumn):
    # register a signal to update exif data when editing is done,.
    # this will enable searching on data that has been modified.
    def __init__(self,parent,index,name=None,data_type=unicode):
        super(SongEditColumn,self).__init__(parent,index,name,data_type)
        self.cell_modified.connect(self.editing_finished)

    def editing_finished(self,rows,new_value):

        for row in rows:
            song = self.parent.data[row]
            #print(song[Song.uid], new_value)
            Library.instance().update(song[Song.uid],**{self.index:new_value})

    def editor_insert(self,chara):
        # enable japanese character input
        self.editor.insert(chara)
        o = SymTr.SymTr(self.editor.buffer)
        if o.nstring != self.editor.buffer:
            self.editor.buffer = o.nstring
            self.editor.insert_index=o.position

class PathEditColumn(SongEditColumn):
    def editing_finished(self,rows,new_value):
        for row in rows:
            # yes the editor already updated the row, but he did it wrong!
            new_value = new_value.replace('"','')
            # if plat win / -> \
            # if plat lin \ -> \
            song = self.parent.data[row]
            song[Song.path] =  new_value
            Library.instance().update(song[Song.uid],**{Song.path:new_value})

if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    #style_set_custom_theme("D:\\Dropbox\\Scripting\\PyModule\\GlobalModules\\src\\","default",app)

    from Song_LibraryFormat import *
    path = r"D:\Dropbox\ConsolePlayer\user\music.libz"

    t1 = SongTable()
    t1.setData(musicLoad_LIBZ(path))
    t1.container.resize(800,320)
    t1.container.show()

    #p = QApplication.palette()
    #CR = [QPalette.Light,QPalette.Midlight,QPalette.Mid,QPalette.Dark,QPalette.Shadow]
    #for cr in CR:
    #    c = p.color(QPalette.Active,cr)
    #    print c.red(),c.blue(),c.green()

    sys.exit(app.exec_())