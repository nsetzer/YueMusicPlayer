

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from ..core.sound.device import MediaState
from yue.core.song import Song
from ..core.settings import Settings
from yue.core.library import Library
from yue.core.playlist import PlaylistManager

from ..core.sound.bassdevice import BassSoundDevice

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

def newDevice( playlist, libpath ):
    return BassSoundDevice(playlist, libpath,True, QtCallbackSlot)

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

    def on_song_load(self, song):
        self.root.plview.update()

        index = -1
        try:
            if self.playlist is not None and not self.one_shot:
                index,_ = self.playlist.current()
        except IndexError:
            pass

        self.root.songview.setCurrentSong( song )
        self.root.songview.setPlaylistInfo( index, len(self.playlist) )
        self.root.posview.setMaximum( song[Song.length] )
        self.root.libview.setCurrentSongId(song[Song.uid])

    def on_song_tick(self, pos):
        self.root.posview.setValue(pos)
        self.root.songview.setPosition(pos)

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
            # TODO: the library view should be refreshed, without
            # moving the scroll bar in some way to reflect this change

            Library.instance().incrementPlaycount(song[Song.uid])
            # return to the first song in the playlist if the current
            # song does not match the song that just finished.
            # for example, when the user makes a new playlist
            _, uid = self.playlist.current()
            if uid != song[Song.uid]:
                self.device.play_index( 0 )
            else:
                self.device.next()

        if idx == self.stop_index:
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
        s = Settings.instance()
        query = "ban=0"
        presets = s['playlist_presets']
        if len(presets) > 0:
            query = presets[0]
        size =s['playlist_size']

        songs = Library.instance().search(query, orderby=Song.random, limit=size)
        lst = [ song[Song.uid] for song in songs ]
        self.playlist.set( lst )
        self.device.play_index( 0 )
        self.root.plview.updateData()
        self.root.plview.scrollToCurrent()

    def playOneShot(self, path):
        """ play a song, then return to the current playlist """
        self.one_shot = True
        song = Song.fromPath( path )
        self.device.load( song )
        self.device.play()

    def play_index(self,row):
        self.device.play_index( row )

    def playpause(self, state):
        if state == MediaState.play:
            self.device.play()
        else:
            self.device.pause();

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
