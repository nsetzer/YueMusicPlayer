
import sys
from ..library import Library
from ..util import check_path_alternatives
#from ..playlist import PlaylistManager

from enum import Enum

import os

class MediaState(Enum):
    not_ready = 0
    error = 1
    play = 2
    pause = 3
    end = 4

    @staticmethod
    def toString(s):
        return {
            MediaState.not_ready: "Not Ready",
            MediaState.error: "Error",
            MediaState.play: "Play",
            MediaState.pause: "Pause",
            MediaState.end: "Ended",
        }[ s ]

class CallbackSlot(object):
    def __init__(self):
        super(CallbackSlot, self).__init__()
        self.callbacks = []

    def connect(self,cbk):
        self.callbacks.append(cbk)

    def emit(self,*args,**kwargs):
        for cbk in self.callbacks:
            cbk(*args,**kwargs)

class SoundDevice(object):
    """ interface class for playing audio, managing current playlist """

    def __init__(self, playlist, cbkfactory=None):
        super(SoundDevice, self).__init__()
        self.playlist = playlist

        cbkfactory = cbkfactory or CallbackSlot

        self.on_load = cbkfactory() # song-dict
        self.on_state_changed = cbkfactory() # idx, key, state
        self.on_song_end = cbkfactory() # song
        self.on_playlist_end = cbkfactory() # no args

        # TODO: not current implemented in any way
        self.on_song_tick = cbkfactory() # position

        self.path_alternatives = []
        self.last_alt = None

    def refresh(self):
        # refresh underlying device connection
        pass

    # playback controls

    def name(self):
        raise NotImplementedError()

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

    def isPaused(self):
        """ returns true if calling play() will succeed """
        return self.state() == MediaState.pause

    def load_current( self ):
        idx, key = self.playlist.current()
        print(idx,key)
        song = Library.instance().songFromId( key )
        self.load( song )
        return song

    # current playlist management

    def load_index(self,idx):
        if 0 <= idx < len(self.playlist):
            key = self.playlist.set_index( idx )
            song = Library.instance().songFromId( key )
            self.load( song )
            return True
        return False;

    def play_index(self,idx):
        if self.load_index( idx ):
            self.play()

    def current(self):
        idx,key = self.playlist.current()
        song = Library.instance().songFromId( key )
        return idx,song

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
            sys.stderr.write("no next song\n");
            self.on_playlist_end.emit()
        except KeyError as e:
            sys.stderr.write("no such song %s\n"%e);

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
            sys.stderr.write("no prev song\n");
        except KeyError as e:
            sys.stderr.write("no such song %s\n"%e);
        return False

    def currentSong(self):
        idx,key = self.playlist.current()
        song = Library.instance().songFromId( key )
        return song

    def setAlternatives(self,a):
        self.path_alternatives = a

    def check_path( self, path ):
        self.last_alt,path = check_path_alternatives( \
            self.path_alternatives, path, self.last_alt)
        return path





