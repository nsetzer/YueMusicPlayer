
import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.qtcommon import resource

from yue.core.song import Song

class ResourceManager(object):
    """docstring for ResourceManager"""
    _instance = None

    LINK      = 0x100
    DIRECTORY = 0x001
    FILE      = 0x002
    SONG      = 0x003
    ARCHIVE   = 0x004
    IMAGE     = 0x005
    GIF       = 0x006
    MOVIE     = 0x007
    DOCUMENT  = 0x008
    CODE      = 0x009

    LINK_DIRECTORY = 0x101
    LINK_FILE      = 0x102
    LINK_SONG      = 0x103
    LINK_ARCHIVE   = 0x104
    LINK_IMAGE     = 0x105
    LINK_GIF       = 0x106
    LINK_MOVIE     = 0x107
    LINK_DOCUMENT  = 0x108
    LINK_CODE      = 0x109

    @staticmethod
    def instance():
        # TODO: not thread safe....
        if ResourceManager._instance is None:
            ResourceManager._instance = ResourceManager()
        return ResourceManager._instance

    def __init__(self):
        super(ResourceManager, self).__init__()
        self.resources = {}

        # configure default file associations
        self.ext_archive  = [".gz",".zip",".7z",".rar",".iz",".bz2"]
        self.ext_image    = [".jpg",".png",".bmp",".jpeg",]
        self.ext_gif    = [".gif"]
        self.ext_movie    = [".avi",".mp4",".webm",".mkv"]
        self.ext_document = [".doc",".docx",".xls",".xlsx",".pdf"]
        self.ext_code     = [".py", ".sh", ".pl", ".bat",
                             ".c", ".c++", ".cpp",".h", ".h++", ".hpp"]

        self.rebuildFileAssociations()

    def load(self):

        self.resources = {}

        self.resources[ResourceManager.FILE]      = QPixmap(':/img/app_file.png')
        self.resources[ResourceManager.SONG]      = QPixmap(':/img/app_song.png')
        self.resources[ResourceManager.DIRECTORY] = QPixmap(':/img/app_folder.png')
        self.resources[ResourceManager.ARCHIVE]   = QPixmap(':/img/app_archive.png')
        self.resources[ResourceManager.IMAGE]     = QPixmap(':/img/app_media.png')
        self.resources[ResourceManager.GIF]       = QPixmap(':/img/app_media.png')
        self.resources[ResourceManager.MOVIE]     = QPixmap(':/img/app_video.png')
        self.resources[ResourceManager.DOCUMENT]  = QPixmap(':/img/app_document.png')
        self.resources[ResourceManager.CODE]      = QPixmap(':/img/app_code.png')

        self.img_link = QPixmap(':/img/app_shortcut.png')

        for res in [ResourceManager.FILE,ResourceManager.SONG,
                    ResourceManager.DIRECTORY,ResourceManager.ARCHIVE,
                    ResourceManager.IMAGE, ResourceManager.GIF,
                    ResourceManager.MOVIE, ResourceManager.DOCUMENT,
                    ResourceManager.CODE]:
            img = self.compose(self.resources[res],self.img_link)
            self.resources[ResourceManager.LINK|res] = img

    def rebuildFileAssociations(self):

        self.map_ext = dict()

        for ext in Song.supportedExtensions():
            self.map_ext[ext] = ResourceManager.SONG

        for ext in self.ext_archive:
            self.map_ext[ext] = ResourceManager.ARCHIVE

        for ext in self.ext_image:
            self.map_ext[ext] = ResourceManager.IMAGE

        for ext in self.ext_gif:
            self.map_ext[ext] = ResourceManager.GIF

        for ext in self.ext_movie:
            self.map_ext[ext] = ResourceManager.MOVIE

        for ext in self.ext_document:
            self.map_ext[ext] = ResourceManager.DOCUMENT

        for ext in self.ext_code:
            self.map_ext[ext] = ResourceManager.CODE

    def setFileAssociation(self,kind,lst):
        """
        update the file associations for a given kind
        lst should be the list of all extensions that map to kind

        rebuildFileAssociations must be called manually after
        calling this function
        """
        if   kind == ResourceManager.FILE:
            # assume all files that do not match a given extension
            # are simply generic files.
            raise Exception("Not Supported")
        elif   kind == ResourceManager.SONG:
            # the song associations are dependant on the bass/vlc library
            raise Exception("Cannot set song associations")
        elif kind == ResourceManager.ARCHIVE:
            self.ext_archive = set(lst)
        elif kind == ResourceManager.IMAGE:
            self.ext_image = set(lst)
        elif kind == ResourceManager.GIF:
            self.ext_gif = set(lst)
        elif kind == ResourceManager.MOVIE:
            self.ext_movie = set(lst)
        elif kind == ResourceManager.DOCUMENT:
            self.ext_document = set(lst)
        elif kind == ResourceManager.CODE:
            self.ext_code = set(lst)

    def getFileAssociation(self,kind):
        if   kind == ResourceManager.FILE:
            raise Exception("Not Supported")
        elif   kind == ResourceManager.SONG:
            return list(Song.supportedExtensions())
        elif kind == ResourceManager.ARCHIVE:
            return list(self.ext_archive)
        elif kind == ResourceManager.IMAGE:
            return list(self.ext_image)
        elif kind == ResourceManager.GIF:
            return list(self.ext_gif)
        elif kind == ResourceManager.MOVIE:
            return list(self.ext_movie)
        elif kind == ResourceManager.DOCUMENT:
            return list(self.ext_document)
        elif kind == ResourceManager.CODE:
            return list(self.ext_code)

    def compose(self,imga,imgb):

        imgc = QImage(imga.size(), QImage.Format_ARGB32_Premultiplied);
        painter = QPainter(imgc);

        painter.setCompositionMode(QPainter.CompositionMode_Source);
        painter.fillRect(imgc.rect(), Qt.transparent);

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver);
        painter.drawPixmap(0, 0, imga);

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver);
        painter.drawPixmap(0, 0, imgb);

        painter.end();

        return QPixmap.fromImage(imgc);

    def get(self,kind):
        """ return the icon associated with the given kind """
        return self.resources[kind]

    def getExtType(self,ext):
        """ given an extension return the matching kind """
        return self.map_ext.get(ext.lower(),ResourceManager.FILE)

    def width(self):
        """ return the standard icon width
        icons are assumed to be square
        TODO: this method should be removed, and replaced with size()
            which returns the dimensions of the largest icon width & height
        """
        return self.resources[ResourceManager.FILE].width()


