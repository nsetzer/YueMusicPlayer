

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class Tab(QWidget):
    """docstring for Tab"""
    def __init__(self, parent = None):
        super(Tab, self).__init__( parent)

    def onEnter(self):
        pass

    def onExit(self):
        pass

class TabWidget(QTabWidget):
    """Tab Widget

    Tab and TabWidget provide a common api for defining
    tabs within Yue.  Combined they provide the ability
    to detect when tabs are switch and enable enter/exit events.
    """
    def __init__(self, parent = None):
        super(TabWidget, self).__init__( parent)
        self.currentChanged.connect(self.onCurrentTabChanged)

        self.previousTab = None

    def onCurrentTabChanged(self,index):

        w = self.widget( index )

        if self.previousTab is not None:
            self.previousTab.onExit()

        if isinstance(w,Tab):
            w.onEnter();
            self.previousTab = w

        else:
            self.previousTab = None


