
import os, sys, platform
import kivy.metrics
from kivy.logger import Logger
from kivy.core.text import LabelBase

from kivy.storage.dictstore import DictStore
from yue.core.sqlstore import SQLStore, SQLView
from kivy.core.text import Label as CoreLabel

class Settings(object):
    """docstring for Library"""
    __instance = None
    def __init__(self, manager):
        super(Settings, self).__init__()

        self.font_size = 12
        self.font_height = 0
        #self.font_factor = 1.5

        self.manager = manager
        self.screen_home = 'Home'
        self.screen_library = 'Library'
        self.screen_now_playing = 'Now Playing'
        self.screen_current_playlist = 'Current Playlist'
        self.screen_presets = 'Presets'
        self.screen_modify_preset = 'Modify Presets'
        self.screen_ingest = 'Ingest'
        self.screen_settings = 'Settings'

        # history is a stack, indicating previous screens.
        self.screen_history = []

        self.init_platform()

        self.default_ingest_path = r'D:\Music\Flac'
        if self.platform == 'android':
            self.default_ingest_path = r'/'
        elif self.platform == 'linux2':
            self.default_ingest_path = r"/mnt/data/music/6ft.Down"

        self.img_noart_path =  os.path.join(self.platform_path,'img','noart.png')

        self.db_settings_path = os.path.join(self.platform_path, "settings.db")
        self.db_path  = os.path.join(self.platform_path, "yue.db")

        self.db_settings = DictStore( self.db_settings_path )

        self.sqldb = SQLStore(self.db_path)

        self.recompute_dimensions()

        self.load_font("TakaoPMincho")

    def load_font(self,name):
        font_path = os.path.join(self.platform_path, 'font', name+".ttf")
        if os.path.exists( font_path ):
            LabelBase.register(name=name, fn_regular=font_path);

    def recompute_dimensions(self):

        lbl = CoreLabel(font_size = self.font_size)
        self.font_height = lbl.get_extents("_")[1]
        self.padding_top = self.font_height//2
        self.padding_bottom = self.font_height//2

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
        app_path = '/data/data/com.github.nsetzer.yue'
        if os.path.exists(app_path):
            self.platform = "android"
            self.platform_path = os.path.join(app_path,"files")
            self.arch = 'armeabi' # TODO, detect, x86, armeabi-v7a
            self.platform_libpath = os.path.join(app_path,"lib")

        Logger.info("settings: platform name: %s"%self.platform)
        Logger.info("settings: platform path: %s"%self.platform_path)
        Logger.info("settings: platform lib : %s"%self.platform_libpath)

    def font_height(self, font_size ):
        """ return height in pixels for a given font size """
        return kivy.metrics.sp( font_size )

    def row_height(self):
        return self.font_height + self.padding_top + self.padding_bottom

    def go_back(self, *args):
        """ go back to the previous screen. return true on success """
        if self.screen_history:
            scr = self.screen_history.pop()
            self.manager.current = scr
            return True
        return False

    def go_home(self, *args):
        self.manager.current = self.screen_home
        self.screen_history = []

    def go_library(self, *args):
        self.manager.current = self.screen_library
        #TODO: make the back button smarter.
        self.screen_history = [self.screen_home, ]

    def go_now_playing(self, *args):
        self.manager.current = self.screen_now_playing
        self.screen_history = [self.screen_home, ]

    def go_current_playlist(self, *args):
        self.manager.current = self.screen_current_playlist
        self.screen_history = [self.screen_home, ]

    def go_presets(self, *args):
        self.manager.current = self.screen_presets
        self.screen_history = [self.screen_home, ]

    def go_modify_preset(self, *args):
        self.manager.current = self.screen_modify_preset
        self.screen_history = [self.screen_home, ]

    def go_ingest(self, *args):
        self.manager.current = self.screen_ingest
        self.screen_history = [self.screen_home, ]

    def go_settings(self, *args):
        self.manager.current = self.screen_settings
        self.screen_history = [self.screen_home, ]

    @staticmethod
    def init( manager ):
        Settings.__instance = Settings( manager )

    @staticmethod
    def instance():
        return Settings.__instance
