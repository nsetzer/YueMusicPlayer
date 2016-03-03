
import os,sys

from yue.core.song import Song
from .device import SoundDevice, MediaState

class DummySoundDevice(SoundDevice):
    """Playback implementation of Sound Device"""
    __instance = None
    def __init__(self, playlist, libpath, use_capi = False, cbkfactory=None):
        super(DummySoundDevice, self).__init__( playlist, cbkfactory )
        self.playlist = playlist

    def load_plugin(self,libpath,name):
        pass

    def unload(self):
        pass

    def load(self, song):
        self.on_load.emit(song)

    def play(self):
        try:
            idx,key = self.playlist.current()
            self.on_state_changed.emit(idx,key,MediaState.play)
        except IndexError:
            sys.stderr.write("error: No Current Song\n")

    def pause(self):
        try:
            idx,key = self.playlist.current()
            self.on_state_changed.emit(idx,key,MediaState.pause)
        except IndexError:
            sys.stderr.write("error: No Current Song\n")

    def seek(self,seconds):
        pass

    def position(self):
        """ return current position in seconds (float)"""
        return 0

    def duration(self):
        return 100

    def setVolume(self,volume):
        """ volume: in range 0.0 - 1.0"""
        pass

    def getVolume(self):
        """ volume: in range 0.0 - 1.0"""
        return 50

    def state(self):
        return MediaState.pause

