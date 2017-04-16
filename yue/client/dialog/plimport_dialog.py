#! python34 ../../../test/test_client.py $this
import os, sys, codecs

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from yue.qtcommon.ProgressDialog import ProgressDialog

class ImportM3uDialog(ProgressDialog):

    def __init__(self, path, parent=None):
        super().__init__("Sync", parent)

        self.uids = []
        self.m3upath = path
        self.paths = []

        self.errors = 0

    def run(self):

        lib = Library.instance().reopen()

        self.setMessage("Reading Playlist...")

        with codecs.open(self.m3upath,"r","utf-8") as rf:
            for line in rf:
                if line.startswith("#"):
                    continue
                self.paths.append(line.strip())

        self.setMessage("Import Songs...")

        self.pbar.setMaximum( len(self.paths) - 1 )

        for i,path in enumerate(self.paths):
            # TODO: support relative paths

            songs = lib.searchPath( path )
            if len(songs) > 0:
                self.uids.append( songs[0][Song.uid] )
            else:
                self.errors += 1
                sys.stderr.write("Failed to Import: %s\n"%path)

            self.valueChanged.emit(i)

        self.setMessage("Imported %d/%d songs failed for %d"%( \
                        len(self.uids), len(self.paths), self.errors))

    def getData(self):
        return self.uids

    def closeOnFinish(self):
        return self.errors == 0