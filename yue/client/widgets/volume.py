
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class VolumeController(QWidget):
    def __init__(self, parent):
        super(VolumeController, self).__init__(parent)

        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(0,0,0,0)

        self.btn = QToolButton(self)
        self.btn.setDefaultAction(QAction(QIcon(':/img/app_volume.png'),"volume",self))

        self.volume_slider = QSlider(Qt.Horizontal,self);
        self.volume_slider.setRange(0,100)

        self.hbox.addWidget(self.btn)
        self.hbox.addWidget( self.volume_slider)

    def sizeHint(self):
        return QSize(128,32)