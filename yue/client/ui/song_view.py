#! python34 ../../../test/test_client.py $this
import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.util import format_date

from ..widgets.slider import PositionSlider

class SongPositionView(QWidget):

    seek = pyqtSignal( int )
    next = pyqtSignal()
    prev = pyqtSignal()

    def __init__(self, parent=None):
        super(SongPositionView,self).__init__(parent);

        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(0,0,0,0)

        self.slider = PositionSlider( self );
        self.slider.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.slider.value_set.connect(self.seek.emit)
        self.slider.setObjectName("TimeSlider")

        self.btn_prev = QPushButton("<")
        self.btn_prev.setMinimumWidth(16)
        self.btn_prev.setMaximumWidth(32)
        self.btn_prev.clicked.connect(lambda:self.prev.emit())
        self.btn_prev.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)
        self.btn_prev.setObjectName("MediaPrev")

        self.btn_next = QPushButton(">")
        self.btn_next.setMinimumWidth(16)
        self.btn_next.setMaximumWidth(32)
        self.btn_next.clicked.connect(lambda:self.next.emit())
        self.btn_next.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)
        self.btn_next.setObjectName("MediaNext")

        self.hbox.addWidget(self.btn_prev)
        self.hbox.addWidget(self.slider)
        self.hbox.addWidget(self.btn_next)

    def setValue(self, v):
        if not self.slider.user_control:
            self.slider.setValue( v )

    def setMaximum(self, v):
        self.slider.setMaximum(v)

class SongPositionSlider(QSlider):

    def __init__(self, view, parent=None):
        super(SongPositionSlider,self).__init__(Qt.Horizontal,parent);
        self.setObjectName("TimeSlider")

        self.user_control = False
        self.view = view;

        #self.actionTriggered.connect(self.actionEvent)
        self.sliderReleased.connect(self.on_release)
        self.sliderPressed.connect(self.on_press)

    def mouseReleaseEvent(self,event):
        super().mouseReleaseEvent(event)
        pos = int(self.maximum()*(event.x()/self.width()))
        self.view.seek.emit( pos )

    def on_press(self):
        self.user_control = True

    def on_release(self):
        self.user_control = False
        self.view.seek.emit( self.value() )

def fmt_seconds( t ):
    m,s = divmod( t, 60)
    if m > 60:
        h,m = divmod(m,60)
        return "%d:%02d:%02d"%(h,m,s)
    else:
        return "%d:%02d"%(m,s)

class CurrentSongView(QWidget):

    # uid, new rating
    update_rating = pyqtSignal(int,int)
    def __init__(self, parent=None):
        super(CurrentSongView,self).__init__(parent);

        self.song = Song.new()
        self.song[Song.rating]= 5
        self.playlist_index  = 0
        self.playlist_length = 0
        self.equalizer_enabled = False
        self.is_library_song = True

        self.offseta = 0
        self.offsett = 0
        self.offsetb = 0
        self.offseta_max = -1
        self.offsett_max = -1
        self.offsetb_max = -1
        self.region_width = 0

        self.text_time = "000"
        self.text_date = "000"
        self.text_eq = "000"

        self.padt = 2
        self.padb = 2
        self.padtb = self.padt+self.padb

        self.menu_callback = None;

        self.setMouseTracking(True)
        self.disable_autoscroll = False
        self.mouse_hover = False

        self.timer_autoscroll = QTimer(self)
        self.timer_autoscroll.timeout.connect(self.on_timeout_event)
        self.timer_autoscroll.setSingleShot(False)
        self.timer_autoscroll.setInterval(125)
        self.timer_autoscroll.start(125)

        self.scroll_index = 0;
        self.scroll_speed = 2 # pixels per step

        self.rtdrawy=0
        self.rtdrawh=0
        self.rtdrawx=0
        self.enable_rate_tracking = False
        self.suggested_rating = 0

        self.resize()

    def resize(self):
        #f = QApplication.instance().font()
        f = self.font()
        fh = QFontMetrics(f).height()
        self.setFixedHeight( (fh+self.padtb) * 4)
        print("songview resize: fh:%d fam:%s ps:%d h:%d"%( \
            fh, \
            f.family(), \
            f.pointSize(), \
            QFontMetrics(f).height()))

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

        self.offseta = 0
        self.offsett = 0
        self.offsetb = 0
        self.offseta_max = -1
        self.offsett_max = -1
        self.offsetb_max = -1

        self.scroll_index = 0

        self.text_date = format_date( self.song[Song.last_played] )
        self.text_eq = "%d%%"%int(100.0*song[Song.equalizer]/Song.eqfactor)
        self.setPosition( 0 )

        if not self.timer_autoscroll.isActive():
            self.timer_autoscroll.start(125)

    def setPlaylistInfo(self,index,length):
        self.playlist_index  = index
        self.playlist_length = length
        self.is_library_song = 0<= self.playlist_index < self.playlist_length
        self.update()

    def setEQEnabled(self,b):
        self.equalizer_enabled = b
        self.update()

    def on_timeout_event(self):
        if self.disable_autoscroll:
            return

        if self.scroll_index == 0:
            if self.offseta < self.offseta_max and \
               self.offseta_max > self.region_width:
                self.offseta += self.scroll_speed
            else:
                self.offseta = 0

                if self.offsett_max > self.region_width:
                    self.scroll_index = 1
                elif self.offsetb_max > self.region_width:
                    self.scroll_index = 2
                #elif self.offseta_max > self.region_width:
                #    self.timer_autoscroll.stop()

        elif self.scroll_index == 1:
            if self.offsett < self.offsett_max and \
               self.offsett_max > self.region_width:
                self.offsett += self.scroll_speed
            else:
                self.offsett = 0

                if self.offsetb_max > self.region_width:
                    self.scroll_index = 2
                elif self.offseta_max > self.region_width:
                    self.scroll_index = 0
                #elif self.offsett_max > self.region_width:
                #    self.timer_autoscroll.stop()

        elif self.scroll_index == 2:
            if self.offsetb < self.offsetb_max and \
               self.offsetb_max > self.region_width:
                self.offsetb += self.scroll_speed
            else:
                self.offsetb = 0

                if self.offseta_max > self.region_width:
                    self.scroll_index = 0
                elif self.offsett_max > self.region_width:
                    self.scroll_index = 1
                #elif self.offsetb_max > self.region_width:
                #    self.timer_autoscroll.stop()

        self.update()

    def mouseMoveEvent(self,event):

        w=self.width()
        h=self.height()/4
        p=int(event.y()/h)

        if event.x() > self.rtdrawx and self.enable_rate_tracking:
            v = min(1.0,(event.y() - self.rtdrawy)/self.rtdrawh)
            v = round((1.0-v)*10)
            v = min(10,min(10,v))
            self.suggested_rating = v
            self.update()
            return

        if p==0 and self.region_width<self.offseta_max:
            self.offseta = int((self.offseta_max - w//4) * (event.x()/self.width()))
            self.offsett = 0
            self.offsetb = 0
            self.update()
        elif p==1 and self.region_width<self.offsett_max:
            self.offseta = 0
            self.offsett = int((self.offsett_max - w//4) * (event.x()/self.width()))
            self.offsetb = 0
            self.update()
        elif p==2 and self.region_width<self.offsetb_max:
            self.offseta = 0
            self.offsett = 0
            self.offsetb = int((self.offsetb_max - w//4) * (event.x()/self.width()))
            self.update()

    def enterEvent(self,event):
        self.enable_rate_tracking = False
        self.disable_autoscroll = True
        self.mouse_hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self,event):
        self.enable_rate_tracking = False
        self.disable_autoscroll = False
        self.mouse_hover = False
        self.scroll_index = 0;
        self.offseta = 0
        self.offsett = 0
        self.offsetb = 0
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        w = self.width()
        h = self.height()

        painter = QPainter(self)
        #painter.setFont(QApplication.instance().font())
        fh = painter.fontMetrics().height()

        fw1 = painter.fontMetrics().width('0')
        fw3 = (fw1+1)*3
        fwt = painter.fontMetrics().width(self.text_time)

        if self.offseta_max < 0:
            self.offseta_max = painter.fontMetrics().width(self.song[Song.artist])
            self.offsett_max = painter.fontMetrics().width(self.song[Song.title])
            self.offsetb_max = painter.fontMetrics().width(self.song[Song.album])

        rh = fh + self.padtb
        padl = 2;
        padr = 2;
        padlr = padl+padr

        row1h = fh + self.padt
        row2h = row1h+self.padtb+fh
        row3h = row2h+self.padtb+fh
        row4h = row3h+self.padtb+fh

        text = ""
        if self.is_library_song:
            text = "%d/%d"%(self.playlist_index,self.playlist_length)
        pltextlen = len(text)
        painter.drawText(padl,row1h-fh,w-padlr-fw3,fh,Qt.AlignRight,text)

        if self.equalizer_enabled:
            text = "EQ"
            if self.mouse_hover:
                text = self.text_eq
            painter.drawText(padl,row2h-fh,w-padlr-fw3,fh,Qt.AlignRight,text)

        #painter.drawText(padl,row3h-fh,w-padlr-fw3,fh,Qt.AlignRight,"33")

        text = "%d"%self.song[Song.play_count]
        painter.drawText(padl,row4h-fh,w-padlr-fw3,fh,Qt.AlignRight,text)

        if self.mouse_hover:
            painter.drawText(padl,row4h-fh,w,fh,Qt.AlignLeft,self.text_date)
        else:
            painter.drawText(padl,row4h-fh,w,fh,Qt.AlignLeft,self.text_time)

        rw = w - padl - padr - fwt - 2*fw3
        #painter.drawRect(2*padl+fwt,row4h-fh,rw,fh)
        #recth=4*rh-self.padtb
        recth=h-self.padtb
        pillh = recth//5
        pillo = (h-pillh*5)//2

        self.rtdrawy=pillo
        self.rtdrawh=pillh*5
        self.rtdrawx=w-fw3+1

        bgc = self.palette().dark()    # QBrush(QColor(160,175,220))
        fgc = self.palette().light()  # QBrush(QColor(60,60,200))

        if self.is_library_song:
            rating = self.song[Song.rating]
            if self.enable_rate_tracking:
                rating = self.suggested_rating
            n = rating//2

            for i in range(0,5):
                x=w-fw3+1
                y=h-((i+1)*pillh)-pillo+2
                pw=fw3-padr-1
                ph=pillh-2


                painter.fillRect(x,y,pw,ph,bgc)
                if i < n:
                    painter.fillRect(x,y,pw,ph,fgc)
            if rating%2==1:
                x=w-fw3+1
                y=h-((n+1)*pillh)-pillo+1
                pw=fw3-padr-1
                ph=pillh-2
                painter.fillRect(x,y+ph//2,pw,ph//2,fgc)

            default_pen = painter.pen()
            pen = QPen(default_pen)
            pen.setColor(QColor(0,0,0))
            pen.setWidth(2)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen)
            for i in range(0,5):
                x=w-fw3+1
                y=h-((i+1)*pillh)-pillo+2
                pw=fw3-padr-1
                ph=pillh-2
                painter.drawRect(x,y,pw-1,ph-1)
            painter.setPen(default_pen)

            #painter.drawRect(x,y,pw,ph)

        #recths = int(recth*(self.song[Song.rating]/10))
        #rectho = recth-recths
        #painter.fillRect(w-fw3+1,self.padt+rectho+1,fw3-padr-1,recths-1,QBrush(QColor(0,0,200)))

        painter.setClipping(True)
        self.region_width = w-(fw1+1)*pltextlen - fw3
        painter.setClipRegion(QRegion(0,0,self.region_width,row4h))

        a = max(0,self.offseta)
        t = max(0,self.offsett)
        b = max(0,self.offsetb)

        painter.drawText(padl-a,self.padt,2*self.offseta_max,fh,Qt.AlignLeft,self.song[Song.artist])
        painter.drawText(padl-t,self.padtb+fh,2*self.offsett_max,fh,Qt.AlignLeft,self.song[Song.title])
        painter.drawText(padl-b,2*(self.padtb+fh),2*self.offsetb_max,fh,Qt.AlignLeft,self.song[Song.album])

    def setMenuCallback(self,cbk):
        """
        callback as a function which accepts a menu and a song
        and returns nothing. the function should add actions to
        the given song
        """
        self.menu_callback = cbk

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.enable_rate_tracking = True
            event.accept()

    def mouseReleaseEvent(self, event):
        self.enable_rate_tracking = False

        if event.button() == Qt.RightButton and self.menu_callback is not None:
            menu = QMenu(self)
            self.menu_callback(menu,self.song)
            menu.exec_( event.globalPos() )

        if event.button() == Qt.LeftButton:
            if event.x() > self.rtdrawx:
                v = min(1.0,(event.y() - self.rtdrawy)/self.rtdrawh)
                v = round((1.0-v)*10)
                v = min(10,min(10,v))
                self.song[Song.rating] = v
                self.update_rating.emit(self.song[Song.uid],v)
                self.update()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Console Player")
    app.setQuitOnLastWindowClosed(True)
    window = CurrentSongView()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
