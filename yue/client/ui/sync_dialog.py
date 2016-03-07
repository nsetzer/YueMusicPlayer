#! python34 ../../../test/test_client.py $this
import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from ..widgets.ProgressDialog import ProgressDialog

class SyncDialog(ProgressDialog):

    def __init__(self, parent=None):
        super().__init__("Sync", parent)

    def run(self):

        self.task_delete()
        self.task_copy()
        self.task_transcode()

    def task_delete(self):
        self.setMessage("delete")
        count = self.pbar.minimum()
        while self.alive and count < self.pbar.maximum():
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(6000);

    def task_copy(self):
        self.setMessage("copy")
        count = self.pbar.minimum()
        while self.alive and count < self.pbar.maximum():
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(6000);

    def task_transcode(self):
        self.setMessage("transcode")
        count = self.pbar.minimum()
        while self.alive and count < self.pbar.maximum():
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(6000);


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