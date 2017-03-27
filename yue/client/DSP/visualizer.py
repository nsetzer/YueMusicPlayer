#! python $this "D:/Music/Discography/Discography - Kyuss/[1994] Welcome to Sky Valley [Promo]/07 Odyssey.mp3"
#! python $this "D:/Music/Japanese/Discography - Dazzle Vision/[2012.05.04] Shocking Loud Voice/01 Second.mp3"


#! python $this ./media/odyssey.mp3
import sys,os

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import math



class Visualizer(QWidget):
    def __init__(self,parent=None):
        super(Visualizer,self).__init__(parent);
        self.maxvaluelist = [1.0,]*11;

        self.data = [ 0.5*i/10.0 for i in range(11) ]#[0,]*11;
        self.data_max = [0]*30; # bug waiting to happen again

        self.timer = QTimer(self);
        self.timer.setInterval(1000/20)

        self.timer.timeout.connect(self.timeout);
        self.bar_color = QColor(0,0,0);

    def getData(self):
        return [ i/10.0 for i in range(11) ]

    def isActive(self):
        """ return true if there is new data to update """
        return True;

    def isRunning(self):
        """ return whether the timer is runnning """
        return self.timer.isActive();

    def start(self):
        self.timer.start();

    def stop(self):
        self.timer.stop();

    def hide(self):
        self.stop();
        return super(Visualizer,self).hide();

    def timeout(self):
        if self.isActive():
            self.data = self.getData()
            for i,(f,g) in enumerate(zip(self.data,self.data_max)):
                if f>=g:
                    self.data_max[i]=f
                else:
                    self.data_max[i]*=.9
            self.update();

    def paintEvent(self, event= None):
        w = self.width()
        h = self.height()
        m = h/2
        p = QPainter(self)
        self.draw_main(p,w,h)

    def draw_main(self,p,w,h):
        # div by 3 scales maximum expected value to 1.0
        m = lambda x : 0 if x<.001 else (math.log(x*1000,10))/3.0;
        bw = int(w/len(self.data)) ;
        s = int( ((w-2-2)%len(self.data)) )
        lpad = int( (w - bw*len(self.data))/2 )
        q=max(1,h/100)
        for i,(f,g) in enumerate(zip(self.data,self.data_max)):
        #for i,f in enumerate(self.data):
            v = m( max(min(1.0,f),0.0) )
            u = m( max(min(1.0,g),0.0) )
            #p.fillRect(bw*i+self.bar_lpad,h,bw-self.bar_lpad-self.bar_rpad,-v*h,self.bar_color)
            p.fillRect(bw*i+lpad,h,bw-1,-v*h,self.bar_color)
            p.fillRect(bw*i+lpad,h-(u*h+q/2),bw-1,q,QColor(30,75,200))

        p.setPen(QColor(255,0,0,48))
        #v = m(.75)
        #p.drawLine(0,h-(v*h),w,h-(v*h))
        for i in range(1,10):
            v = h * (1 - m(1.0/(2**i)) );
            p.drawLine(0,v,w,v);



