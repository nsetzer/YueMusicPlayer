#! python34 ../../../test/test_client.py $this
import os, sys, codecs

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from ..widgets.ProgressDialog import ProgressDialog

class ExportM3uDialog(ProgressDialog):

    def __init__(self, uids, path, parent=None):
        super().__init__("Sync", parent)

        self.uids = uids
        self.pbar.setMaximum( len(uids) - 1 )
        self.path = path

    def run(self):

        lib = Library.instance().reopen()
        songs = lib.songFromIds( self.uids )

        self.setMessage("Saving Playlist...")

        with codecs.open(self.path,"w","utf-8") as wf:
            wf.write("#EXTM3U")
            for i, song in enumerate(songs):
                wf.write("#EXTINF:%d:%s - %s\n"%(song[Song.length],song[Song.artist],song[Song.title]))
                wf.write("%s\n"%song[Song.path])
                self.valueChanged.emit(i)

    def closeOnFinish(self):
        return True