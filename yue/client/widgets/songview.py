import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song


class SongPositionView(QScrollBar):

    def __init__(self, device, parent=None):
        super(SongPositionView,self).__init__(Qt.Horizontal,parent);

        self.device = device;

        self.actionTriggered.connect(self.actionEvent)
        self.sliderReleased.connect(self.on_release)

    def actionEvent(self,action):
        #QAbstractSlider.SliderMove

        # button is pressed
        if action == QAbstractSlider.SliderSingleStepAdd:
            self.device.next()
        elif action == QAbstractSlider.SliderSingleStepSub:
            self.device.prev()

        # gutter is pressed.
        elif action == QAbstractSlider.SliderPageStepAdd:
            if self.device.isPaused():
                self.device.play()
            self.device.seek( self.value()+5 )
        elif action == QAbstractSlider.SliderPageStepSub:
            if self.device.isPaused():
                self.device.play()
            self.device.seek( self.value()-5 )

    def on_release(self):

        if self.device.isPaused():
            self.device.play()
        self.device.seek( self.value() )

def fmt_seconds( t ):
    m,s = divmod( t, 60)
    if m > 60:
        h,m = divmod(m,60)
        return "%d:%02d:%02d"%(h,m,s)
    else:
        return "%d:%02d"%(m,s)

class CurrentSongView(QWidget):
    def __init__(self, parent=None):
        super(CurrentSongView,self).__init__(parent);

        self.song = {
            Song.artist : "None",
            Song.title  : "None",
            Song.album  : "None",
            Song.length : 0,
            Song.play_count : 0,
        }

        self.text_time = ""

        fh = QFontMetrics(self.font()).height()
        self.padt = 2
        self.padb = 2
        self.padtb = self.padt+self.padb
        self.setFixedHeight( (fh+self.padtb) * 4)

    def setPosition(self, position ):
        length = self.song[Song.length]
        remaining = length - position

        self.text_time = "%s/%s - %s"%(
                fmt_seconds(position),
                fmt_seconds(length),
                fmt_seconds(remaining) )

        self.update()

    def setCurrentSong(self, song):
        self.song = song
        self.setPosition( 0 )

    def paintEvent(self, event):
        w = self.width()
        h = self.height()

        painter = QPainter(self)
        fh = painter.fontMetrics().height()
        fw1 = painter.fontMetrics().width('000')
        fw2 = painter.fontMetrics().width(self.text_time)

        rh = fh + self.padtb
        padl = 2;
        padr = 2;
        padlr = padl+padr

        row1h = fh + self.padt
        row2h = row1h+self.padtb+fh
        row3h = row2h+self.padtb+fh
        row4h = row3h+self.padtb+fh

        painter.drawText(padl,row1h,self.song[Song.artist])
        painter.drawText(padl,row2h,self.song[Song.title])
        painter.drawText(padl,row3h,self.song[Song.album])

        painter.drawText(padl,row4h-fh,w-padlr-fw1,fh,Qt.AlignRight,"00")
        painter.drawText(padl,row4h,self.text_time)

        rw = w - padl - padr - fw2 - 2*fw1
        painter.drawRect(2*padl+fw2,row4h-fh,rw,fh)
        painter.drawRect(w-fw1,self.padt,fw1-padr,4*rh-self.padtb)
