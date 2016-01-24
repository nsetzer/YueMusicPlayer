
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

    def unload(self):
        osc.sendMsg('/audio_action', dataArray=["unload"], port=self.info.serviceport)

    def load(self, song):
        osc.sendMsg('/audio_action', dataArray=["load",song['path'],], port=self.info.serviceport)
        self.dispatch('on_load',song)

    def play(self):
        osc.sendMsg('/audio_action', dataArray=["play"], port=self.info.serviceport)

    def pause(self):
        osc.sendMsg('/audio_action', dataArray=["pause"], port=self.info.serviceport)

    def playpause(self):
        """ toggle state of audio
        """
        osc.sendMsg('/audio_action', dataArray=["playpause"], port=self.info.serviceport)

    #def stop(self):
    #    if self.sound is not None:
    #        self.sound.stop()

    def seek(self,seconds):
        osc.sendMsg('/audio_action', dataArray=["seek",seconds], port=self.info.serviceport)

    def position(self):
        raise NotImplementedError()

    def duration(self):
        raise NotImplementedError()

    def setVolume(self,volume):
        osc.sendMsg('/audio_action', dataArray=["volume",volume], port=self.info.serviceport)

    def getVolume(self):
        raise NotImplementedError()

    def state(self):
        raise NotImplementedError()

    def setClock(self,state):
        if self.clock_scheduled == False and state == True:
            self.clock_scheduled = True
            Clock.schedule_interval( self.on_song_tick_callback, self.clock_interval )
        elif self.clock_scheduled == True and state == False:
            self.clock_scheduled = False
            Clock.unschedule( self.on_song_tick_callback )

