
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

from yue.app.settings import Settings

from kivy.event import EventDispatcher

#from .kivydevice import KivySoundDevice
from yue.core.sound.bassdevice import BassSoundDevice
from .clientdevice import ClientSoundDevice

class PlayList(object):
    """docstring for PlayList"""
    def __init__(self, list):
        super(PlayList, self).__init__()

        self.list
    def __getitem__(self,index):
        return self.list[index]

class KivyCallbackSlot(EventDispatcher):
    """
    the playback device callback slot, this version
    emits signals so that functions are always run from
    the main thread.
    """

    def __init__(self):
        super(KivyCallbackSlot, self).__init__()
        self.callbacks = []

        self.register_event_type('on_custom_signal')
        #self.bind(on_custom_signal=self.execute_callback)

    def connect(self,cbk):
        self.callbacks.append(cbk)

    def emit(self,*args,**kwargs):
        for cbk in self.callbacks:
            self.dispatch('on_custom_signal',cbk,args,kwargs)

    def on_custom_signal(self, *args):
        print("on custom signal",args)
        cbk, args, kwargs = args
        cbk(*args,**kwargs)


class SoundManager(object):
    __instance = None

    supported_types = [".mp3", ".flac"]

    @staticmethod
    def init( playlist, libpath, info = None ):
        """ instanciate a client device if info is not none
        """
        #SoundManager.__instance = VlcSoundManager( libpath )
        #SoundManager.__instance = KivySoundDevice( libpath )
        if info is not None:
            SoundManager.__instance = ClientSoundDevice( playlist, info, KivyCallbackSlot )
        else:
            SoundManager.__instance = BassSoundDevice( playlist, libpath, True, KivyCallbackSlot )

    @staticmethod
    def instance():
        return SoundManager.__instance

