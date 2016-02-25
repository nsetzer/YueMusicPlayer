

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
        self.setMessage("move progress dialog")
        count = self.pbar.minimum()
        while self.alive and count < self.pbar.maximum():
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(7500);

    def closeOnFinish(self):
        # TODO: only if there are no errors
        return True