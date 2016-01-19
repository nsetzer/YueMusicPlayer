
import os,sys
import kivy.metrics

from kivy.storage.dictstore import DictStore

class Settings(object):
    """docstring for Library"""
    __instance = None
    def __init__(self):
        super(Settings, self).__init__()

        self.font_size = 16
        self.font_factor = 1.5

        self.manager = None
        self.screen_home = 'Home'
        self.screen_library = 'Library'
        self.screen_now_playing = 'Now Playing'
        self.screen_current_playlist = 'Current Playlist'
        self.screen_presets = 'Presets'
        self.screen_modify_preset = 'Modify Presets'
        self.screen_ingest = 'Ingest'
        self.screen_settings = 'Settings'

        self.supported_types = ['.mp3', '.flac']

        self.platform = sys.platform
        self.platform_path = os.getcwd()
        if os.environ.get("NDKPLATFORM") is not None:
            self.platform = "android"
            self.platform_path = '/data/data/com.github.nsetzer.yue/'

        self.db_settings_path = os.path.join(self.platform_path, "settings.db")
        self.db_library_path  = os.path.join(self.platform_path, "library.db")

        self.db_settings = DictStore( self.db_settings_path )

    def font_height(self, font_size ):
        """ return height in pixels for a given font size """
        return kivy.metrics.sp( font_size )

    def row_height(self):
        return self.font_factor * self.font_height( self.font_size )

    def go_home(self, *args):
        self.manager.current = self.screen_home

    def go_library(self, *args):
        self.manager.current = self.screen_library

    def go_now_playing(self, *args):
        self.manager.current = self.screen_now_playing

    def go_current_playlist(self, *args):
        self.manager.current = self.screen_current_playlist

    def go_presets(self, *args):
        self.manager.current = self.screen_presets

    def go_modify_preset(self, *args):
        self.manager.current = self.screen_modify_preset

    def go_ingest(self, *args):
        self.manager.current = self.screen_ingest

    def go_settings(self, *args):
        self.manager.current = self.screen_settings

    def newSongUid(self):
        uid = 1
        if self.db_settings.exists("next_uid"):
            uid = self.db_settings.get("next_uid")['value']
        self.db_settings.put("next_uid",value=uid+1)
        return uid

    @staticmethod
    def init():
        Settings.__instance = Settings()

    @staticmethod
    def instance():
        return Settings.__instance
