import osxmmkeys, time

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import sys

"""
# two libraries are requiered on osx
$ pip install pyobjc-core
$ pip install osxmmkeys

# The following works for OS version less than High Sierra
# disable itunes from reacting to media keys
launchctl unload -w /System/Library/LaunchAgents/com.apple.rcd.plist
"""

def emit(action):
    action.emit()
    # prevent iTunes from capturing the event
    return False

class HookThread(QObject):
    """docstring for HookThread"""

    playpause = pyqtSignal()
    play_prev = pyqtSignal()
    play_next = pyqtSignal()
    stop      = pyqtSignal()

    def __init__(self, parent=None):
        super(HookThread, self).__init__(parent)
        self.tap = osxmmkeys.Tap()
        print("tapping play_pause, next_track, prev_track")
        self.tap.on('play_pause', lambda: emit(self.playpause))
        self.tap.on('next_track', lambda: emit(self.play_next))
        self.tap.on('prev_track', lambda: emit(self.play_prev))

    def reload(self):
        pass

    def start(self):
        self.run()

    def run(self):
        sys.stdout.write("KeyBoard Hook Thread (start)\n")
        self.tap.start()

    def join(self):
        sys.stdout.write("KeyBoard Hook Thread (join)\n")
        # this causes python to never stop
        self.tap.stop()

    def setDiagEnabled(self,b):
        pass

    def getDiagEnabled(self):
        return False

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    hk = HookThread()
    hk.playpause.connect(lambda : sys.stdout.write("play/pause pressed\n"))
    hk.play_prev.connect(lambda : sys.stdout.write("prev pressed\n"))
    hk.play_next.connect(lambda : sys.stdout.write("next pressed\n"))
    hk.start()


    #input()
    sys.exit(app.exec_())

    hk.join() # gHQ!NeTKz7@*mBz9

if __name__ == '__main__':
    main()


