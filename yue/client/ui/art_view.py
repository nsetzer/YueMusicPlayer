
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
        self.display()

    def display(self):
        self.pixmap = QPixmap.fromImage(self.image).scaled(
                                self.size(),
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation)
        self.label.setPixmap(self.pixmap)

    def resizeEvent(self,event):
        self.display()
        pass

class AlbumArtView(QLabel):
    """docstring for AlbumArtView"""
    def __init__(self, parent=None):
        super(AlbumArtView, self).__init__(parent)

        self.dialog = AlbumArtDialog(self)
        self.dialog.resize(512,512)
    def setArt(self, song):
        try:
            self.image = QImage.fromData(get_album_art_data(song))
            self.pixmap = QPixmap.fromImage(self.image).scaled(
                                self.size(),
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation)
            self.setPixmap(self.pixmap)
            self.setHidden(False)
        except ArtNotFound:
            # surpress error not interesting
            #sys.stderr.write("%s\n"%e)
            self.setHidden(True)

    def mouseReleaseEvent(self,event):
        self.dialog.setImage( self.image )
        self.dialog.show()
