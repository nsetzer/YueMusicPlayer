

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.library import Library
from ..widgets.ProgressDialog import ProgressDialog

class IngestProgressDialog(ProgressDialog):

    def __init__(self, controller, paths, parent=None):
        super().__init__("Ingest", parent)
        self.controller = controller
        self.paths = paths

    def run(self):
        # scan input paths for media files
        # for each file found emit on_ingest signal
        self.setMessage("ingest progress dialog")
        count = self.pbar.minimum()
        while self.alive and count < self.pbar.maximum():
            count += 1
            self.valueChanged.emit(count)
            QThread.usleep(7500);
