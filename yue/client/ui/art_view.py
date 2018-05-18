
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import get_album_art_data, ArtNotFound

class AlbumArtDialog(QDialog):
    def __init__(self,parent=None):
        super(AlbumArtDialog,self).__init__(parent);
        self.vbox = QVBoxLayout( self )
        self.vbox.setContentsMargins(0,0,0,0)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumWidth(1)
        self.label.setMinimumHeight(1)

        self.vbox.addWidget(self.label)

        self.label.setStyleSheet("QLabel { background-color : black; }")

    def setImage(self,image):

        self.image = image
        self.update_pixmap()

    def update_pixmap(self):
        self.pixmap = QPixmap.fromImage(self.image).scaled(
                                self.size(),
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation)
        self.label.setPixmap(self.pixmap)

    def resizeEvent(self,event):
        self.update_pixmap()

class AlbumArtView(QLabel):
    """docstring for AlbumArtView"""
    _dialog = None

    def __init__(self, parent=None):
        super(AlbumArtView, self).__init__(parent)

        self.dialog = None
        self.default_pixmap = None

        self.image = None
        self.pixmap = None

    def setDefaultArt(self, pixmap):
        self.default_pixmap = pixmap

        if self.pixmap is None:
            self.image = pixmap.toImage()
            self.pixmap = pixmap
            super().setPixmap(self.pixmap)
            self.setHidden(False)

    def setArt(self, song):
        try:
            image = QImage.fromData(get_album_art_data(song))
            self.setImage(image)
        except (ArtNotFound, KeyError) as e:
            # surpress error not interesting
            #sys.stderr.write("%s\n"%e)
            if self.default_pixmap is None:
                self.setHidden(True)
            else:
                self.setPixmap(self.default_pixmap)

    def setImage(self, image):
        self.image = image
        self.pixmap = QPixmap.fromImage(image).scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation)
        super().setPixmap(self.pixmap)
        self.setHidden(False)

    def mouseReleaseEvent(self,event):

        if event.button()&Qt.LeftButton:
            event.accept()
            if self.image is not None:
                if AlbumArtView._dialog is None:
                    AlbumArtView._dialog = AlbumArtDialog(self)
                    AlbumArtView._dialog.finished.connect(self.onDialogClosed)
                    AlbumArtView._dialog.setAttribute(Qt.WA_DeleteOnClose);
                AlbumArtView._dialog.setImage( self.image )
                AlbumArtView._dialog.resize(512,512)
                AlbumArtView._dialog.show()
        else:
            event.ignore()

    def onDialogClosed(self):

        # this causes osx to crash
        #if AlbumArtView._dialog:
        #    AlbumArtView._dialog.setParent(None)
        #    AlbumArtView._dialog = None
        pass
