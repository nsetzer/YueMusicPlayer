
import os,sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.settings import Settings
from yue.qtcommon.Tab import TabWidget,Tab
from yue.qtcommon.explorer.imgview import ImageDisplay

from yue.core.explorer.source import SourceGraphicsView
from yue.qtcommon.ResourceManager import ResourceManager


class SourceImageView(SourceGraphicsView):
    """docstring for SourceImageView"""
    def __init__(self, source, dirpath):
        super(SourceImageView, self).__init__(source, dirpath)

    def validateResource(self,path):
        ext = self.source.splitext(path)[1]
        kind = ResourceManager.instance().getExtType(ext)
        return kind in (ResourceManager.IMAGE,ResourceManager.GIF);


class ImageDisplayDialog(QDialog):

    def __init__(self, parent=None):
        super(ImageDisplayDialog, self).__init__(parent)

        self.vbox=QVBoxLayout(self)
        self.vbox.setContentsMargins(0,0,0,0)

        self.display = ImageDisplay(self);

        self.display.displayResource.connect(self.onDisplayResource)

        self.statusbar = QStatusBar(self)
        self.sbar_lbl_imginfo = QLabel(self)

        self.statusbar.addWidget(self.sbar_lbl_imginfo)

        self.vbox.addWidget(self.display)
        self.vbox.addWidget(self.statusbar)

        self.resize(640,480);

    def setSource(self, source, path):

        if not source.isdir(path):
            dirpath, name = source.split(path)
            view = SourceImageView( source, dirpath)
            view.chdir( dirpath )
            view.setIndex( name )
        else:
            view = SourceImageView( source, path)
            view.chdir( path )

        self.display.setSource( view )
        self.display.update()
        self.display.current()

    def accept(self):
        self.display.close()
        super(ImageDisplayDialog,self).accept()

    def reject(self):
        self.display.close()
        super(ImageDisplayDialog,self).reject()

    def onDisplayResource(self, path, item):

        name=self.display.getSource().split(path)[1]
        self.setWindowTitle(name)