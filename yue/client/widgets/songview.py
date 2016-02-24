import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except:
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

        self.position = 0;

        painter = QPainter(self)
        fh = painter.fontMetrics().height()

        self.padt = 2
        self.padb = 2
        self.padtb = self.padt+self.padb
        self.setFixedHeight( (fh+self.padtb) * 4)

    def setPosition(self, pos ):
        self.position = pos

    def setCurrentSong(self, song):
        self.song = song
        self.text_time = "%d/%d - %d"%(0,0,0)
        self.update()

    def paintEvent(self, event):
        w = self.width()
        h = self.height()

        painter = QPainter(self)
        fh = painter.fontMetrics().height()

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

        painter.drawText(padl,row3h+self.padtb+2,w-padlr,fh,Qt.AlignRight,"00")
        painter.drawText(padl,row4h,self.text_time)
