import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class ContextBar(QComboBox):
    """docstring for ContextBar"""

    accepted = pyqtSignal(str)

    def __init__(self, parent=None):
        super(ContextBar, self).__init__(parent)
        self.setEditable(True)

    def keyReleaseEvent(self, event=None):
        super(ContextBar, self).keyReleaseEvent(event)
        key = event.key()
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            self.keyReleaseEnter(self.currentText())
            self.accepted.emit(self.currentText())

    def keyReleaseEnter(self, text):
        pass

    def setText(self, text):
        self.setEditText(text)

    def text(self):
        return self.currentText()
