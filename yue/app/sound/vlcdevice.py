
from kivy.core.audio import SoundLoader
from kivy.clock import Clock, mainthread
from kivy.event import EventDispatcher
from kivy.logger import Logger

from .device import SoundDevice, MediaState

from . import vlc

class VlcSoundDevice(SoundDevice):
    """Playback implementation of SoundManager using Kivy"""
    __instance = None
    def __init__(self, libpath):
        super(VlcSoundManager, self).__init__()
        self.volume = 0.5
        self.media_duration = 100 # updated on load

        self.clock_scheduled = False
        self.clock_interval = 0.5 # in seconds

        self.invoke();

    def invoke(self):
        """
            If the initalization fails
            an attempt can be made to restart it from the command line
            by typing:
                exec MpGlobal.Player.mp.invoke()
        """
        try:
            self.__instance__ = None;
            if isPosix:
                #'--plugin-path=/usr/lib/vlc'
                self.__instance__ = vlc.Instance('--plugin-path=%s'%Settings.POSIX_VLC_MODULE_PATH)
            else:
                self.__instance__ = vlc.Instance()
        except Exception as e:
            print("VLC instance Error: %s"%(e.args))

        if self.__instance__ == None:
            print("VLC instance Error: No Instance was created")
        else:
            try:
                self.__player__ = self.__instance__.media_player_new()

            except Exception as e:
                print("VLC Player Error: %s"%(e.args))

            self.setVolume( self.volume )



        self.__media__ = None

    def destroy(self):

        self.unload()
        self.__player__.release()
        self.__player__ = None
        self.__instance__.release()
        self.__instance__ = None
        print("vlc destroyed")

    def unload(self):
        if self.__media__ is not None:
            self.__media__.release()
            self.__media__ = None
            self.setClock(False)

    def load(self, song):

        self.unload()
        # TODO: if path is unicode, some files will actually
        # be loaded correctly, even if there are unicode characters
        # in the path. decoding as utf-8 seems to always work correctly
        # at least on windows. further research is required.
        path = song['path']
        self.media_duration = song.get('length',60)
        if self.__media__ is None:
            self.__media__ = self.__instance__.media_new(path)
            self.__player__.set_media(self.__media__)
            eventmgr = self.__player__.event_manager()
            eventmgr.event_attach(vlc.EventType.MediaPlayerEndReached,self.on_stop)
            self.dispatch('on_load',song)
        else:
            print("error loading")

    def play(self):
        if self.__media__ is not None:
            self.__player__.play()
            self.setClock(True)

    def pause(self):
        """
        kivy audio does not enable pausing, instead the current position
        is recorded when the audio is stopped.
        """
        if self.__media__ is not None:
            self.__player__.pause()
            self.setClock(False)

    #def stop(self):
    #    if self.sound is not None:
    #        self.sound.stop()

    def seek(self,seconds):
        if self.__player__ is not None:
            self.__player__.set_time(int(seconds*1000))

    def position(self):
        """ return current position in seconds (float)"""
        if self.__media__ != None :
            t = self.__player__.get_time();
            return t/1000
        else:
            return 0

    def duration(self):
        #t = self.__media__.get_duration()/1000.0
        #print("duration: %d"%t)
        return self.media_duration

    def setVolume(self,volume):

        self.__player__.audio_set_volume( max(0,min(100,int(100*volume))) )
        self.volume = volume

    def getVolume(self):
        return self.volume

    def state(self):
        if self.__player__ is None:
            return MediaState.not_ready;

        s = self.__player__.get_state();

        if s == vlc.State.NothingSpecial:
            return MediaState.not_ready
        elif s == vlc.State.Opening:
            return MediaState.not_ready
        elif s == vlc.State.Buffering:
            return MediaState.not_ready
        elif s == vlc.State.Playing:
            return MediaState.play
        elif s == vlc.State.Paused:
            return MediaState.pause
        elif s == vlc.State.Stopped:
            return MediaState.not_ready
        elif s == vlc.State.Ended:
            return MediaState.not_ready
        elif s == vlc.State.Error:
            return MediaState.not_ready
        return MediaState.not_ready

    def setClock(self,state):

        if self.clock_scheduled == False and state == True:
            self.clock_scheduled = True
            Clock.schedule_interval( self.on_song_tick_callback, self.clock_interval )
        elif self.clock_scheduled == True and state == False:
            self.clock_scheduled = False
            Clock.unschedule( self.on_song_tick_callback )

    @mainthread
    def on_stop(self,vlcEvent):
        print("on stop", vlcEvent)
        self.dispatch('on_song_end')





