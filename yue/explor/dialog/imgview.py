
import os,sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.settings import Settings
from yue.qtcommon.Tab import TabWidget,Tab
from yue.qtcommon.explorer.imgview import ImageDisplay

class ImageDisplayDialog(QDialog):

    def __init__(self, parent=None):
        super(ImageDisplayDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(16,8,16,8)

        self.display = ImageDisplay(self);

        self.vbox.addWidget(self.display)

        self.resize(640,480);

    def setSource(self, source):

        self.display.setSource(source)
        self.display.update()
        self.display.current()

    def accept(self):
        self.display.close()
        super(ImageDisplayDialog,self).accept()

    def reject(self):
        self.display.close()
        super(ImageDisplayDialog,self).reject()