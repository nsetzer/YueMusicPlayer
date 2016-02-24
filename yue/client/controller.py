

import sys
isPython3 = sys.version_info[0]==3
if isPython3:
    unicode = str
try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except:
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import *

from ..core.sound.device import MediaState
from yue.core.song import Song

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

        self.thread = PlaybackThread(device)
        self.thread.start()

    def on_song_load(self, song):
        self.root.plview.update()
        self.root.songview.setCurrentSong( song )
        self.root.posview.setMaximum( song[Song.length] )

    def on_song_tick(self, pos):
        self.root.posview.setValue(pos)
        self.root.songview.setPosition(pos)

    def on_state_changed(self,idx,key,state):
        # this can be used to start/stop a thread which updates
        # the current position of the song
        self.thread.notify(state == MediaState.play)

    def on_song_end(self, song):
        self.device.next()
        self.root.plview.update()

    def on_playlist_end(self):
        pl = PlaylistManager.instance().openPlaylist("current")
        songs = Library.instance().search(None, orderby=Song.random, limit=20)
        lst = [ s['uid'] for s in songs ]
        pl.set( lst )
        self.device.play_index( 0 )
        self.root.plview.update()
