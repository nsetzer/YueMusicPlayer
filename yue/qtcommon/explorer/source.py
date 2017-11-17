

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.explorer.source import SourceListView


class LazySourceListView(SourceListView, QObject):
    """docstring for LazySourceListView"""
    loadDirectory = pyqtSignal(object)

    def load(self):

        self.data = []

        self.loadDirectory.emit(self)
