
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class PositionSlider(QSlider):

    # value_set is emitted whenever the user changes the volume
    # it differs from valueChanged in that it is not sent
    # while the slider is being moved, but after the user is
    # finished moving the slider
    value_set = pyqtSignal(int)

    def __init__(self, parent=None):
        super(PositionSlider,self).__init__(Qt.Horizontal,parent);

        self.sliderReleased.connect(self.on_release)
        self.sliderPressed.connect(self.on_press)
        self.user_control = False

        self.setPageStep(0)

    def mouseReleaseEvent(self,event):
        super().mouseReleaseEvent(event)
        pos = int(self.maximum()*(event.x()/self.width()))
        self.value_set.emit( pos )
        with QSignalBlocker(self):
            self.setValue(pos)

    def setPosition(self,pos):
        if not self.user_control:
            self.setValue(pos)

    def on_press(self):
        self.user_control = True

    def on_release(self):
        self.user_control = False
        self.value_set.emit( self.value() )
