
from kivy.core.audio import SoundLoader
from kivy.clock import Clock, mainthread
from kivy.event import EventDispatcher
from kivy.logger import Logger

from yue.settings import Settings
from yue.library import Library
from yue.playlist import PlaylistManager

from enum import Enum

class MediaState(Enum):
    not_ready = 0
    play = 1
    pause = 2

class SoundDevice(EventDispatcher):
    """ interface class for playing audio, managing current playlist """
    def __init__(self):
        super(SoundDevice, self).__init__()
        self.current_playlist = []
        self.playlist_index = 0 # current song, from current playlist

        self.register_event_type('on_song_tick')
        self.register_event_type('on_song_end')
        self.register_event_type('on_playlist_end')
        self.register_event_type('on_load')

        self.playlist = PlaylistManager.instance().openPlaylist('current')


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
        pass

    def next(self):
        """ play the next song in the playlist

        return true if a song was successfully loaded and playback began
        """
        #TODO: next causes 'end of file' stop

        try:
            idx,key = self.playlist.next()
            song = Library.instance().songFromId( key )
            self.load( song )
            self.play()
            return True # TODO this isnt quite right
        except StopIteration:
            Logger.info("no next song");
        except KeyError as e:
            Logger.info("no such song %s"%e);

        return False

    def prev(self):
        """ play the next song in the playlist

        return true if a song was successfully loaded and playback began
        """

        try:
            idx,key = self.playlist.prev()
            song = Library.instance().songFromId( key )
            self.load( song )
            self.play()
            return True # TODO this isnt quite right
        except StopIteration:
            Logger.info("no prev song");
        except KeyError as e:
            Logger.info("no such song %s"%e);
        return False

    def currentSong(self):
        idx,key = self.playlist.current()
        song = Library.instance().songFromId( key )
        return song

    @mainthread
    def setCurrentPlayList(self,lst):
        self.playlist.set(lst)
        song = self.currentSong()
        self.load( song )

    def playlist_remove(self,idx):
        self.playlist.delete(idx)

    def playlist_move(self, i, j):
        # TODO: update current playback index

        self.playlist.reinsert(i,j)

    def playlist_shuffle(self):
        pass

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