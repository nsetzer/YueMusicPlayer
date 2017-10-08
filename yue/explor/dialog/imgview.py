
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

        self.toolbar = QToolBar(self)
        self.tbar_btn_fullscreen = QToolButton(self)
        self.tbar_btn_fullscreen.setIcon(QIcon(":/img/app_fullscreen.png"))
        self.tbar_btn_fullscreen.clicked.connect(self.toggleFullScreen)
        self.toolbar.addWidget(self.tbar_btn_fullscreen)

        self.statusbar = QStatusBar(self)
        self.sbar_lbl_imginfo = QLabel(self)

        self.statusbar.addWidget(self.sbar_lbl_imginfo)

        self.vbox.addWidget(self.toolbar)
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

        if isinstance(item,QImage):
            txt = "(%d, %d)"%(item.width(),item.height())
            self.sbar_lbl_imginfo.setText(txt)

        elif isinstance(item,tuple):
            img,map,map_params = item
            txt = "(%d, %d)"%(img.width(),img.height())
            self.sbar_lbl_imginfo.setText(txt)

        elif isinstance(item,QByteArray):
            self.sbar_lbl_imginfo.setText("")
        else:
            self.sbar_lbl_imginfo.setText("")


    def keyPressEvent(self,event):

        if event.key() ==  Qt.Key_Escape and self.isFullScreen():
            self.toggleFullScreen();

    def toggleFullScreen(self):
        self.setWindowState(self.windowState() ^ Qt.WindowFullScreen);

        self.toolbar.setHidden(self.isFullScreen())
        self.statusbar.setHidden(self.isFullScreen())


