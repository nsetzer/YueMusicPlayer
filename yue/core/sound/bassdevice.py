
import os,sys

from .device import SoundDevice, MediaState
from ..bass.bassplayer import BassPlayer, BassException

bass_states = {
    BassPlayer.PLAYING : MediaState.play,
    BassPlayer.PAUSED  : MediaState.pause,
    BassPlayer.STOPPED  : MediaState.pause,
    BassPlayer.UNKNOWN  : MediaState.error,
    }

class BassSoundDevice(SoundDevice):
    """Playback implementation of Sound Device"""
    __instance = None
    def __init__(self, playlist, libpath, use_capi = False, cbkfactory=None):
        super(BassSoundDevice, self).__init__( playlist, cbkfactory )
        self.volume = 0.5
        self.error_state = False
        self.current_song = None

        BassPlayer.init()

        #TODO: support other plugins
        self.load_plugin(libpath, "bassflac")

        self.device = BassPlayer(use_capi=use_capi)

        # this feature causes a segfault on android.
        if use_capi:
            self.device.setStreamEndCallback( self.on_bass_end )

    def on_bass_end(self, *args):
        self.on_song_end.emit( self.current_song )

    def load_plugin(self,libpath,name):

        try:

            plugin_path = os.path.join(libpath,"lib%s.so"%name)
            if os.path.exists( plugin_path ):
                return BassPlayer.loadPlugin( plugin_path )

            plugin_path = os.path.join(libpath,"%s.dll"%name)
            if os.path.exists( plugin_path ):
                return BassPlayer.loadPlugin( plugin_path )

            print("Plugin: Plugin not found '%s' in %s."%(name,libpath))

        except OSError as e:
            print(e)
        except Exception as e:
            print(e)

    def unload(self):
        self.device.unload()

    def load(self, song):
        path = song['path']
        self.current_song = song
        try:
            self.device.unload()
            if self.device.load( path ):
                self.error_state = False
                self.on_load.emit(song)
            else:
                self.error_state = True
        except UnicodeDecodeError as e:
            print(e)
            self.error_state = True

    def play(self):
        #self.device.channelIsValid():
        if self.device.play():
            idx,key = self.playlist.current()
            self.on_state_changed.emit(idx,key,self.state())

    def pause(self):
        if self.device.pause():
            idx,key = self.playlist.current()
            self.on_state_changed.emit(idx,key,self.state())

    def seek(self,seconds):
        self.device.position( seconds )

    def position(self):
        """ return current position in seconds (float)"""
        return self.device.position( )

    def duration(self):
        return self.device.duration()

    def setVolume(self,volume):
        """ volume: in range 0.0 - 1.0"""
        self.device.volume( max(0,min(100,int(volume*100))) )

    def getVolume(self):
        """ volume: in range 0.0 - 1.0"""
        return self.device.volume()/100

    def state(self):
        if self.error_state:
            return MediaState.error
        bass_state = self.device.status()
        return bass_states.get(bass_state,MediaState.not_ready)

