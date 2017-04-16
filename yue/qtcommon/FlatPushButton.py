
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class FlatPushButton(QPushButton):
    """
        callBack is the function to run when clicked
    """
    def __init__(self,icon,parent=None):
        super(FlatPushButton,self).__init__(parent);
        self.setObjectName("FlatPushButton")
        self.setIcon(icon)
        self.setFlat(True)

