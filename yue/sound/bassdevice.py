
# todo: bass syncproc
import os
from kivy.core.audio import SoundLoader
from kivy.clock import Clock, mainthread
from kivy.event import EventDispatcher
from kivy.logger import Logger

from .device import SoundDevice, MediaState

from .bassplayer import BassPlayer, BassException

class BassSoundDevice(SoundDevice):
    """Playback implementation of SoundManager using Kivy"""
    __instance = None
    def __init__(self, libpath):
        super(BassSoundDevice, self).__init__()
        self.volume = 0.5
        #self.media_duration = 100 # updated on load

        self.clock_scheduled = False
        self.clock_interval = 0.5 # in seconds

        BassPlayer.init()

        #TODO: support other plugins
        for name in os.listdir(libpath):
            if 'flac' in name:
                BassPlayer.loadPlugin( os.path.join(libpath,name) )

        self.device = BassPlayer()

        self.device.setStreamEndCallback( self.on_end )

    def unload(self):

        self.device.unload()
        self.setClock(False)

    def load(self, song):
        path = song['path']
        #self.media_duration = song.get('length',100)
        if self.device.load( path ):
            self.dispatch('on_load',song)

    def play(self):
        if self.device.play():
            self.setClock(True)

    def pause(self):
        if self.device.pause():
            self.setClock(False)

    #def stop(self):
    #    if self.sound is not None:
    #        self.sound.stop()

    def seek(self,seconds):
        self.device.position( seconds )

    def position(self):
        """ return current position in seconds (float)"""
        return self.device.position( )

    def duration(self):
        #return self.media_duration
        return self.device.duration()

    def setVolume(self,volume):
        self.device.volume( max(0,min(100,int(vol*100))) )

    def getVolume(self):
        return self.device.volume()/100

    def state(self):

        status = {
            BassPlayer.PLAYING : MediaState.play,
            BassPlayer.PAUSED  : MediaState.pause,
        }.get(self.device.status(),MediaState.not_ready)

        return status

    def setClock(self,state):

        if self.clock_scheduled == False and state == True:
            self.clock_scheduled = True
            Clock.schedule_interval( self.on_song_tick_callback, self.clock_interval )
        elif self.clock_scheduled == True and state == False:
            self.clock_scheduled = False
            Clock.unschedule( self.on_song_tick_callback )

    @mainthread
    def on_end(self, player):
        self.dispatch('on_song_end')




