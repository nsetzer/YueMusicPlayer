from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from .keyhook import cHook

class HookThread(QThread):
    """docstring for HookThread"""

    playpause = pyqtSignal()
    play_prev = pyqtSignal()
    play_next = pyqtSignal()

    def __init__(self, parent=None):
        super(HookThread, self).__init__(parent)

    def keyproc(self,vkCode,scanCode,flags,time):

        if not flags&0x80: # only handle keyboard release
            return 1

        if vkCode == 0xB3:
            self.playpause.emit()
        elif vkCode == 0xB1:
            self.play_prev.emit()
        elif vkCode == 0xB0:
            self.play_next.emit()

        return 1


    def run(self):
        try:
            cHook.listen(self.keyproc)
        except Exception as e:
            print(e)
        sys.stdout.write("KeyBoard Hook Thread has ended");

    def join(self):
        sys.stdout.write("KeyBoard Hook Thread (join)");
        # TODO: this does not work at all
        #cHook.unhook();
        self.wait()

