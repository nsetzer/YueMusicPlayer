import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song


class SongPositionView(QWidget):

    def __init__(self, device, parent=None):
        super(SongPositionView,self).__init__(parent);

        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(0,0,0,0)

        self.slider = SongPositionSlider( device, self );
        self.slider.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        #self.slider.setTickInterval(15)
        #self.slider.setTickPosition(QSlider.TicksBelow)

        self.btn_prev = QPushButton("<")
        self.btn_prev.setMinimumWidth(16)
        self.btn_prev.setMaximumWidth(32)
        self.btn_prev.clicked.connect(device.prev)
        self.btn_prev.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)

        self.btn_next = QPushButton(">")
        self.btn_next.setMinimumWidth(16)
        self.btn_next.setMaximumWidth(32)
        self.btn_next.clicked.connect(device.next)
        self.btn_next.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)

        self.hbox.addWidget(self.btn_prev)
        self.hbox.addWidget(self.slider)
        self.hbox.addWidget(self.btn_next)

    def setValue(self, v):
        if not self.slider.user_control:
            self.slider.setValue( v )

    def setMaximum(self, v):
        self.slider.setMaximum(v)

class SongPositionSlider(QSlider):

    def __init__(self, device, parent=None):
        super(SongPositionSlider,self).__init__(Qt.Horizontal,parent);

        self.user_control = False
        self.device = device;

        #self.actionTriggered.connect(self.actionEvent)
        self.sliderReleased.connect(self.on_release)
        self.sliderPressed.connect(self.on_press)

    def mouseReleaseEvent(self,event):
        super().mouseReleaseEvent(event)
        pos = int(self.maximum()*(event.x()/self.width()))
        self.device.seek( pos )
        if self.device.isPaused():
            self.device.play()

    def on_press(self):
        self.user_control = True

    def on_release(self):
        self.user_control = False
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

        self.song = Song.new()

        self.text_time = ""

        fh = QFontMetrics(self.font()).height()
        self.padt = 2
        self.padb = 2
        self.padtb = self.padt+self.padb
        self.setFixedHeight( (fh+self.padtb) * 4)

        self.menu_callback = None;

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

    def setMenuCallback(self,cbk):
        """
        callback as a function which accepts a menu and a song
        and returns nothing. the function should add actions to
        the given song
        """
        self.menu_callback = cbk
    def mouseReleaseEvent(self, event):

        if event.button() == Qt.RightButton and self.menu_callback is not None:
            menu = QMenu(self)
            self.menu_callback(menu,self.song)
            menu.exec_( event.globalPos() )