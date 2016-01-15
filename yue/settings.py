
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

        self.platform = sys.platform
        if os.environ.get("NDKPLATFORM") is not None:
            self.platform = "android"
            base_path = '/data/data/com.github.nsetzer.yue/'
            self.db_settings_path = base_path + "settings.db"
            self.db_library_path  = base_path + "library.db"
        else:
            self.db_settings_path = "./settings.db"
            self.db_library_path  = "./library.db"

        self.db_settings = DictStore( self.db_settings_path )
        self.db_library = DictStore( self.db_library_path )

    def font_height(self, font_size ):
        """ return height in pixels for a given font size """
        return kivy.metrics.pt( font_size )

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

    @staticmethod
    def init():
        Settings.__instance = Settings()

    @staticmethod
    def instance():
        return Settings.__instance
