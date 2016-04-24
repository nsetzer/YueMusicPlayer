from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.settings import Settings

from .keyhook import cHook

import sys

# function keys are 0x70 to 0x7B
# playpause : 0xB3
# prev : 0xB1
# next : 0xB0

class HookThread(QThread):
    """docstring for HookThread"""

    playpause = pyqtSignal()
    play_prev = pyqtSignal()
    play_next = pyqtSignal()
    stop      = pyqtSignal()

    def __init__(self, parent=None):
        super(HookThread, self).__init__(parent)
        self.diag = False

        self.reload()

    def reload(self):

        s = Settings.instance()
        self.key_playpause = s["keyhook_playpause"]
        self.key_stop = s["keyhook_stop"]
        self.key_next = s["keyhook_next"]
        self.key_prev = s["keyhook_prev"]


    def keyproc(self,vkCode,scanCode,flags,time,ascii):

        if not flags&cHook.KEY_RELEASE: # only handle keyboard release events
            return 1

        if self.diag:
            if 0x20<=ascii<0x80 or ascii == 0x0A:
                sys.stdout.write("%c"%ascii);
            else:
                sys.stdout.write("{%02X}"%vkCode);

        if vkCode ==self.key_playpause:
            self.playpause.emit()
        elif vkCode ==self.key_stop:
            self.stop.emit()
        elif vkCode == self.key_prev:
            self.play_prev.emit()
        elif vkCode == self.key_next :
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
        #self.wait()

