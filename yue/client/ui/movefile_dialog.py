
import os

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.library import Library
from ..widgets.ProgressDialog import ProgressDialog

class MoveFileProgressDialog(ProgressDialog):
    """
    move the set of items in paths to target_path
    """
    def __init__(self, target_path, paths, parent=None):
        super().__init__("Ingest", parent)
        self.paths = paths
        self.target_path = target_path

    def run(self):
        # scan input paths for media files
        # for each file found emit on_ingest signal

        # get a thread local copy of the library
        lib = Library.instance().reopen()

        self.setMessage("move progress dialog")

        self.pbar.setRange(0, len(self.paths))

        count = 0
        for path in self.paths:

            if os.path.isdir( path ):
                self.move_directory(lib, path)
            else:
                self.move_file(lib, path)
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(100000);

    def move_directory(self,lib,path):
        print("move dir ", path)

        songs = lib.searchDirectory(path,True)

        for song in songs:
            print(song['title'])

    def move_file(self,lib,path):
        print("move file",path)

    def closeOnFinish(self):
        # TODO: only if there are no errors
        return True