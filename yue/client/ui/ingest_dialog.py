
import os,sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library
from ..widgets.ProgressDialog import ProgressDialog

class IngestProgressDialog(ProgressDialog):

    def __init__(self, paths, parent=None):
        super().__init__("Ingest", parent)
        self.paths = paths

        self.media_files = []

        self.supported_exts = Song.supportedExtensions()

        self.ingest_count = 0

    def closeOnFinish(self):
        # auto close if we successfully ingest one file
        return self.ingest_count == 1

    def run(self):
        # scan input paths for media files
        # for each file found emit on_ingest signal

        self.setMessage("Scanning input...")

        lib = Library.instance().reopen()

        for path in self.paths:
            if os.path.isdir( path ):
                self.scan_directory( path )
            else:
                ext = os.path.splitext( path )[1]
                if ext in self.supported_exts:
                    self.media_files.append( path )

        if len(self.media_files) == 0:
            self.setMessage("No Media Files Found...")
            return

        self.setMessage("Importing %d media files..."%len(self.media_files))

        self.pbar.setMaximum( len(self.media_files) )

        for i, path in enumerate(self.media_files):
            if not self.alive:
                return

            self.load_file( lib, path )

            self.valueChanged.emit(i)

        self.setMessage("Successfully imported %d media files."%self.ingest_count)

    def scan_directory( self, path):

        # TODO: for linux, followlinks will need to be true
        # at that time, we will need to keep track of visited directories
        # in some way. when topdown is true (by default) removing names
        # from dnames will prevent walking into a directory
        # the only question is whether dpath is an absolute path, with links
        # resolved. to store visited directories it  would be best to consider
        # only absolute paths, but still refer to media files by their
        # symlink path

        for dpath, dnames, fnames in os.walk( path, followlinks=False ):

            if not self.alive:
                return

            self.setMessage("Scanning input... %s"%os.path.basename(dpath))

            for fname in fnames:
                ext = os.path.splitext( fname )[1].lower()
                if ext in self.supported_exts:
                    self.media_files.append( os.path.join(dpath,fname) )

    def load_file(self, lib, path):

        res = lib.searchPath( path )
        if len(res)==0: # file not in library
            sys.stdout.write("load file: `%s`\n"%path)
            lib.loadPath( path )
            self.ingest_count += 1
            return True
        else:
            sys.stdout.write("ingest skipping duplicate file: %s\n"%path)

        return False
