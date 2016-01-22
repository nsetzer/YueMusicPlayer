
# todo: bass syncproc
import os
from kivy.core.audio import SoundLoader
from kivy.clock import Clock, mainthread
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.lib import osc

from .device import SoundDevice, MediaState

from .bassplayer import BassPlayer, BassException

from collections import namedtuple

ServiceInfo = namedtuple("ServiceInfo",['oscid', 'hostname','clientport','serviceport'])

class ClientSoundDevice(SoundDevice):
    """Playback implementation of SoundManager for a remote provider"""
    __instance = None
    def __init__(self, libpath, info):
        super(ClientSoundDevice, self).__init__()
        self.volume = 0.5
        self.info = info
        #self.media_duration = 100 # updated on load

        self.clock_scheduled = False
        self.clock_interval = 0.5 # in seconds

        # osc.bind(self.info.oscid, someapi_callback, '/some_api')
        #osc.sendMsg('/init', dataArray=[libpath,], port=self.info.serviceport)

        #self.setClock(True)
        self._state = True

    def unload(self):
        osc.sendMsg('/audio_action', dataArray=["unload"], port=self.info.serviceport)

    def load(self, song):
        osc.sendMsg('/load_path', dataArray=[song['path'],], port=self.info.serviceport)

    def play(self):
        osc.sendMsg('/audio_action', dataArray=["play"], port=self.info.serviceport)
        self._state = True

    def pause(self):
        osc.sendMsg('/audio_action', dataArray=["pause"], port=self.info.serviceport)
        self._state = False

    #def stop(self):
    #    if self.sound is not None:
    #        self.sound.stop()

    def seek(self,seconds):
        pass

    def position(self):
        pass

    def duration(self):
        pass

    def setVolume(self,volume):
        pass

    def getVolume(self):
        pass

    def state(self):
        if self._state:
            return MediaState.play

        return MediaState.pause

    def setClock(self,state):
        if self.clock_scheduled == False and state == True:
            self.clock_scheduled = True
            Clock.schedule_interval( self.on_song_tick_callback, self.clock_interval )
        elif self.clock_scheduled == True and state == False:
            self.clock_scheduled = False
            Clock.unschedule( self.on_song_tick_callback )

