#! python34 ../../../test/test_client.py $this

import os,sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

isPosix = os.name == 'posix'


from yue.core.sound.device import MediaState

class PlayButton(QWidget):
    state_btn1 = True      # play / pause
    state_btn2 = False      # stop playback / continue playback on song end
    state_hvr1 = True   # mouse over
    state_hvr2 = False  # mouse over
    state_mouseDown = False # mouse held down
    location = 0 # which button the mouse is over

    on_play = pyqtSignal(MediaState)
    on_stop = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(PlayButton, self).__init__( parent )

        self.path = QPainterPath()
        self.path.addEllipse(QRectF(5,5,90,90))

        self.cont_size = 40;         # size of inner circle
        l = 95 - self.cont_size      # place the inner circle on the right edge
        t = 50 - self.cont_size/2    # to make a cresent moon
        self.path2 = QPainterPath()

        self.path2.addEllipse(QRectF(l,t,self.cont_size,self.cont_size))

        points = [QPointF(0,0),QPointF(0,100),QPointF(100,50)]
        poly = QPolygonF(points)

        self.path_play = QPainterPath()
        self.path_play.addPolygon(poly)
        self.path_play.closeSubpath()
        self.path_play.translate(-50,-50)

        self.path_pause = QPainterPath()
        # TODO: in pyqt4, was addRoundRect
        self.path_pause.addRoundedRect(0,0,33,100,3,3)
        self.path_pause.addRoundedRect(66,0,33,100,3,3)
        self.path_pause.translate(-50,-50)

        points = [QPointF(0,0),QPointF(0,100),QPointF(66,50)]
        poly = QPolygonF(points)

        self.path_cont = QPainterPath()
        self.path_cont.addPolygon(poly)
        self.path_cont.closeSubpath()
        self.path_cont.addRoundedRect(66,0,33,100,3,3)
        self.path_cont.translate(-50,-50)

        self.penWidth = 2

        self.rotationAngle = 0
        self.setBackgroundRole(QPalette.Base)

        self.penColor = QColor(0, 0, 0)
        self.fillColor1 = QColor(  76,  99, 200) # play, bright
        self.fillColor2 = QColor(  24,  58, 125) # play, dark
        self.fillColor4 = QColor( 225,  31,   0) # cont, bright
        self.fillColor3 = QColor( 121,   2,   0) # cont, dark

        self.fillColor5 = QColor(  24,  30, 100) # play, darker
        self.fillColor6 = QColor(  64,   2,   0) # cont, darker
        self.fillColorlg = QColor(112, 112, 112) # light gray
        self.fillColordg = QColor(64, 64, 64) # dark gray
        self.fillColordg2 = QColor(32, 32, 32) # darker gray
        self.rotationAngle = 0

        self.setMouseTracking(True)

    def minimumSizeHint(self):
        return QSize(50, 50)

    def sizeHint(self):
        return QSize(100, 100)

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        side = min(w,h)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale( side / 100.0, side / 100.0)

        painter.setPen(QPen(self.penColor, self.penWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        # draw the play button:
        f = (90 - self.cont_size) / 2
        gradient = QRadialGradient(50, 50, 75, f, 50)

        c1 = self.fillColor1
        c2 = self.fillColor2
        c3 = self.fillColor5

        if self.state_hvr1 :
            if self.state_mouseDown :
                gradient.setColorAt(0.0, c2)
                gradient.setColorAt(.80, c3)
            else:
                gradient.setColorAt(0.0, c1)
                gradient.setColorAt(.80, c2)
        else:
            gradient.setColorAt(0.0, c2)
            gradient.setColorAt(.80, c1)

        painter.setBrush(QBrush(gradient))
        painter.drawPath(self.path)

        # draw the continue button:
        self.cont_size = 40;         # size of inner circle
        c = 95 - self.cont_size/2      # place the inner circle on the right edge
        r = self.cont_size/2    # to make a cresent moon
        gradient = QRadialGradient(c, 50, r, c, 50)

        if self.state_btn2 :
            c1 = self.fillColor3
            c2 = self.fillColor4
            c3 = self.fillColor6
        else:
            c1 = self.fillColorlg
            c2 = self.fillColordg
            c3 = self.fillColordg2


        if self.state_hvr2 :
            if self.state_mouseDown :
                gradient.setColorAt(0.0, c2)
                gradient.setColorAt(.80, c3)
            else:
                gradient.setColorAt(0.0, c2)
                gradient.setColorAt(.80, c1)
        else:
            gradient.setColorAt(0.0, c1)
            gradient.setColorAt(.70, c2)

        painter.setBrush(QBrush(gradient))
        painter.drawPath(self.path2)

        # draw the play / pause icon
        # we need to center it in w, the lengeth from the left
        # edge of the play button, to the start of the cont button
        # we want some padding, say 10 or so pixels on each side
        painter.setBrush(QBrush(self.penColor))

        s = 90 - self.cont_size/2
        scale = ((s / 100.0) * (side/100.0)) / 2.5
        l = (((s/2)) / 100.0) * side
        painter.resetTransform()
        painter.translate(l, side/2)
        painter.scale( scale , scale ) # scale after translation
        if self.state_btn1 :
            painter.drawPath(self.path_play)
        else:
            painter.drawPath(self.path_pause)

        # draw the cont icon
        s = self.cont_size
        # scale the length down to units per cent, and scale the
        # width of the widget down to units per cent, and then half scale
        scale = ((s/ 100.0) * (side/100.0)) / 2
        l = (((s)/2.0 + 5) / 100.0)
        l = side - l*side
        painter.resetTransform()
        painter.translate(l, side/2)
        painter.scale( scale, scale) # scale after translation

        painter.drawPath(self.path_cont)

    def enterEvent(self,event):
        self.state_hvr1 = True
        self.state_hvr2 = False
        self.stat_mouseDown = False;
        self.update()

    def leaveEvent(self,event):
        self.state_hvr1 = False
        self.state_hvr2 = False
        self.stat_mouseDown = False;
        self.update()

    def mouseMoveEvent(self,event):
        local = self.getLocation(event)
        if (self.location != local):
            self.location = local
            if self.location == 0 :
                self.state_hvr1 = True
                self.state_hvr2 = False
            else:
                self.state_hvr1 = False
                self.state_hvr2 = True
            self.update()

    def mousePressEvent(self,event):
        self.state_mouseDown = True
        self.update()

    def mouseReleaseEvent(self,event):
        self.state_mouseDown = False
        self.clickEvent()
        self.update()

    def getLocation(self,event):
        w = self.width()
        h = self.height()
        side = float(min(w,h))
        x = event.x()
        y = event.y()

        # bounding box, start x,y, and dimension d as a percentage length
        bx=(95-self.cont_size)/100.0
        by=(50-(self.cont_size/2))/100.0
        bd=(self.cont_size)/100.0

        localx = x/side
        localy = y/side

        if  localx > bx and localy > by and \
            localx < bx+bd and localy < by+bd :
            return 1

        return 0 # mouse is not inside middle button

    def clickEvent(self):
        if self.location == 0 :
            self.state_btn1 = not self.state_btn1
            self.on_play.emit( MediaState.pause if self.state_btn1 else MediaState.play )
        else:
            self.state_btn2 = not self.state_btn2
            self.on_stop.emit( self.state_btn2 )

    def setPlayState(self, state):
        self.state_btn1 = state != MediaState.play
        self.update()

    def setStopState(self, state):
        self.state_btn2 = state
        self.update()

class AdvanceButton(QWidget):

    clicked = pyqtSignal()

    def __init__(self, reverse=False, parent=None):
        super(AdvanceButton, self).__init__( parent )

        self.reverse = reverse
        self.mouse_hover = False

        s = 100
        m = 3
        m2 = 2*m
        a = 15
        self.path = QPainterPath()
        self.path.moveTo(s-m,m)
        self.path.arcTo(m,m, 2*(s-m2),s-m2, 90,180)
        self.path.arcTo(s-a,s-m,a*2,-(s-m2),90,180)

        h = 35
        w = s - 3*a
        points = [QPointF(s/2+w/2,s/2-h/2),
                  QPointF(s/2+w/2,s/2+h/2),
                  QPointF(s/2,s/2)]
        poly = QPolygonF(points)

        self.path_icon = QPainterPath()
        self.path_icon.setFillRule(Qt.WindingFill)
        self.path_icon.addPolygon(poly)
        self.path_icon.closeSubpath()
        self.path_icon.translate(-20,0)
        self.path_icon.addPolygon(poly)
        self.path_icon.closeSubpath()
        self.path_icon.translate(-10,0)
        self.path_icon.addRect(20,s/2-h/2,5,h)

        self.penColor = QColor(0, 0, 0)
        self.penWidth = 3

    def paintEvent(self, event):

        w = self.width()
        h = self.height()
        side = min(w,h)
        painter = QPainter(self)
        painter.setPen(QPen(self.penColor, self.penWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setTransform ( QTransform.fromTranslate(.5,1))

        self.fillColormg = self.palette().mid().color()
        self.fillColordg = self.palette().dark().color()

        self.gradient1 = QRadialGradient(50, 50, 50, 50, 50)
        self.gradient1.setColorAt(0.0, self.fillColormg)
        self.gradient1.setColorAt(.70, self.fillColordg)

        self.gradient2 = QRadialGradient(50, 50, 50, 50, 50)
        self.gradient2.setColorAt(0.0, self.fillColordg)
        self.gradient2.setColorAt(.70, self.fillColormg)

        if self.reverse == True:
            painter.translate( w, 0)
            painter.scale( -w / 100.0, h / 100.0)
        else:
            painter.translate( 0, 0)
            painter.scale( w / 100.0, h / 100.0)

        gradient = self.gradient1
        if self.mouse_hover:
            gradient = self.gradient2

        painter.setBrush(QBrush(gradient))
        painter.drawPath(self.path)
        painter.setBrush(QBrush(self.penColor))
        painter.translate(10,0)
        painter.drawPath(self.path_icon)

    def enterEvent(self,event):
        self.mouse_hover = True
        self.update()

    def leaveEvent(self,event):
        self.mouse_hover = False
        self.update()

    def mouseReleaseEvent(self,event):
        self.clicked.emit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Console Player")
    app.setQuitOnLastWindowClosed(True)
    window = AdvanceButton(True)
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
