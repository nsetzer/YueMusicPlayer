
"""

TODO:
    there are 4 events:
        on state change
        on song tick
        on song end
        on playlist end
    I need a way to bind functions to these events and decide on a function
    signature.

    SoundManager may want to be an instance of EventDispatcher
        enables: self.register_event_type('on_song_end')
        self.dispatch('on_song_end')
    https://kivy.org/docs/api-kivy.event.html#kivy.event.EventDispatcher

    seeking does not work for flac files
        duration() does work
        may be related to flac files create on windows,
        flac files have 'seek' points contained inside the file

    create a playlist class and move common playlist operations to this class
        playlists have a 'current index', which must me updated
        whenever an operation adds or removes elements before the index

    kivy sound class does not reliably detect audio duration
        - use mutagen

    vlc fails to play next song when current song finishes
        the song is loaded, but the player crashes.

"""
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger

from yue.settings import Settings
from yue.library import Library

from enum import Enum
import random

try:
    import yue.vlc as vlc
    vlc_support = True
except:
    vlc_support = False

isPosix = False

class MediaState(Enum):
    not_ready = 0
    play = 1
    pause = 2

class PlayList(object):
    """docstring for PlayList"""
    def __init__(self, list):
        super(PlayList, self).__init__()

        self.list
    def __getitem__(self,index):
        return self.list[index]

class SoundManager(EventDispatcher):
    """ interface class for playing audio, managing current playlist """
    def __init__(self):
        super(SoundManager, self).__init__()
        self.current_playlist = []
        self.playlist_index = 0 # current song, from current playlist

        self.register_event_type('on_song_tick')
        self.register_event_type('on_song_end')
        self.register_event_type('on_playlist_end')
        self.register_event_type('on_load')

    @staticmethod
    def init():
        #if vlc_support:
        #    SoundManager.__instance = VlcSoundManager()
        #else:
        SoundManager.__instance = KivySoundManager()

    @staticmethod
    def instance():
        return SoundManager.__instance

    def on_load(self,song):
        pass

    # playback controls

    def unload(self):
        raise NotImplementedError()

    def load(self, path):
        raise NotImplementedError()

    def play(self):
        raise NotImplementedError()

    def pause(self):
        raise NotImplementedError()

    def playpause(self):
        """ toggle state of audio
        """
        state = self.state()
        if state == MediaState.play:
            self.pause()
        else: # if state == MediaState.pause:
            self.play()

    #def stop(self):
    #    raise NotImplementedError()

    def seek(self, pos):
        """ pos as time in seconds (float) """
        raise NotImplementedError()

    def position(self):
        """ return current time in seconds"""
        raise NotImplementedError()

    def duration(self):
        """ return length of the loaded song in seconds (float) """
        raise NotImplementedError()

    def setVolume(self,volume):
        """ float from 0..1. 0: off, 1: maximum """
        raise NotImplementedError()

    def getVolume(self):
        raise NotImplementedError()

    def state(self):
        """ return MediaState """
        raise NotImplementedError()

    # current playlist management
    def play_index(self,idx):
        if 0 <= idx < len(self.current_playlist):
            self.playlist_index = idx
            key = self.current_playlist[ idx ]
            song = Library.instance().songFromId( key )
            self.load( song )
            self.play()
            return True # TODO this isnt quite right
        return False

    def next(self):
        """ play the next song in the playlist

        return true if a song was successfully loaded and playback began
        """
        #TODO: next causes 'end of file' stop
        if self.playlist_index < len(self.current_playlist) - 1:
            self.playlist_index += 1
            song = self.currentSong()
            if song is not None:
                self.load( song )
                self.play()
                return True # TODO this isnt quite right
            else:
                print("no next song to play")
        return False

    def prev(self):
        """ play the next song in the playlist

        return true if a song was successfully loaded and playback began
        """

        if self.playlist_index > 0:
            self.playlist_index -= 1
            song = self.currentSong()
            if song is not None:
                self.load( song )
                self.play()
                return True # TODO this isnt quite right
        return False

    def currentSong(self):
        if self.playlist_index < len(self.current_playlist):
            key = self.current_playlist[ self.playlist_index ]
            return Library.instance().songFromId( key )
        return None

    def setCurrentPlayList(self,lst):
        self.current_playlist = lst
        self.playlist_index = 0 # current song, from current playlist
        if len(lst) > 0:
            song = self.currentSong()
            self.load( song )

    def playlist_remove(self,idx):
        if 0 <= idx < len(self.current_playlist):
            del self.current_playlist[ idx ]

    def playlist_move(self, i, j):
        # TODO: update current playback index

        if 0 <= i < len(self.current_playlist):
            item = self.current_playlist[i]
            del self.current_playlist[i]
            self.current_playlist.insert(j,item)

    def playlist_shuffle(self):

        b= self.current_playlist[:self.playlist_index+1]
        a= self.current_playlist[self.playlist_index+1:]
        random.shuffle(a)
        self.current_playlist = b + a

    def on_song_tick(self, value):
        """ during playback, used to update the ui """
        # todo: need a mechanism to bind functions to events,
        # so that this object does not need to know about the UI.
        pass

    def on_song_tick_callback(self, *args):
        """ during playback, used to update the ui """
        # todo: need a mechanism to bind functions to events,
        # so that this object does not need to know about the UI.

        self.dispatch('on_song_tick',self.position())

    def on_song_end(self):
        """ callback for when current song finishes playing """
        Logger.info(" song finished ")
        if not self.next():
            self.dispatch('on_playlist_end')

    def on_playlist_end(self):
        """callback for when there are no more songs in the current playlist"""
        Logger.info(" playlist finished ")
        self.unload()

class KivySoundManager(SoundManager):
    """Playback implementation of SoundManager using Kivy"""
    __instance = None
    def __init__(self):
        super(KivySoundManager, self).__init__()
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

class VlcSoundManager(SoundManager):
    """Playback implementation of SoundManager using Kivy"""
    __instance = None
    def __init__(self):
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
            print "VLC instance Error: %s"%(e.args)

        if self.__instance__ == None:
            print "VLC instance Error: No Instance was created"
        else:
            try:
                self.__player__ = self.__instance__.media_player_new()

            except Exception as e:
                print "VLC Player Error: %s"%(e.args)

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

    def on_stop(self,vlcEvent):
        print("on stop", vlcEvent)
        self.dispatch('on_song_end')







