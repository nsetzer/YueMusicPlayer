import os

from yue.core.settings import Settings

class FileAssoc(object):
    """docstring for FileAssoc"""
    def __init__(self):
        super(FileAssoc, self).__init__()

    @staticmethod
    def isText(path):
        dir,name = os.path.split(path)
        name,ext = os.path.splitext(name)

        if name.startswith(".") and ext =="":
            return True # dot file

        exts = Settings.instance()["ext_text"]

        return ext in exts

    @staticmethod
    def isImage(path):
        dir,name = os.path.split(path)
        name,ext = os.path.splitext(name)

        exts = Settings.instance()["ext_image"]

        return ext in exts

    @staticmethod
    def isAudio(path):
        dir,name = os.path.split(path)
        name,ext = os.path.splitext(name)

        exts = Settings.instance()["ext_audio"]

        return ext in exts

    @staticmethod
    def isMovie(path):
        dir,name = os.path.split(path)
        name,ext = os.path.splitext(name)

        exts = Settings.instance()["ext_movie"]

        return ext in exts
