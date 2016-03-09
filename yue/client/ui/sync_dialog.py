#! python34 ../../../test/test_client.py $this
import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from yue.core.sync import SyncManager
from ..widgets.ProgressDialog import ProgressDialog

class QtSyncManager(SyncManager):
    """docstring for QtSyncManager"""
    def __init__(self,library,playlist,target,enc_path,
        transcode=0,
        player_directory=None,
        equalize=False,
        bitrate=0,
        no_exec=False,
        parent=None):
        super(QtSyncManager, self).__init__(library,playlist,target,enc_path, \
            transcode,player_directory,equalize,bitrate,no_exec)

        self.step_count = 0
        self.parent = parent

    def setOperationsCount(self,count):
        self.parent.setRange(0,count)

    def message(self,msg):
        self.parent.setMessage(msg)

    def getYesOrNo(msg):
        result = self.parent.getInput("Delete",msg,"cancel","delete")
        return result==1

    def log(self,msg):
        try:
            sys.stdout.write(msg+"\n")
        except UnicodeEncodeError:
            sys.stdout.write("<>\n")

    def run_proc(self,proc):
        n = proc.begin()
        for i in range(n):
            proc.step(i)
            self.step_count += 1
            self.parent.valueChanged.emit(self.step_count)
            if self.no_exec:
                QThread.usleep(25000);
        proc.end()


class SyncDialog(ProgressDialog):

    def __init__(self, parent=None):
        super().__init__("Sync", parent)

    def setRange(self,a,b):
        self.pbar.setRange(a,b)

    def run(self):

        ffmpeg=r"C:\ffmpeg\bin\ffmpeg.exe"
        db_path = "yue.db"

        target = "test"
        transcode = SyncManager.T_NON_MP3
        equalize = False
        bitrate = 320
        no_exec = True

        sqlstore = SQLStore(db_path)
        Library.init( sqlstore )
        PlaylistManager.init( sqlstore )

        lib = Library.instance().reopen()
        pm = PlaylistManager.instance().reopen()
        pl = pm.openPlaylist("current")

        sm = QtSyncManager(lib,pl,target,ffmpeg, \
                transcode=transcode,equalize=equalize,no_exec=no_exec,parent=self)
        sm.run()

def main():

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    db_path = "./yue.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

    window = SyncDialog()
    window.start()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()