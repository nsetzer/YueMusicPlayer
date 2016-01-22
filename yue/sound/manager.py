
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

from yue.settings import Settings

from .kivydevice import KivySoundDevice
from .bassdevice import BassSoundDevice
from .clientdevice import ClientSoundDevice

class PlayList(object):
    """docstring for PlayList"""
    def __init__(self, list):
        super(PlayList, self).__init__()

        self.list
    def __getitem__(self,index):
        return self.list[index]

class SoundManager(object):
    __instance = None

    @staticmethod
    def init( libpath, info = None ):
        #SoundManager.__instance = VlcSoundManager( libpath )
        #SoundManager.__instance = KivySoundDevice( libpath )
        if info is not None:
            SoundManager.__instance = ClientSoundDevice( libpath, info )
        else:
            SoundManager.__instance = BassSoundDevice( libpath )

    @staticmethod
    def instance():
        return SoundManager.__instance

