

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class CloseTabButton(QPushButton):
    """
        callBack is the function to run when clicked
    """
    def __init__(self,callBack,parent=None):
        super(CloseTabButton,self).__init__(parent);
        self.setObjectName("CloseTabButton")
        self.setFixedHeight(16);
        self.setFixedWidth(16);
        self.callBack = callBack
        self.setIcon( QIcon(':/img/app_x.png') )

    def mouseReleaseEvent(self,event=None):
        self.callBack();