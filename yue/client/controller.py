

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from ..core.sound.device import MediaState
from yue.core.song import Song, UnsupportedFormatError
from yue.core.search import ParseError
from ..core.settings import Settings
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from ..core.sound.dummydevice import DummySoundDevice
#from yue.core.sound.vlcdevice import VlcSoundDevice

try:
    from ..core.sound.bassdevice import BassSoundDevice
except ImportError as e:
    sys.stderr.write('bass import: %s'%e)
    BassSoundDevice = None

class QtCallbackSlot(QObject):
    """
    the playback device callback slot, this version
    emits signals so that functions are always run from
    the main thread.
    """
    callback_signal = pyqtSignal(object,tuple,dict)

    def __init__(self):
        super(QtCallbackSlot, self).__init__()
        self.callbacks = []
        self.callback_signal.connect( self.execute_callback )

    def connect(self,cbk):
        self.callbacks.append(cbk)

    def emit(self,*args,**kwargs):
        for cbk in self.callbacks:
            self.callback_signal.emit(cbk,args,kwargs)

    def execute_callback(self, cbk, args, kwargs):
        cbk(*args,**kwargs)

def newDevice( playlist, libpath, kind="default" ):
    if kind in ("bass","default") and BassSoundDevice is not None:
        return BassSoundDevice(playlist, libpath,True, QtCallbackSlot)
    #elif kind == 'vlc':
    #    return VlcSoundDevice(playlist,libpath, QtCallbackSlot)
    return DummySoundDevice(playlist, libpath,True, QtCallbackSlot)

class PlaybackThread(QThread):
    """peridocially update the UI during playback"""
    def __init__(self, device):
        super(PlaybackThread, self).__init__()

        self.device = device;
        self.mutex = QMutex()
        self.condvar = QWaitCondition()

        self.updates_enabled = False
        self.alive = True

    def run(self):

        self.mutex.lock();

        # TODO: no idea what happens here if there is an exception
        # is there a way to test, if the mutex is locked, catch
        # the exception and then release?

        while self.alive:
            self.device.on_song_tick.emit( self.device.position() )
            if self.updates_enabled:
                self.condvar.wait(self.mutex,250)
            else:
                self.condvar.wait(self.mutex)

        self.mutex.unlock();

    def notify(self,update=None):
        # if update is true, the thread will reawaken to update the ui
        # if false, the thread will eventually shutdown, waiting
        # for nitify to be called again with a true value
        self.mutex.lock();
        if update is not None:
            self.updates_enabled = update
        self.condvar.wakeOne();
        self.mutex.unlock();

    def join(self):
        self.alive = False

class PlaybackController(object):

    def __init__(self,device, root):
        super(PlaybackController,self).__init__();

        self.root = root
        self.device = device
        device.on_load.connect( self.on_song_load )
        device.on_song_tick.connect( self.on_song_tick )
        device.on_state_changed.connect( self.on_state_changed )
        device.on_song_end.connect( self.on_song_end )
        device.on_playlist_end.connect( self.on_playlist_end )

        self.stop_index = - 1;

        self.thread = PlaybackThread(device)
        self.thread.start()

        self.one_shot = False

        self.playlist = PlaylistManager.instance().openCurrent()

        if self.dspSupported():
            s = Settings.instance()
            if s["volume_equalizer"]:
                self.device.setEQEnabled( True )

        self.last_tick = 0

    def play_index(self,idx):
        self.one_shot = False
        self.device.play_index( idx )

    def play_next(self):
        self.one_shot = False
        self.device.next()

    def play_prev(self):
        self.one_shot = False
        self.device.prev()

    def get_playlist_info(self):
        index = -1
        try:
            if self.playlist is not None and not self.one_shot:
                index,_ = self.playlist.current()
                index += 1
        except IndexError:
            pass
        length = len(self.playlist)

        return index, length

    def getCurrentQuery(self):
        """ return the current query string and suggested number of songs. """
        s = Settings.instance()
        presets = s['playlist_presets']
        size =s['playlist_size']
        idx = s['playlist_preset_default']

        query = "ban=0" # default, always ignore banised songs

        # use the default preset when available
        if idx < len(presets):
            query = presets[idx]
        #elif len(presets) > 0:
        #    query = presets[0]

        return query,size

    def on_song_load(self, song):

        index,length = self.get_playlist_info()
        self.root.songview.setCurrentSong( song )
        self.root.songview.setPlaylistInfo( index, length)

        self.root.aartview.setArt( song )

        self.root.posview.setMaximum( song[Song.length] )

        self.root.libview.setCurrentSongId(song[Song.uid])

        self.root.plview.update()

    def on_song_tick(self, pos):
        if pos >= 0:
            self.root.posview.setPosition(pos)
            self.root.songview.setPosition(pos)
            self.last_tick = pos

    def on_state_changed(self,idx,key,state):
        # this can be used to start/stop a thread which updates
        # the current position of the song
        self.thread.notify(state == MediaState.play)
        self.root.btn_playpause.setPlayState( state )

    def on_song_end(self, song):

        try:
            idx,_ = self.device.current()
        except IndexError:
            sys.stderr.write("error: No Current Song\n")
            return

        if self.one_shot:
            self.device.play_index( idx )
            self.device.pause();
            self.one_shot = False
        else:

            Library.instance().incrementPlaycount(song[Song.uid])
            self.duration_fix( song, self.last_tick )

            # return to the first song in the playlist if the current
            # song does not match the song that just finished.
            # for example, when the user makes a new playlist
            _, uid = self.playlist.current()
            if uid != song[Song.uid]:
                self.device.play_index( 0 )
            else:
                self.device.next()

            # todo: only if song matches current query?
            self.root.libview.refresh()

        if idx == self.stop_index:
            self.root.btn_playpause.setStopState(False)
            self.device.pause()
            self.stop_index = -1;

        # i have wanted this *forever*.
        # it could be annoying, so i should make it optional
        # when turned off, update() must be called instead.
        self.root.plview.scrollToCurrent()

    def on_playlist_end(self):
        """
        create a new playlist using the default query, or a preset
        """

        query,size = self.getCurrentQuery()
        sys.stdout.write("create playlist `%s` limit %d\n"%(query,size))

        # TODO: set limit to size + 10
        # filter the list by searching for any consecutive songs-by-artist
        # pop that song and cycle it to the end of the list
        # then use the first `size` elements of the list as the result
        # I also want to implement the hash.... limit total number of
        # songs per artist in the resulting list when possible

        try:
            songs = Library.instance().search(query, orderby=Song.random, limit=size)
            lst = [ song[Song.uid] for song in songs ]
        except ParseError as e:
            sys.stderr.write("%s"%e)
            lst =[]

        self.playlist.set( lst )
        self.device.play_index( 0 )
        self.root.plview.updateData()
        self.root.plview.scrollToCurrent()
        self.root.backup_database()

    def rollPlaylist(self):
        """ generate new songs using the default query."""

        index,_ = self.playlist.current()
        length = len(self.playlist)
        pcnt = 1.0 - index/length

        query,plsize = self.getCurrentQuery()

        size =int(plsize * .25)
        size = max(plsize - length + min(index,size), size)

        count = min(index,size) # number to deelte

        sys.stdout.write("insert songs using `%s` limit %d\n"%(query,size))

        try:
            # generate a new list and insert it
            songs = Library.instance().search(query, orderby=Song.random, limit=size)
            lst = [ song[Song.uid] for song in songs ]
            self.playlist.insert(length,lst);

            # remove the same number of songs from the start of the list
            if count > 0:
                self.playlist.delete(list(range(count)));
        except ParseError as e:
            sys.stderr.write("%s"%e)

    def playOneShot(self, path):
        """ play a song, then return to the current playlist """
        self.one_shot = True
        try:
            song = Song.fromPath( path )
        except UnsupportedFormatError as e:
            sys.stderr.write("playback error: %s\n"%e)
        else:
            self.device.load( song )
            self.device.play()

    def playpause(self, state):
        if state == MediaState.play:
            self.device.play()
        else:
            self.device.pause();

    def seek(self,position):
        self.device.seek( position )
        if self.device.isPaused():
            self.device.play()

    def toggleStop(self):
        # toggle stop state and update ui

        self._setStop( self.stop_index == -1 )
        self.root.plview.update()
        self.root.btn_playpause.setStopState( self.stop_index != -1 )

    def _setStop(self, state):
        # if true, stop playback after this song
        if state:
            try:
                self.stop_index,_ = self.device.current()
            except IndexError:
                sys.stderr.write("error: No Current Song\n")
        else:
            self.stop_index = -1;

    def setEQGain(self, gdb_list):

        if isinstance(self.device,BassSoundDevice):
            sys.stdout.write("User Updated EQ : %s\n"%' '.join(["%.2f"%f for f in gdb_list]))
            self.device.updateDSP( {"ZBPEQ": gdb_list} )

    def dspSupported(self):
        if isinstance(self.device,BassSoundDevice):
            return self.device.zbpeq is not None
        return False

    def toggleEQ(self):
        """ toggle the state on/off for equalizer """
        if isinstance(self.device,BassSoundDevice):
            self.device.toggleEQ()
        else:
            sys.stderr.write("Equalizer not supported.\n")

    def getEQ(self):
        """ return true if equalizer is enabled """
        if isinstance(self.device,BassSoundDevice):
            return self.device.equalizerEnabled()
        else:
            sys.stderr.write("Equalizer not supported.\n")
        return False;

    def duration_fix( self, song, new_length):
        new_length = int(new_length)
        if int(song[Song.length]) != new_length:
            sys.stdout.write("%s length: %d new_length:%d\n"%(
                Song.toString(song),
                song[Song.length],self.last_tick))
            Library.instance().update(song[Song.uid],**{Song.length:new_length})