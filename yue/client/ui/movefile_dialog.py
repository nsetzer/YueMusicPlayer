
import os

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library
from ..widgets.ProgressDialog import ProgressDialog

class MoveFileProgressDialog(ProgressDialog):
    """
    move the set of items in paths to target_path

    file_or_paths:
        type str : path to a single file to rename
                   target_path must be the new name of the file
        type list: list of files or directories
                   target_path must be the directory to move files to

    TODO: this has not been tested for any serious errors
          it would be best to pull some of the logic out
          so that it is testable

    """
    def __init__(self, view, target_path, file_or_paths, parent=None):
        super().__init__("Ingest", parent)

        if isinstance(file_or_paths, str):
            self.input_file = file_or_paths
            self.paths = None
        else:
            self.input_file = None
            self.paths = file_or_paths

        self.target_path = target_path

        self.view = view

        self.updated_count = 0;

    def run(self):
        # scan input paths for media files
        # for each file found emit on_ingest signal

        # get a thread local copy of the library
        lib = Library.instance().reopen()

        self.setMessage("move progress dialog")

        try:
            if self.paths:
                self.move(lib)

            elif self.input_file:
                self.rename( lib, self.input_file, self.target_path )


            self.setMessage("Updated %d songs."%self.updated_count)
        except OSError as e:
            self.setMessage("error: %s"%e)

    def rename(self, lib, src, tgt):

        if self.view.isdir( src ):
            songs = lib.searchDirectory( src ,True)
            self.view.move(src,tgt)
            for song in songs:
                tmp = tgt + song[Song.path][len(src):]
                lib.update(song[Song.uid],path=tmp)
                self.updated_count += 1
        else:
            songs = lib.searchPath( src )
            self.view.move(src,tgt)
            for song in songs: # this will update duplicate songs by path
                lib.update(song[Song.uid],path=tgt)
                self.updated_count += 1
        print( "src", src )
        print( "tgt", tgt )

    def move(self, lib):

        self.pbar.setRange(0, len(self.paths))

        count = 0
        for path in self.paths:
            new_path = os.path.join( self.target_path, os.path.basename( path ) )
            if os.path.isdir( path ):
                self._move_one(lib, path, new_path)
            else:
                self.rename(lib, path, new_path)
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(100000);

    def _move_one(self,lib,path,new_path):
        print( "dir-src", path )
        print( "dir-tgt", new_path )

        self.view.move(path,new_path)

        songs = lib.searchDirectory(path,True)

        for song in songs:
            tmp = new_path + song[Song.path][len(path):]
            lib.update(song[Song.uid],path=tmp)

        print("update %d songs"%len(songs))

    def closeOnFinish(self):
        # TODO: only if there are no errors
        return False
