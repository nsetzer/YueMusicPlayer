
import os, sys, platform
import kivy.metrics
from kivy.logger import Logger

from kivy.storage.dictstore import DictStore
from yue.sqlstore import SQLStore, SQLView

class Settings(object):
    """docstring for Library"""
    __instance = None
    def __init__(self, manager):
        super(Settings, self).__init__()

        self.font_size = 16
        self.font_factor = 1.5

        self.manager = manager
        self.screen_home = 'Home'
        self.screen_library = 'Library'
        self.screen_now_playing = 'Now Playing'
        self.screen_current_playlist = 'Current Playlist'
        self.screen_presets = 'Presets'
        self.screen_modify_preset = 'Modify Presets'
        self.screen_ingest = 'Ingest'
        self.screen_settings = 'Settings'

        self.supported_types = ['.mp3', '.flac']

        self.init_platform()

        self.default_ingest_path = r'D:\Music\Flac'
        if self.platform == 'android':
            self.default_ingest_path = r'/sdcard'
        elif self.platform == 'linux2':
            self.default_ingest_path = r"/mnt/data/music/6ft.Down"

        self.img_noart_path =  os.path.join(self.platform_path,'img','noart.png')

        self.db_settings_path = os.path.join(self.platform_path, "settings.db")
        self.db_library_path  = os.path.join(self.platform_path, "library.db")
        self.db_path  = os.path.join(self.platform_path, "yue.db")

        self.db_settings = DictStore( self.db_settings_path )

        self.sqldb = SQLStore(self.db_path)

    def init_platform(self):
        self.platform = sys.platform
        self.platform_path = os.getcwd()
        self.arch = 'x86_64'

        if platform.architecture()[0] != '64bit':
                self.arch = 'x86'

        self.platform_libpath = os.path.join(self.platform_path,'lib',
                                             self.platform,
                                             self.arch)

        # there seems no better way to check if we are running on android
        #if os.environ.get("NDKPLATFORM") is not None:
        app_path = '/data/data/com.github.nsetzer.yue/'
        if os.path.exists(app_path):
            self.platform = "android"
            self.platform_path = '/data/data/com.github.nsetzer.yue/'
            self.arch = 'armeabi' # TODO, detect, x86, armeabi-v7a
            self.platform_libpath = os.path.join(self.platform_path,'lib')

        Logger.info("settings: platform name: %s"%self.platform)
        Logger.info("settings: platform path: %s"%self.platform_path)
        Logger.info("settings: platform lib : %s"%self.platform_libpath)


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
    def init( manager ):
        Settings.__instance = Settings( manager )

    @staticmethod
    def instance():
        return Settings.__instance
