
from kivy.core.audio import SoundLoader
from kivy.clock import Clock, mainthread
from kivy.event import EventDispatcher
from kivy.logger import Logger

from .device import SoundDevice, MediaState

class KivySoundDevice(SoundDevice):
    """Playback implementation of SoundManager using Kivy"""
    __instance = None
    def __init__(self, libpath):
        super(KivySoundDevice, self).__init__()
        self.sound = None
        self.volume = 0.5
        self.current_position = 0
        # todo use a mutex to control mode_stop
        # when True, stop was issued by the user, intended for 'pause'
        # when false, stop was issued by end-of-file
        self.mode_stop = False

        self.clock_scheduled = False
        self.clock_interval = 0.5 # in seconds

    def unload(self):
        if self.sound is not None:
            self.sound.unload()
            self.setClock(False)
            self.sound = None

    def load(self, song):

        self.unload()
        # TODO: if path is unicode, some files will actually
        # be loaded correctly, even if there are unicode characters
        # in the path. decoding as utf-8 seems to always work correctly
        # at least on windows. further research is required.
        path = song['path']
        self.sound = SoundLoader.load( path.encode('utf-8') )
        if self.sound is not None:
            self.sound.volume = self.volume
            self.sound.bind(on_play=self.on_play)
            self.sound.bind(on_stop=self.on_stop)
            self.current_position = 0
            self.dispatch('on_load',song)

    def play(self):
        if self.sound is not None:
            self.sound.play()
            self.seek(self.current_position)
            self.setClock(True)

    def pause(self):
        """
        kivy audio does not enable pausing, instead the current position
        is recorded when the audio is stopped.
        """
        if self.sound is not None:
            if self.sound.state == 'play':
                self.mode_stop = True
                self.current_position = self.position()
                self.sound.stop()
                self.setClock(False)

    #def stop(self):
    #    if self.sound is not None:
    #        self.sound.stop()

    def seek(self,pos):
        if self.sound is not None:
            self.sound.seek(int(pos))

    def position(self):
        """ return current position in seconds (float)"""
        if self.sound is not None:
            return self.sound.get_pos()
        return 0.0

    def duration(self):
        if self.sound is not None:
            return self.sound.length
        return 0.0

    def setVolume(self,volume):
        if self.sound is not None:
            self.volume = volume
            self.sound.volume = volume

    def getVolume(self):
        return self.volume

    def state(self):
        if self.sound is not None:
            if self.sound.state == 'play':
                return MediaState.play
            else:
                return MediaState.pause
        return MediaState.not_ready

    def setClock(self,state):

        if self.clock_scheduled == False and state == True:
            self.clock_scheduled = True
            Clock.schedule_interval( self.on_song_tick_callback, self.clock_interval )
        elif self.clock_scheduled == True and state == False:
            self.clock_scheduled = False
            Clock.unschedule( self.on_song_tick_callback )

    def on_play(self,*args):
        pass

    def on_stop(self,*args):
        # if mode stop is True, stop was issued by a user 'pause'
        # otherwise stop was automatic 'end-of-file'
        if self.mode_stop:
            self.mode_stop = False
        else:
            self.dispatch('on_song_end')