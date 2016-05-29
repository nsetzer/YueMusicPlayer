

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class Tab(QWidget):
    """docstring for Tab"""
    def __init__(self, parent = None):
        super(Tab, self).__init__( parent)

    def onEnter(self):
        print("entering tab....")
