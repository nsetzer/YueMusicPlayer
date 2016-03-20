
# todo: bass syncproc
from kivy.logger import Logger
from kivy.lib import osc

from .device import SoundDevice, MediaState

from collections import namedtuple

ServiceInfo = namedtuple("ServiceInfo",['oscid', 'hostname','clientport','serviceport'])

class ClientSoundDevice(SoundDevice):
    """Playback implementation of SoundManager for a remote provider"""
    __instance = None
    def __init__(self, libpath, info):
        super(ClientSoundDevice, self).__init__()
        self.volume = 0.5
        self.info = info

    def unload(self):
        osc.sendMsg('/audio_action', dataArray=["unload"], port=self.info.serviceport)

    def load(self, song):
        osc.sendMsg('/audio_action', dataArray=["load",song['path'],], port=self.info.serviceport)
        Logger.info("client: send load ")
        #self.dispatch('on_load',song)

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
        self.volume = volume
        osc.sendMsg('/audio_action', dataArray=["volume",volume], port=self.info.serviceport)

    def getVolume(self):
        return self.volume

    def state(self):
        raise NotImplementedError()

