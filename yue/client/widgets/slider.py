
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class PositionSlider(QSlider):

    value_set = pyqtSignal(int)

    def __init__(self, parent=None):
        super(PositionSlider,self).__init__(Qt.Horizontal,parent);

        self.user_control = False
        self.sliderReleased.connect(self.on_release)
        self.sliderPressed.connect(self.on_press)

    def mouseReleaseEvent(self,event):
        super().mouseReleaseEvent(event)
        pos = int(self.maximum()*(event.x()/self.width()))
        self.value_set.emit( pos )
        self.setValue(pos)

    def on_press(self):
        self.user_control = True

    def on_release(self):
        self.user_control = False
        self.value_set.emit( self.value() )
